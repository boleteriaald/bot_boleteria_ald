"""RESERVAR_TICKETMASTER["excluir"] y la configuracion real de Don Omar.

Solo corre con un script que lo tenga (monitor_todas_las_urls.py); con otro se omite.
"""
import inspect

from apoyo import cargar_monitor
from test_reserva_monitor import Base, DriverFalso

URL = "https://www.ticketmaster.co/event/prueba-excluir"
MEDELLIN = ["Norte", "Palco Platino Sur", "Occidental", "Palco Oro Norte", "KINGDOM VIP 1"]

URLS_DON_OMAR = [
    "https://www.ticketmaster.co/event/don-omar-bogota-preventa-artista",
    "https://www.ticketmaster.co/event/don-omar-cali-preventa-artista",
    "https://www.ticketmaster.co/event/don-omar-medellin-preventa-artista-fecha-2",
    "https://www.ticketmaster.co/event/don-omar-medellin-preventa-artista",
    "https://www.ticketmaster.co/event/don-omar-cali-venta-general",
    "https://www.ticketmaster.co/event/don-omar-medellin-venta-general-fecha-2",
    "https://www.ticketmaster.co/event/don-omar-medellin-venta-general",
]


class TestExcluirEnLaReserva(Base):

    def setUp(self):
        super().setUp()
        if "excluir" not in inspect.getsource(self.m.intentar_reserva):
            self.skipTest("este script no tiene 'excluir' en la reserva")

    def reservar(self, config, sectores):
        self.m.RESERVAR_TICKETMASTER = {URL: config}
        return self.m.intentar_reserva(DriverFalso(), URL, sectores, "Don Omar")

    def test_sin_excluir_reserva_todo(self):
        self.reservar({"maximo": 4}, MEDELLIN)
        self.assertEqual(self.llamadas[0][0], MEDELLIN)

    def test_excluir_palco_no_reserva_palcos_y_conserva_el_orden(self):
        self.reservar({"maximo": 4, "excluir": ["palco"]}, MEDELLIN)
        self.assertEqual(self.llamadas[0][0], ["Norte", "Occidental", "KINGDOM VIP 1"])

    def test_si_solo_hay_palcos_no_reserva_nada_ni_abre_pestana(self):
        d = DriverFalso()
        self.m.RESERVAR_TICKETMASTER = {URL: {"maximo": 4, "excluir": ["palco"]}}
        self.assertIsNone(self.m.intentar_reserva(d, URL, ["Palco Oro Norte", "Palcos Plata x 10"], "E"))
        self.assertEqual((self.llamadas, d.eventos, self.enviados), ([], [], []))

    def test_excluir_se_combina_con_las_palabras_de_sectores(self):
        self.reservar({"maximo": 4, "sectores": ["norte", "kingdom"], "excluir": ["palco"]}, MEDELLIN)
        self.assertEqual(self.llamadas[0][0], ["Norte", "KINGDOM VIP 1"])

    def test_palabra_vacia_en_excluir_no_descarta_todo(self):
        self.reservar({"maximo": 4, "excluir": ["-", ""]}, MEDELLIN)
        self.assertEqual(self.llamadas[0][0], MEDELLIN)


class TestConfiguracionDonOmar(Base):

    def test_las_siete_urls_reservan_sin_palcos_y_estan_en_la_lista(self):
        real = cargar_monitor(self._carpeta.name)
        if "excluir" not in inspect.getsource(real.intentar_reserva):
            self.skipTest("este script no tiene 'excluir' en la reserva")
        for url in URLS_DON_OMAR:
            with self.subTest(url=url):
                config = real.RESERVAR_TICKETMASTER[url]       # la clave debe existir tal cual
                self.assertIn(url, real.URLS_A_MONITOREAR)     # y la URL, estar vigilada
                self.assertEqual(config["maximo"], 4)
                self.assertEqual(config["max_reservas"], 8)
                self.assertEqual(config["excluir"], ["palco"])

    def test_la_pagina_indice_de_bogota_no_reserva(self):
        real = cargar_monitor(self._carpeta.name)
        self.assertNotIn("https://www.ticketmaster.co/event/don-omar-bogota-2027",
                         real.RESERVAR_TICKETMASTER)
