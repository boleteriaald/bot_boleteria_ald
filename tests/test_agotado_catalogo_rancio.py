"""Catalogo rancio: la pagina dice AGOTADO y no deja comprar, pero el catalogo marca localidades libres.

Caso real: preventa de Don Omar en Bogota (25-nov-2026). El monitor avisaba cada 10 min de
"101 - 103 - 105 - 107" y la reserva fallaba porque la pagina no mostraba ni "Ver entradas".
Solo corre con un script que lo tenga (monitor_todas_las_urls.py); con otro se omite.
"""
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from apoyo import CasoMonitor

URL = "https://www.ticketmaster.co/event/prueba-preventa-artista"
CATALOGO = {"origen": "estado", "sectores": [
    {"nombre": "101 - 103 - 105 - 107", "disponible": True, "secciones": ["101"], "totalSecciones": 4},
    {"nombre": "Palco Oro", "disponible": True, "secciones": ["1"], "totalSecciones": 50},
    {"nombre": "Norte", "disponible": False, "secciones": [], "totalSecciones": 1},
]}


class Elemento:
    def __init__(self, texto):
        self.text = texto


class DriverFalso:
    def __init__(self, texto, con_compra=False):
        self.texto = texto
        self.con_compra = con_compra
        self.current_url = URL
        self.title = "Ticketmaster"

    def get(self, url):
        pass

    def execute_script(self, script):
        if "ver entrada|comprar entradas" in script:
            return self.con_compra
        if "window.App" in script:
            return CATALOGO
        return None

    def find_element(self, by, valor):
        if by == By.TAG_NAME and valor == "body":
            return Elemento(self.texto)
        raise NoSuchElementException(valor)


class TestCatalogoRancio(CasoMonitor):

    def setUp(self):
        super().setUp()
        if not hasattr(self.m, "_agotado_sin_compra"):
            self.skipTest("este script no ignora el catalogo rancio")
        self.m.obtener_nombre_evento = lambda driver: "Don Omar - Bogota"

    def leer(self, driver):
        disponibles, agotadas, _ = self.m.verificar_disponibilidad_ticketmaster(driver, URL)
        return disponibles, agotadas

    def test_agotado_en_la_cabecera_sin_boton_ignora_el_catalogo(self):
        disponibles, agotadas = self.leer(DriverFalso("Don Omar - Bogotá | 04 de Noviembre\nAGOTADO\nTérminos"))
        self.assertEqual(disponibles, [])
        self.assertEqual(agotadas, ["101 - 103 - 105 - 107", "Palco Oro", "Norte"])

    def test_con_boton_ver_entradas_el_catalogo_manda(self):
        disponibles, _ = self.leer(DriverFalso("Don Omar - Bogotá\nAGOTADO\nTérminos", con_compra=True))
        self.assertEqual(disponibles, ["101 - 103 - 105 - 107", "Palco Oro"])

    def test_sin_rotulo_agotado_el_catalogo_manda(self):
        disponibles, _ = self.leer(DriverFalso("Don Omar - Cali | 5 de noviembre\n6 sectores disponibles\nVer entradas"))
        self.assertEqual(disponibles, ["101 - 103 - 105 - 107", "Palco Oro"])

    def test_la_palabra_agotado_en_los_terminos_no_cuenta(self):
        texto = "Don Omar - Cali\nVer entradas\n" + "Venta adicional 6/10: AGOTADO\n" * 3
        disponibles, _ = self.leer(DriverFalso(texto))
        self.assertEqual(len(disponibles), 2)

    def test_agotado_dentro_de_una_frase_de_la_cabecera_no_cuenta(self):
        disponibles, _ = self.leer(DriverFalso("Don Omar\nTodo AGOTADO en la zona norte\nOtra linea"))
        self.assertEqual(len(disponibles), 2)

    def test_si_no_se_puede_leer_la_pagina_el_catalogo_manda(self):
        class Roto(DriverFalso):
            def find_element(self, by, valor):
                raise RuntimeError("sesion rota")
        # Directo sobre la ayuda: verificar_disponibilidad_ticketmaster ya falla antes, en
        # detectar_bloqueo, con una pagina que no se puede leer.
        self.assertFalse(self.m._agotado_sin_compra(Roto("AGOTADO")))


if __name__ == "__main__":
    import unittest
    unittest.main()
