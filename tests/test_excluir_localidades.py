"""EXCLUIR_LOCALIDADES: "todo menos palcos" con los nombres reales del catalogo de Don Omar.

Solo corre con un script que la tenga (monitor_todas_las_urls.py); con otro se omite.
"""
from apoyo import CasoMonitor

URL = "https://www.ticketmaster.co/event/prueba-excluir"

# Nombres tal como salen del catalogo de las preventas (24-nov-2026).
MEDELLIN = ["Norte", "Palco Platino Sur", "Occidental", "Palco Oro Norte", "KINGDOM VIP 1"]
CALI = ["Palcos Plata  x 10 - Oriental (Mayores + 18)", "Oriental - Baja (Mayores +18)",
        "Kingdom - VIP 1 Occidental (Mayores +18)", "Palcos Rubí  x 10 - Occidental (Mayores + 18)"]
BOGOTA = ["101 - 103 - 105 - 107  (Mayores +18)", "Palco Bronce - Oriental (Mayores +18)",
          "Kingdom VIP 2"]


class TestExcluirLocalidades(CasoMonitor):

    def setUp(self):
        super().setUp()
        if not hasattr(self.m, "EXCLUIR_LOCALIDADES"):
            self.skipTest("este script no tiene EXCLUIR_LOCALIDADES")
        self.m.EXCLUIR_LOCALIDADES = {URL: ["palco"]}
        self.m.FILTROS_LOCALIDADES = {}

    def test_sin_filtro_descarta_solo_los_palcos(self):
        self.assertEqual(self.m.filtrar_localidades(MEDELLIN, URL),
                         ["Norte", "Occidental", "KINGDOM VIP 1"])
        self.assertEqual(self.m.filtrar_localidades(CALI, URL),
                         ["Oriental - Baja (Mayores +18)",
                          "Kingdom - VIP 1 Occidental (Mayores +18)"])
        self.assertEqual(self.m.filtrar_localidades(BOGOTA, URL),
                         ["101 - 103 - 105 - 107  (Mayores +18)", "Kingdom VIP 2"])

    def test_palco_escrito_con_tilde_y_plural_tambien(self):
        self.m.EXCLUIR_LOCALIDADES = {URL: ["PALCÓ"]}
        self.assertEqual(self.m.filtrar_localidades(["Palcos Oro", "Norte"], URL), ["Norte"])

    def test_se_combina_con_el_filtro_por_localidad(self):
        self.m.FILTROS_LOCALIDADES = {URL: ["norte"]}
        self.assertEqual(self.m.filtrar_localidades(MEDELLIN, URL), ["Norte"])

    def test_otra_url_no_se_toca(self):
        self.assertEqual(self.m.filtrar_localidades(MEDELLIN, URL + "-otra"), MEDELLIN)

    def test_un_aviso_sin_detalle_nunca_se_descarta(self):
        sin_detalle = f"Don Omar Palco - venta abierta {self.m.MARCADOR_SIN_DETALLE}"
        self.assertEqual(self.m.filtrar_localidades([sin_detalle], URL), [sin_detalle])

    def test_palabra_vacia_no_descarta_todo(self):
        self.m.EXCLUIR_LOCALIDADES = {URL: ["-", ""]}
        self.assertEqual(self.m.filtrar_localidades(MEDELLIN, URL), MEDELLIN)

    def test_las_urls_reales_de_don_omar_excluyen_palcos(self):
        from apoyo import cargar_monitor
        real = cargar_monitor(self._carpeta.name)
        for url in ("https://www.ticketmaster.co/event/don-omar-medellin-venta-general",
                    "https://www.ticketmaster.co/event/don-omar-medellin-venta-general-fecha-2",
                    "https://www.ticketmaster.co/event/don-omar-cali-venta-general",
                    "https://www.ticketmaster.co/event/don-omar-bogota-preventa-artista",
                    "https://www.ticketmaster.co/event/don-omar-cali-preventa-artista",
                    "https://www.ticketmaster.co/event/don-omar-medellin-preventa-artista",
                    "https://www.ticketmaster.co/event/don-omar-medellin-preventa-artista-fecha-2"):
            with self.subTest(url=url):
                self.assertIn(url, real.URLS_A_MONITOREAR)
                self.assertEqual(real.filtrar_localidades(["Palco Oro Norte", "Norte"], url), ["Norte"])


if __name__ == "__main__":
    import unittest
    unittest.main()
