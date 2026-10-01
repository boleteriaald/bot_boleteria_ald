"""
Integracion de la reserva en el monitor: solo URLs activadas, solo sectores
nuevos, pestana aparte y un aviso de Telegram con el resultado.
"""
from unittest import mock

import reserva_ticketmaster as rt
from apoyo import CasoMonitor

URL = "https://www.ticketmaster.co/event/carlos-vives-bucaramanga-venta-general"
OTRA = "https://www.ticketmaster.co/event/otro-evento"
SECTOR = "VIP (silletería no numerada)"


class Pestanas:
    def __init__(self, driver):
        self.driver = driver

    def new_window(self, tipo):
        self.driver.eventos.append(("nueva", tipo))
        self.driver.actual = "reserva"

    def window(self, handle):
        self.driver.eventos.append(("volver", handle))
        self.driver.actual = handle


class DriverFalso:
    nombre = "falso"

    def __init__(self):
        self.actual = "monitor"
        self.eventos = []
        self.switch_to = Pestanas(self)

    @property
    def current_window_handle(self):
        return self.actual

    def close(self):
        self.eventos.append(("cerrada", self.actual))


class Base(CasoMonitor):

    def setUp(self):
        super().setUp()
        self.m.configurar_registro()
        self.m.RESERVAR_TICKETMASTER = {URL: 4}
        self.m.RESERVA_PUERTO_DEPURACION = None     # por defecto, el Chrome del monitor
        self.m._ULTIMA_RESERVA.clear()
        self.m._NAVEGADOR_RESERVA.clear()
        self.llamadas = []
        self.resultado = rt.Reserva(True, SECTOR, 4, 4, "$ 1.527.000", "04:52")
        self.lanza = None

        def reservar(pagina, sectores, maximo=4, minimo=1, reloj=None):
            self.llamadas.append((list(sectores), maximo))
            if self.lanza:
                raise self.lanza
            return self.resultado

        patches = [mock.patch.object(rt, "reservar", reservar),
                   mock.patch.object(rt, "PaginaSelenium", lambda driver, url, cargar: object())]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)


class TestIntentarReserva(Base):

    def test_url_no_activada_no_reserva_ni_abre_pestana(self):
        d = DriverFalso()
        self.assertIsNone(self.m.intentar_reserva(d, OTRA, [SECTOR], "E"))
        self.assertEqual((self.llamadas, d.eventos, self.enviados), ([], [], []))

    def test_reserva_ok_en_pestana_nueva_la_deja_abierta_y_avisa(self):
        d = DriverFalso()
        self.m.intentar_reserva(d, URL, [SECTOR], "Carlos Vives")
        self.assertEqual(self.llamadas, [([SECTOR], 4)])
        self.assertEqual(d.eventos, [("nueva", "tab"), ("volver", "monitor")])   # sin cerrar
        self.assertEqual(len(self.enviados), 1)
        self.assertIn("RESERVA LISTA", self.enviados[0])
        self.assertIn("RESERVA OK", self.leer_registro())

    def test_fallo_limpio_cierra_la_pestana_y_avisa(self):
        self.resultado = rt.Reserva(False, SECTOR, detalle="no hay boletas ni para 1 en este momento")
        d = DriverFalso()
        self.m.intentar_reserva(d, URL, [SECTOR], "E")
        self.assertEqual(d.eventos, [("nueva", "tab"), ("cerrada", "reserva"), ("volver", "monitor")])
        self.assertIn("NO PUDE RESERVAR", self.enviados[0])

    def test_fallo_con_boletas_retenidas_no_cierra_la_pestana(self):
        self.resultado = rt.Reserva(False, SECTOR, 4, 4, detalle="la pagina no avanza", retenidas=True)
        d = DriverFalso()
        self.m.intentar_reserva(d, URL, [SECTOR], "E")
        self.assertNotIn(("cerrada", "reserva"), d.eventos)
        self.assertEqual(d.actual, "monitor")

    def test_un_error_inesperado_no_tumba_al_monitor_y_devuelve_la_pestana(self):
        self.lanza = RuntimeError("boom")
        d = DriverFalso()
        r = self.m.intentar_reserva(d, URL, [SECTOR], "E")
        self.assertFalse(r.ok)
        self.assertEqual(d.actual, "monitor")
        self.assertIn("NO PUDE RESERVAR", self.enviados[0])
        self.assertIn("boom", self.enviados[0])

    def test_aviso_sin_detalle_no_dispara_reserva(self):
        d = DriverFalso()
        self.m.intentar_reserva(d, URL, ["Evento - venta abierta " + self.m.MARCADOR_SIN_DETALLE], "E")
        self.assertEqual((self.llamadas, d.eventos), ([], []))

    def test_no_reserva_dos_veces_seguidas_el_mismo_evento(self):
        d = DriverFalso()
        self.m.intentar_reserva(d, URL, [SECTOR], "E")
        self.m.intentar_reserva(d, URL, [SECTOR], "E")
        self.assertEqual(len(self.llamadas), 1)
        self.reloj.ahora += self.m.INTERVALO_RECORDATORIO + 1
        self.m.intentar_reserva(d, URL, [SECTOR], "E")
        self.assertEqual(len(self.llamadas), 2)

    def test_un_fallo_limpio_si_puede_reintentarse(self):
        self.resultado = rt.Reserva(False, SECTOR, detalle="sin boletas")
        d = DriverFalso()
        self.m.intentar_reserva(d, URL, [SECTOR], "E")
        self.m.intentar_reserva(d, URL, [SECTOR], "E")
        self.assertEqual(len(self.llamadas), 2)


BTS = "https://www.ticketmaster.co/event/bts-world-tour-venta-general-sabado-3-octubre"


class TestReservaPorSector(Base):
    """RESERVAR_TICKETMASTER admite {"maximo", "sectores"}: se avisa de todo, se reserva solo eso."""

    def setUp(self):
        super().setUp()
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4, "sectores": ["GRAMILLA"]}}

    def test_reserva_solo_el_sector_que_coincide(self):
        d = DriverFalso()
        self.m.intentar_reserva(d, BTS, ["OCCIDENTAL BAJA", "VIP (GRAMILLA)", "SUR ALTA"], "BTS")
        self.assertEqual(self.llamadas, [(["VIP (GRAMILLA)"], 4)])

    def test_coincide_sin_importar_mayusculas_ni_parentesis(self):
        self.m.intentar_reserva(DriverFalso(), BTS, ["Vip - Gramilla"], "BTS")
        self.assertEqual(self.llamadas, [(["Vip - Gramilla"], 4)])

    def test_si_ninguno_coincide_no_reserva_ni_abre_pestana(self):
        d = DriverFalso()
        self.assertIsNone(self.m.intentar_reserva(d, BTS, ["OCCIDENTAL BAJA", "SUR ALTA"], "BTS"))
        self.assertEqual((self.llamadas, d.eventos, self.enviados), ([], [], []))
        self.assertIn("ningun sector nuevo coincide", self.leer_registro())

    def test_el_maximo_sale_del_dict(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 2, "sectores": ["GRAMILLA"]}}
        self.m.intentar_reserva(DriverFalso(), BTS, ["VIP (GRAMILLA)"], "BTS")
        self.assertEqual(self.llamadas, [(["VIP (GRAMILLA)"], 2)])

    def test_un_dict_sin_sectores_reserva_todos_los_que_lleguen(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4}}
        self.m.intentar_reserva(DriverFalso(), BTS, ["A", "B"], "BTS")
        self.assertEqual(self.llamadas, [(["A", "B"], 4)])

    def test_el_nombre_viene_del_catalogo_el_filtro_de_avisos_no_interviene(self):
        # No hay FILTROS_LOCALIDADES para BTS: se avisa de todo y la reserva elige sola.
        self.assertNotIn(BTS, self.m.FILTROS_LOCALIDADES)

    def test_pestana_en_fila_de_queue_it_no_se_cierra(self):
        self.resultado = rt.Reserva(False, detalle="este navegador quedo en la fila de Queue-it",
                                    conservar_pestana=True)
        d = DriverFalso()
        self.m.intentar_reserva(d, BTS, ["VIP (GRAMILLA)"], "BTS")
        self.assertNotIn(("cerrada", "reserva"), d.eventos)
        self.assertEqual(d.actual, "monitor")
        self.assertIn("NO PUDE RESERVAR", self.enviados[0])


class TestNavegadorDeReserva(Base):
    """Con RESERVA_PUERTO_DEPURACION se reserva en otro navegador, no en el del monitor."""

    def setUp(self):
        super().setUp()
        self.m.RESERVA_PUERTO_DEPURACION = 9223

    def test_reserva_en_el_otro_navegador_y_no_toca_el_del_monitor(self):
        monitor, comet = DriverFalso(), DriverFalso()
        comet.actual = "comet-principal"
        self.m.navegador_reserva = lambda d: (comet, None)
        self.m.intentar_reserva(monitor, URL, [SECTOR], "E")
        self.assertEqual(monitor.eventos, [])
        self.assertEqual(comet.eventos, [("nueva", "tab"), ("volver", "comet-principal")])
        self.assertIn("RESERVA LISTA", self.enviados[0])

    def test_puerto_cerrado_avisa_sin_tocar_chromedriver(self):
        self.m.puerto_depuracion_activo = lambda puerto=None: False
        d = DriverFalso()
        r = self.m.intentar_reserva(d, URL, [SECTOR], "E")
        self.assertFalse(r.ok)
        self.assertEqual(d.eventos, [])
        self.assertEqual(self.llamadas, [])
        self.assertIn("iniciar_comet_debug.bat", self.enviados[0])
        self.assertIn("9223", self.enviados[0])

    def test_fallo_de_conexion_no_tumba_el_monitor(self):
        self.m.puerto_depuracion_activo = lambda puerto=None: True
        with mock.patch.object(self.m.urllib.request, "urlopen", side_effect=OSError("sin red")):
            r = self.m.intentar_reserva(DriverFalso(), URL, [SECTOR], "E")
        self.assertFalse(r.ok)
        self.assertIn("no pude conectar", self.enviados[0])

    def test_sin_puerto_configurado_usa_el_driver_del_monitor(self):
        self.m.RESERVA_PUERTO_DEPURACION = None
        d = DriverFalso()
        self.assertEqual(self.m.navegador_reserva(d), (d, None))

    def test_chromedriver_de_la_misma_version_mayor(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as casa:
            base = os.path.join(casa, ".cache", "selenium", "chromedriver", "win64")
            for version in ("152.0.7977.82", "153.0.8010.52", "154.0.8037.92"):
                os.makedirs(os.path.join(base, version))
                open(os.path.join(base, version, "chromedriver.exe"), "w").close()
            with mock.patch("os.path.expanduser", lambda ruta: casa):
                elegido = self.m._chromedriver_para("153.0.8010.224")
                self.assertIn("153.0.8010.52", elegido)
                self.assertIsNone(self.m._chromedriver_para("99.0.1.1"))


class TestEnElBucle(Base):

    def setUp(self):
        super().setUp()
        self.m.URLS_A_MONITOREAR = [URL, OTRA]
        self.m.FILTROS_LOCALIDADES = {}
        self.visitas = 0
        self.m.detectar_bloqueo = lambda driver: (False, None)
        self.m.obtener_nombre_evento = lambda driver: "Evento"
        self.m.obtener_fecha_evento = lambda driver: None
        self.m.sesion_viva = lambda driver: True

        def detector(driver, url):
            self.visitas += 1
            return [SECTOR], [], url
        self.m.verificar_disponibilidad_ticketmaster = detector

    def correr(self, rondas):
        guardar_real = self.m.guardar_estado

        def guardar(estado):
            guardar_real(estado)
            if self.visitas >= rondas * 2:
                raise KeyboardInterrupt
        self.m.guardar_estado = guardar
        try:
            self.m.monitorear_urls(DriverFalso())
        except KeyboardInterrupt:
            pass

    def test_reserva_una_vez_por_sector_nuevo_y_solo_en_la_url_activada(self):
        self.correr(3)
        self.assertEqual(self.llamadas, [([SECTOR], 4)])      # 3 rondas, 2 URLs: una sola reserva

    def test_el_aviso_de_disponibilidad_sale_antes_que_el_de_reserva(self):
        self.correr(1)
        self.assertIn("DISPONIBILIDAD DETECTADA", self.enviados[0])
        self.assertIn("RESERVA LISTA", self.enviados[1])

    def test_sin_url_activada_el_monitor_solo_observa(self):
        self.m.RESERVAR_TICKETMASTER = {}
        self.correr(1)
        self.assertEqual(self.llamadas, [])
        self.assertEqual(len(self.enviados), 2)               # un aviso por URL, nada mas
