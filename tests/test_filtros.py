"""Filtros de localidades: coincidencia parcial y normalizacion de nombres."""
from apoyo import CasoMonitor

URL = "https://evento/prueba"


class TestFiltros(CasoMonitor):

    def filtrar(self, filtro, disponibles):
        self.m.FILTROS_LOCALIDADES = {URL: filtro}
        return self.m.filtrar_localidades(disponibles, URL)

    def test_sin_filtro_pasa_todo(self):
        self.m.FILTROS_LOCALIDADES = {}
        self.assertEqual(self.m.filtrar_localidades(["A", "B"], URL), ["A", "B"])

    def test_filtro_vacio_pasa_todo(self):
        self.assertEqual(self.filtrar([], ["A", "B"]), ["A", "B"])

    def test_coincidencia_parcial(self):
        disponibles = ["Platea 1 (Mayores +18)", "Platea 2 (Mayores +18)", "117-118-119-120"]
        self.assertEqual(self.filtrar(["PLATEA"], disponibles), disponibles[:2])

    def test_filtro_especifico(self):
        self.assertEqual(self.filtrar(["PLATEA 1"], ["Platea 1", "Platea 2"]), ["Platea 1"])

    def test_numero_dentro_de_un_rango(self):
        self.assertEqual(self.filtrar(["119"], ["117-118-119-120"]), ["117-118-119-120"])

    def test_ignora_espacios_dobles(self):
        # Nombre real de Mana, escrito a mano con doble espacio
        self.assertEqual(self.filtrar(["PLATEA E PARES"], ["Platea E  Pares (Mayores +18)"]),
                         ["Platea E  Pares (Mayores +18)"])

    def test_ignora_separadores(self):
        self.assertEqual(self.filtrar(["106 - 108"], ["102 - 104 - 106 -108"]), ["102 - 104 - 106 -108"])
        self.assertEqual(self.filtrar(["110, 112"], ["110 - 112 - 114 - 116"]), ["110 - 112 - 114 - 116"])

    def test_ignora_tildes(self):
        self.assertEqual(self.filtrar(["GRADERIA"], ["Gradería Norte"]), ["Gradería Norte"])

    def test_palabra_clave_vacia_no_coincide_con_todo(self):
        self.assertEqual(self.filtrar(["-"], ["Platea A"]), [])

    def test_avisos_sin_detalle_se_saltan_el_filtro(self):
        aviso = f"Evento - venta abierta {self.m.MARCADOR_SIN_DETALLE}"
        self.assertEqual(self.filtrar(["PLATEA"], [aviso, "Sur"]), [aviso])

    def test_nombres_contenidos_en_otros(self):
        # Comportamiento conocido y documentado: la coincidencia es parcial
        disponibles = ["Norte Baja (+7)", "Oriental Norte Baja (+7)"]
        self.assertEqual(self.filtrar(["NORTE BAJA"], disponibles), disponibles)

    def test_normalizar_nombre(self):
        self.assertEqual(self.m.normalizar_nombre("  Platea  É - 1 / A,B "), "platea e 1 a b")
