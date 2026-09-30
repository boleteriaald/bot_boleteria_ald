"""Ticketmaster sin catalogo: fila de Queue-it, pre-fila y agotados reales."""
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from apoyo import CasoMonitor

URL = "https://www.ticketmaster.co/event/prueba-venta-general"
URL_COLA = ("https://ticketmasterco.queue-it.net/?c=ticketmasterco&e=prueba"
            "&cid=es-ES&enqueuetoken=abc")


class Elemento:
    def __init__(self, texto):
        self.text = texto


class DriverFalso:
    """Pagina fija, sin catalogo en App: obliga a pasar por la reserva por texto."""

    def __init__(self, texto, url_actual=URL, con_boton=False):
        self.texto = texto
        self.current_url = url_actual
        self.title = "Ticketmaster"
        self.con_boton = con_boton

    def get(self, url):
        pass

    def execute_script(self, script):
        return None

    def find_element(self, by, valor):
        if by == By.TAG_NAME and valor == "body":
            return Elemento(self.texto)
        if by == By.XPATH and "Ver entradas" in valor and self.con_boton:
            return Elemento("Ver entradas")
        raise NoSuchElementException(valor)


class TestTicketmasterSinCatalogo(CasoMonitor):

    def setUp(self):
        super().setUp()
        self.m.obtener_nombre_evento = lambda driver: "Evento"

    def leer(self, driver):
        disponibles, agotadas, _ = self.m.verificar_disponibilidad_ticketmaster(driver, URL)
        return disponibles, agotadas

    def test_queue_it_por_dominio_aunque_el_texto_sea_largo(self):
        texto = "Texto de la fila sin ninguna frase conocida. " * 100
        self.assertGreater(len(texto), self.m.LONGITUD_MAXIMA_PAGINA_ESPERA)
        disponibles, agotadas = self.leer(DriverFalso(texto, url_actual=URL_COLA))
        self.assertEqual(len(disponibles), 1)
        self.assertIn("SALA DE ESPERA", disponibles[0])
        self.assertIn(self.m.MARCADOR_SIN_DETALLE, disponibles[0])
        self.assertEqual(agotadas, [])

    def test_queue_it_gana_aunque_la_pagina_diga_agotado(self):
        disponibles, _ = self.leer(DriverFalso("AGOTADO", url_actual=URL_COLA))
        self.assertIn("SALA DE ESPERA", disponibles[0])

    def test_pagina_sin_agotado_ni_boton_avisa_posible_prefila(self):
        texto = "BTS WORLD TOUR - La venta comienza pronto. " * 80
        disponibles, agotadas = self.leer(DriverFalso(texto))
        self.assertEqual(len(disponibles), 1)
        self.assertIn("pre-fila", disponibles[0])
        self.assertIn(self.m.MARCADOR_SIN_DETALLE, disponibles[0])
        self.assertEqual(agotadas, [])

    def test_agotado_sigue_siendo_agotado(self):
        self.assertEqual(self.leer(DriverFalso("BTS\nAGOTADO\nTerminos")), ([], ["Evento"]))

    def test_evento_finalizado_no_avisa(self):
        self.assertEqual(self.leer(DriverFalso("EVENTO FINALIZADO\nTerminos " * 50)),
                         ([], ["Evento"]))

    def test_pagina_vacia_no_avisa(self):
        self.assertEqual(self.leer(DriverFalso("")), ([], ["Evento"]))

    def test_boton_ver_entradas_sigue_avisando_venta_abierta(self):
        disponibles, _ = self.leer(DriverFalso("Evento\nVer entradas " * 50, con_boton=True))
        self.assertIn("venta abierta", disponibles[0])
