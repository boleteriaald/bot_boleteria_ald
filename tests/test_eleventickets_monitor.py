"""
Eleventickets en el monitor: lectura de los bloques del mapa y disparo de la reserva
(anadir al carrito) solo ante bloques recien habilitados que casan con la configuracion.
"""
from unittest import mock

import reserva_eleventickets as re11
from apoyo import CasoMonitor

URL = "https://sudamericana.eleventickets.com/#!/apresentacao/abc"
ORIENTAL = "CAT2 - Oriental Tribuna Alta - Sector 7"
OCCIDENTAL = "CAT1 - Occidental Tribuna Baja - Sector 1"


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
    def __init__(self, bloques=None, url_actual="", estado=None):
        self.actual = "monitor"
        self.eventos = []
        self.switch_to = Pestanas(self)
        self.bloques = bloques
        self.estado = estado          # lo que devuelve JS_ESTADO (None = sigue en Cloudflare)
        self.current_url = url_actual
        self.visitadas = []
        self.window_handles = ["monitor", "verificacion"]

    @property
    def current_window_handle(self):
        return self.actual

    def close(self):
        self.eventos.append(("cerrada", self.actual))

    def get(self, url):
        self.visitadas.append(url)
        self.current_url = url

    def execute_script(self, script, *args):
        if script == re11.JS_ESTADO:
            return self.estado
        return self.bloques


class TestLectura(CasoMonitor):

    def setUp(self):
        super().setUp()
        self.m.navegar = lambda driver, url: driver.get(url)

    def test_habilitados_son_disponibles(self):
        d = DriverFalso([{"nombre": ORIENTAL, "libre": True, "numerado": False},
                         {"nombre": OCCIDENTAL, "libre": False, "numerado": False}])
        disponibles, agotadas, url = self.m.verificar_disponibilidad_eleventickets(d, URL)
        self.assertEqual((disponibles, agotadas, url), ([ORIENTAL], [OCCIDENTAL], URL))

    def test_misma_url_con_ancla_fuerza_la_recarga(self):
        d = DriverFalso([], url_actual=URL)
        self.m.verificar_disponibilidad_eleventickets(d, URL)
        self.assertEqual(d.visitadas, ["about:blank", URL])

    def test_mapa_sin_leer_es_lectura_vacia(self):
        d = DriverFalso(None)
        self.assertEqual(self.m.verificar_disponibilidad_eleventickets(d, URL), ([], [], URL))

    def test_la_url_se_despacha_a_eleventickets(self):
        self.assertTrue(self.m.es_url_eleventickets(URL))
        self.assertFalse(self.m.es_url_ticketmaster(URL))


class TestReserva(CasoMonitor):

    def setUp(self):
        super().setUp()
        self.m.configurar_registro()
        self.m.RESERVAR_ELEVENTICKETS = {URL: {"maximo": 4, "sectores": ["CAT2 - Oriental"]}}
        self.m.RESERVA_PUERTO_DEPURACION = None   # se reserva en el propio driver
        self.m._ULTIMA_RESERVA.clear()
        self.m._PESTANA_VERIFICACION.clear()
        self.llamadas = []
        self.paginas = []          # ya_cargada de cada pagina creada
        self.resultado = re11.Reserva(True, ORIENTAL, "Público Colombiano", 2, 4)

        def reservar(pagina, sectores, maximo=4, producto="", reloj=None):
            self.llamadas.append((list(sectores), maximo))
            return self.resultado

        def pagina(driver, url, cargar, ya_cargada=False):
            self.paginas.append(ya_cargada)
            return object()

        for p in (mock.patch.object(re11, "reservar", reservar),
                  mock.patch.object(re11, "PaginaSelenium", pagina)):
            p.start()
            self.addCleanup(p.stop)

    def test_bloque_nuevo_que_casa_anade_y_deja_la_pestana(self):
        d = DriverFalso()
        r = self.m.intentar_reserva_eleventickets(d, URL, [OCCIDENTAL, ORIENTAL], "Final")
        self.assertTrue(r.ok)
        self.assertEqual(self.llamadas, [(["CAT2 - Oriental"], 4)])
        self.assertNotIn(("cerrada", "reserva"), d.eventos)
        self.assertIn("EN EL CARRITO", self.enviados[-1])

    def test_bloque_que_no_casa_no_abre_nada(self):
        d = DriverFalso()
        self.assertIsNone(self.m.intentar_reserva_eleventickets(d, URL, [OCCIDENTAL], "Final"))
        self.assertEqual((self.llamadas, d.eventos, self.enviados), ([], [], []))

    def test_fallo_cierra_la_pestana_y_avisa(self):
        self.resultado = re11.Reserva(False, pedidas=4, detalle="ningun sector se dejo reservar")
        d = DriverFalso()
        self.m.intentar_reserva_eleventickets(d, URL, [ORIENTAL], "Final")
        self.assertIn(("cerrada", "reserva"), d.eventos)
        self.assertEqual(d.actual, "monitor")
        self.assertIn("NO PUDE AÑADIR", self.enviados[-1])

    def test_verificacion_de_cloudflare_deja_la_pestana_abierta(self):
        self.resultado = re11.Reserva(False, pedidas=4, conservar_pestana=True,
                                      detalle="no se pudo abrir el mapa del evento: Cloudflare pide la verificacion")
        d = DriverFalso()
        self.m.intentar_reserva_eleventickets(d, URL, [ORIENTAL], "Final")
        self.assertNotIn(("cerrada", "reserva"), d.eventos)
        self.assertIn("Cloudflare", self.enviados[-1])

    def _primer_intento_en_verificacion(self, d):
        self.resultado = re11.Reserva(False, pedidas=4, conservar_pestana=True, detalle="Cloudflare")
        self.m.intentar_reserva_eleventickets(d, URL, [ORIENTAL], "Final")
        self.assertEqual(self.m._PESTANA_VERIFICACION, {URL: "reserva"})
        d.window_handles = ["monitor", "reserva"]

    def test_mientras_siga_la_verificacion_no_reintenta_ni_abre_otra(self):
        d = DriverFalso(estado=None)
        self._primer_intento_en_verificacion(d)
        self.assertIsNone(self.m.reintentar_tras_verificacion(d, URL, "Final"))
        self.assertIsNone(self.m.intentar_reserva_eleventickets(d, URL, [ORIENTAL], "Final"))
        self.assertEqual(len(self.llamadas), 1)
        self.assertEqual(d.eventos.count(("nueva", "tab")), 1)
        self.assertEqual(d.visitadas, [])          # mirar la pestana no la recarga

    def test_pasada_la_verificacion_reserva_en_esa_pestana_sin_recargar(self):
        d = DriverFalso(estado=None)
        self._primer_intento_en_verificacion(d)
        d.estado = {"usuario": True, "reservas": 0, "pow": False}
        self.resultado = re11.Reserva(True, ORIENTAL, "Público Colombiano", 4, 4)
        r = self.m.reintentar_tras_verificacion(d, URL, "Final")
        self.assertTrue(r.ok)
        self.assertEqual(self.paginas, [False, True])   # la segunda, sobre la pestana ya cargada
        self.assertEqual(d.eventos.count(("nueva", "tab")), 1)
        self.assertEqual(self.m._PESTANA_VERIFICACION, {})
        self.assertIn("EN EL CARRITO", self.enviados[-1])

    def test_si_el_usuario_cierra_la_pestana_se_olvida(self):
        d = DriverFalso(estado=None)
        self._primer_intento_en_verificacion(d)
        d.window_handles = ["monitor"]
        self.assertIsNone(self.m.reintentar_tras_verificacion(d, URL, "Final"))
        self.assertEqual(self.m._PESTANA_VERIFICACION, {})

    def test_no_repite_tras_un_exito_reciente(self):
        d = DriverFalso()
        self.m.intentar_reserva_eleventickets(d, URL, [ORIENTAL], "Final")
        self.assertIsNone(self.m.intentar_reserva_eleventickets(d, URL, [ORIENTAL], "Final"))
        self.assertEqual(len(self.llamadas), 1)

    def test_un_fallo_si_deja_reintentar(self):
        self.resultado = re11.Reserva(False, pedidas=4, detalle="agotado")
        d = DriverFalso()
        self.m.intentar_reserva_eleventickets(d, URL, [ORIENTAL], "Final")
        self.m.intentar_reserva_eleventickets(d, URL, [ORIENTAL], "Final")
        self.assertEqual(len(self.llamadas), 2)
