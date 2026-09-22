"""Conexion con Chrome: tiempos de carga, salud de la sesion y relanzamiento."""
from selenium.common.exceptions import TimeoutException, WebDriverException

from apoyo import CasoMonitor


class DriverFalso:
    def __init__(self, nombre="driver", error_get=None, muerto=False):
        self.nombre, self.error_get, self.muerto = nombre, error_get, muerto
        self.visitas, self.scripts = [], []

    def get(self, url):
        self.visitas.append(url)
        if self.error_get:
            raise self.error_get

    def execute_script(self, script):
        self.scripts.append(script)

    @property
    def current_window_handle(self):
        if self.muerto:
            raise ConnectionError("chromedriver no responde")  # error no-Selenium
        return "ventana"


class TestNavegar(CasoMonitor):

    def test_carga_normal(self):
        driver = DriverFalso()
        self.m.navegar(driver, "https://a")
        self.assertEqual((driver.visitas, driver.scripts), (["https://a"], []))

    def test_carga_agotada_para_la_pagina_y_no_reintenta(self):
        driver = DriverFalso(error_get=TimeoutException("lenta"))
        self.m.navegar(driver, "https://a")          # no debe lanzar
        self.assertEqual(driver.visitas, ["https://a"])
        self.assertEqual(driver.scripts, ["window.stop();"])

    def test_otros_errores_llegan_al_detector(self):
        with self.assertRaises(WebDriverException):
            self.m.navegar(DriverFalso(error_get=WebDriverException("caido")), "https://a")


class TestSesionViva(CasoMonitor):

    def test_viva(self):
        self.m.puerto_depuracion_activo = lambda: True
        self.assertTrue(self.m.sesion_viva(DriverFalso()))

    def test_puerto_caido_se_ve_muerta_sin_preguntar_a_chromedriver(self):
        self.m.puerto_depuracion_activo = lambda: False
        driver = DriverFalso(muerto=True)
        self.assertFalse(self.m.sesion_viva(driver))

    def test_error_no_selenium_cuenta_como_muerta(self):
        self.m.puerto_depuracion_activo = lambda: True
        self.assertFalse(self.m.sesion_viva(DriverFalso(muerto=True)))


class TestRecuperarSesion(CasoMonitor):

    def setUp(self):
        super().setUp()
        self.puerto = False
        self.lanzamientos = []
        self.lanzar_funciona = True
        self.conexion_posible_desde = 0          # hora a partir de la cual conecta
        self.m.puerto_depuracion_activo = lambda: self.puerto
        self.m.soltar_sesion = lambda driver: None

        def lanzar():
            self.lanzamientos.append(self.reloj.ahora)
            return self.lanzar_funciona

        def conectar():
            if self.reloj.ahora >= self.conexion_posible_desde:
                return DriverFalso("nuevo")
            return None

        self.m.lanzar_chrome = lanzar
        self.m.conectar_chrome = conectar

    def test_solo_se_perdio_la_sesion_reconecta_sin_relanzar_ni_avisar(self):
        self.puerto = True
        nuevo = self.m.recuperar_sesion(DriverFalso("viejo"))
        self.assertEqual(nuevo.nombre, "nuevo")
        self.assertEqual((self.lanzamientos, self.enviados), ([], []))

    def test_chrome_caido_se_relanza_y_avisa_una_vez(self):
        nuevo = self.m.recuperar_sesion(DriverFalso("viejo"))
        self.assertEqual(nuevo.nombre, "nuevo")
        self.assertEqual(len(self.lanzamientos), 1)
        self.assertEqual(len(self.enviados), 1)
        self.assertIn("relancé", self.enviados[0])
        self.assertNotIn("CIEGO", self.enviados[0])

    def test_si_no_se_puede_relanzar_avisa_ciego_y_luego_recuperada(self):
        self.lanzar_funciona = False
        inicio = self.reloj.ahora

        def dormir(segundos):            # el usuario abre Chrome al minuto
            self.reloj.ahora += segundos
            if self.reloj.ahora - inicio >= 60:
                self.puerto = True
        self.m.time.sleep = dormir

        self.m.recuperar_sesion(DriverFalso("viejo"))
        self.assertIn("CIEGO", self.enviados[0])
        self.assertIn("recuperada", self.enviados[-1])
        self.assertEqual(len(self.enviados), 2)

    def test_relanza_como_maximo_una_vez_cada_cinco_minutos(self):
        # Chrome no abre el puerto durante 15 minutos (p. ej. hay otra instancia
        # con el perfil del monitor sin modo debug): no debe abrir ventanas en bucle.
        inicio = self.reloj.ahora
        self.conexion_posible_desde = inicio + 900
        self.m.recuperar_sesion(DriverFalso("viejo"))
        relativos = [int(t - inicio) for t in self.lanzamientos]
        self.assertEqual(relativos, [0, 300, 600, 900])
        self.assertEqual(sum("CIEGO" in e for e in self.enviados), 1)
        self.assertIn("recuperada tras 15 min", self.enviados[-1])

    def test_aviso_de_ciego_fallido_se_reintenta(self):
        self.lanzar_funciona = False
        resultados = iter([False, True, True])
        inicio = self.reloj.ahora

        def enviar(mensaje):
            self.enviados.append(mensaje)
            return next(resultados)
        self.m.enviar_notificacion = enviar

        def dormir(segundos):
            self.reloj.ahora += segundos
            if self.reloj.ahora - inicio >= 90:
                self.puerto = True
        self.m.time.sleep = dormir

        self.m.recuperar_sesion(DriverFalso("viejo"))
        self.assertEqual(sum("CIEGO" in e for e in self.enviados), 2)
