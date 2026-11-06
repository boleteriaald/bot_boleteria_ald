"""Eleventickets: aviso cuando aparece un boton nuevo de inicio de sesion (p. ej. socios de Boca)."""
from apoyo import CasoMonitor

URL = "https://sudamericana.eleventickets.com/#!/apresentacao/abc"
HOY = ["SOCIO DE ATL&Eacute;TICO MINEIRO", "HINCHA DE ATL&Eacute;TICO MINEIRO",
       "HINCHA DE BOCA JUNIORS", "HINCHA NEUTRO"]


class DriverFalso:
    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.scripts = []

    def execute_async_script(self, script):
        self.scripts.append(script)
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


class TestBotonesLogin(CasoMonitor):

    def setUp(self):
        super().setUp()
        self.m.BOTONES_LOGIN_CONOCIDOS = ["SOCIO DE ATLÉTICO MINEIRO", "HINCHA DE ATLÉTICO MINEIRO",
                                          "HINCHA DE BOCA JUNIORS", "HINCHA NEUTRO"]
        self.m._BOTONES_LOGIN_AVISADOS = set()

    def test_los_botones_de_siempre_no_avisan(self):
        self.assertEqual(self.m.revisar_botones_login(DriverFalso(HOY), URL), [])
        self.assertEqual(self.enviados, [])

    def test_boton_nuevo_avisa_una_sola_vez(self):
        driver = DriverFalso(HOY + ["SOCIO DE BOCA JUNIORS"])
        self.assertEqual(self.m.revisar_botones_login(driver, URL), ["SOCIO DE BOCA JUNIORS"])
        self.assertEqual(self.m.revisar_botones_login(driver, URL), [])
        self.assertEqual(len(self.enviados), 1)
        self.assertIn("SOCIO DE BOCA JUNIORS", self.enviados[0])
        self.assertIn("HINCHA NEUTRO", self.enviados[0])
        self.assertIn(URL, self.enviados[0])

    def test_entidades_html_y_tildes_no_cuentan_como_nuevo(self):
        driver = DriverFalso(["Socio de Atletico Mineiro", "HINCHA  NEUTRO"])
        self.assertEqual(self.m.revisar_botones_login(driver, URL), [])

    def test_si_telegram_falla_se_reintenta_en_la_siguiente_lectura(self):
        resultados = iter([False, True])

        def enviar(mensaje):
            self.enviados.append(mensaje)
            return next(resultados)
        self.m.enviar_notificacion = enviar
        driver = DriverFalso(HOY + ["SOCIO DE BOCA JUNIORS"])
        self.m.revisar_botones_login(driver, URL)
        self.m.revisar_botones_login(driver, URL)
        self.m.revisar_botones_login(driver, URL)
        self.assertEqual(len(self.enviados), 2)

    def test_lista_ilegible_o_error_no_avisa_ni_lanza(self):
        for respuesta in (None, [], RuntimeError("sin angular")):
            self.assertEqual(self.m.revisar_botones_login(DriverFalso(respuesta), URL), [])
        self.assertEqual(self.enviados, [])
