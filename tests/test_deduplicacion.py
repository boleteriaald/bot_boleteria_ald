"""Deduplicacion de avisos: cuando se avisa, cuando se calla y el reintento."""
from apoyo import CasoMonitor

URL = "https://evento/prueba"


class TestDeduplicacion(CasoMonitor):

    def notificar(self, disponibles):
        return self.m.localidades_a_notificar(self.estado, URL, disponibles)

    def setUp(self):
        super().setUp()
        self.estado = {}

    def test_localidad_nueva_se_avisa(self):
        nuevas, recordatorios, silencio = self.notificar(["119"])
        self.assertEqual((nuevas, recordatorios, silencio), (["119"], [], []))

    def test_localidad_ya_avisada_calla(self):
        self.notificar(["119"])
        self.assertEqual(self.notificar(["119"]), ([], [], ["119"]))

    def test_nueva_junto_a_una_ya_avisada_solo_avisa_la_nueva(self):
        self.notificar(["119"])
        self.assertEqual(self.notificar(["119", "PLATEA 1"]), (["PLATEA 1"], [], ["119"]))

    def test_dos_lecturas_vacias_no_olvidan(self):
        # Un parpadeo de la pagina no debe provocar un aviso repetido
        self.notificar(["119"])
        self.notificar([])
        self.notificar([])
        self.assertEqual(self.notificar(["119"]), ([], [], ["119"]))

    def test_tres_lecturas_vacias_olvidan(self):
        self.notificar(["119"])
        for _ in range(self.m.LECTURAS_VACIAS_PARA_OLVIDAR):
            self.notificar([])
        self.assertEqual(self.estado, {})
        self.assertEqual(self.notificar(["119"])[0], ["119"])

    def test_recordatorio_a_los_diez_minutos(self):
        self.notificar(["119"])
        self.reloj.ahora += self.m.INTERVALO_RECORDATORIO - 1
        self.assertEqual(self.notificar(["119"])[1], [])
        self.reloj.ahora += 1
        self.assertEqual(self.notificar(["119"])[1], ["119"])

    def test_cada_localidad_lleva_su_propio_reloj(self):
        self.notificar(["119"])
        self.reloj.ahora += 300
        self.notificar(["119", "PLATEA 1"])
        self.reloj.ahora += 300
        # 119 cumple 10 min; PLATEA 1 solo 5
        self.assertEqual(self.notificar(["119", "PLATEA 1"])[1], ["119"])

    def test_el_estado_sobrevive_a_un_reinicio(self):
        self.notificar(["119"])
        self.m.guardar_estado(self.estado)
        self.estado = self.m.cargar_estado()
        self.assertEqual(self.notificar(["119"]), ([], [], ["119"]))

    def test_estado_corrupto_arranca_de_cero(self):
        with open(self.m.ARCHIVO_ESTADO, "w", encoding="utf-8") as archivo:
            archivo.write("{esto no es json")
        self.assertEqual(self.m.cargar_estado(), {})


class TestReintentoDeAvisosFallidos(TestDeduplicacion):
    """Si Telegram falla, el aviso no se da por enviado."""

    def test_nueva_fallida_vuelve_a_ser_nueva(self):
        nuevas, recordatorios, _ = self.notificar(["119"])
        self.m.deshacer_avisos(self.estado, URL, nuevas, recordatorios)
        self.assertEqual(self.notificar(["119"])[0], ["119"])

    def test_recordatorio_fallido_se_repite_como_recordatorio(self):
        self.notificar(["119"])
        self.reloj.ahora += self.m.INTERVALO_RECORDATORIO
        nuevas, recordatorios, _ = self.notificar(["119"])
        self.m.deshacer_avisos(self.estado, URL, nuevas, recordatorios)
        self.assertEqual(self.notificar(["119"]), ([], ["119"], []))

    def test_solo_se_deshace_lo_que_iba_en_ese_aviso(self):
        self.notificar(["119"])
        nuevas, recordatorios, _ = self.notificar(["119", "PLATEA 1"])
        self.m.deshacer_avisos(self.estado, URL, nuevas, recordatorios)
        self.assertIn(self.m._clave_estado(URL, "119"), self.estado)
        self.assertNotIn(self.m._clave_estado(URL, "PLATEA 1"), self.estado)
