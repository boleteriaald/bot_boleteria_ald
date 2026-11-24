"""Vigilancia de botones de una pagina indice de Ticketmaster (VIGILAR_BOTONES).

Solo corre con un script que la tenga (monitor_todas_las_urls.py); con otro se omite.
"""
import unittest

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from apoyo import CasoMonitor

URL = "https://www.ticketmaster.co/event/prueba-indice-2027"
PREVENTA = {"texto": "PREVENTA FANS", "enlace": "https://www.ticketmaster.co/event/prueba-preventa-artista"}
TYC = {"texto": "TÉRMINOS Y CONDICIONES", "enlace": "https://www.ticketmaster.co/event/prueba-tyc"}
GENERAL = {"texto": "Venta  General", "enlace": "https://www.ticketmaster.co/event/prueba-venta-general"}


class Elemento:
    def __init__(self, texto):
        self.text = texto


class DriverFalso:
    """Pagina indice: sin catalogo (App sin sectores) y con los botones que se le den."""

    def __init__(self, botones, texto="Don Omar\nACERCA DE\nTerminos", falla_js=False):
        self.botones = botones
        self.texto = texto
        self.falla_js = falla_js
        self.current_url = URL
        self.title = "Prueba"
        self.scripts = 0

    def get(self, url):
        pass

    def execute_script(self, script):
        self.scripts += 1
        if "block_buttons" in script:
            if self.falla_js:
                raise RuntimeError("js roto")
            return list(self.botones)
        return None

    def find_element(self, by, valor):
        if by == By.TAG_NAME and valor == "body":
            return Elemento(self.texto)
        raise NoSuchElementException(valor)


class TestVigilarBotones(CasoMonitor):

    def setUp(self):
        super().setUp()
        if not hasattr(self.m, "VIGILAR_BOTONES"):
            self.skipTest("este script no tiene VIGILAR_BOTONES")
        self.m.VIGILAR_BOTONES = {URL: ["venta general"]}
        self.m.obtener_nombre_evento = lambda driver: "Don Omar - Prueba"
        self.estado = {}

    def vigilar(self, driver):
        self.m.vigilar_botones(driver, URL, self.estado)

    def test_sin_boton_de_venta_no_avisa(self):
        self.vigilar(DriverFalso([PREVENTA, TYC]))
        self.assertEqual(self.enviados, [])

    def test_boton_nuevo_avisa_con_su_enlace(self):
        self.vigilar(DriverFalso([PREVENTA, TYC, GENERAL]))
        self.assertEqual(len(self.enviados), 1)
        self.assertIn(GENERAL["enlace"], self.enviados[0])
        self.assertIn("Venta  General", self.enviados[0])
        self.assertNotIn(PREVENTA["enlace"], self.enviados[0])

    def test_no_repite_el_aviso_ni_con_recordatorio(self):
        driver = DriverFalso([GENERAL])
        self.vigilar(driver)
        self.reloj.sleep(self.m.INTERVALO_RECORDATORIO * 3)
        self.vigilar(driver)
        self.assertEqual(len(self.enviados), 1)

    def test_si_telegram_falla_reintenta_en_la_ronda_siguiente(self):
        driver = DriverFalso([GENERAL])
        self.telegram_funciona = False
        self.vigilar(driver)
        self.telegram_funciona = True
        self.vigilar(driver)
        self.assertEqual(len(self.enviados), 2)
        self.vigilar(driver)
        self.assertEqual(len(self.enviados), 2)

    def test_un_parpadeo_de_la_pagina_no_reavisa(self):
        self.vigilar(DriverFalso([GENERAL]))
        self.vigilar(DriverFalso([]))
        self.vigilar(DriverFalso([GENERAL]))
        self.assertEqual(len(self.enviados), 1)

    def test_un_segundo_boton_distinto_si_avisa(self):
        self.vigilar(DriverFalso([GENERAL]))
        otro = {"texto": "VENTA GENERAL - 2 DE OCTUBRE", "enlace": "https://x/otra-venta"}
        self.vigilar(DriverFalso([GENERAL, otro]))
        self.assertEqual(len(self.enviados), 2)
        self.assertIn("https://x/otra-venta", self.enviados[1])

    def test_error_de_javascript_no_rompe_ni_avisa(self):
        self.vigilar(DriverFalso([GENERAL], falla_js=True))
        self.assertEqual(self.enviados, [])

    def test_pagina_indice_sin_catalogo_no_avisa_de_prefila(self):
        driver = DriverFalso([PREVENTA])
        disponibles, agotadas, _ = self.m.verificar_disponibilidad_ticketmaster(driver, URL)
        self.assertEqual(disponibles, [])
        self.assertEqual(agotadas, ["Don Omar - Prueba"])

    def test_la_url_real_de_bogota_esta_vigilada_y_en_la_lista(self):
        url = "https://www.ticketmaster.co/event/don-omar-bogota-2027"
        import importlib
        real = importlib.import_module("apoyo").cargar_monitor(self._carpeta.name)
        self.assertIn(url, real.VIGILAR_BOTONES)
        self.assertIn(url, real.URLS_A_MONITOREAR)


if __name__ == "__main__":
    unittest.main()
