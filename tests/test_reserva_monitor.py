"""
Integracion de la reserva en el monitor: solo URLs activadas, solo sectores
nuevos, pestana aparte y un aviso de Telegram con el resultado.
"""
import types
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
        self.paginas = []
        self.exclusiones = []   # secciones excluidas que recibio cada llamada
        self.resultado = rt.Reserva(True, SECTOR, 4, 4, "$ 1.527.000", "04:52")
        self.lanza = None
        self.cola = []          # resultados de las proximas llamadas, en orden
        self.tarda = 0          # segundos del reloj simulado que consume cada reserva

        def reservar(pagina, sectores, maximo=4, minimo=1, reloj=None):
            self.llamadas.append((list(sectores), maximo))
            self.exclusiones.append(set(getattr(pagina, "excluir_secciones", set())))
            self.reloj.ahora += self.tarda
            if self.lanza:
                raise self.lanza
            return self.cola.pop(0) if self.cola else self.resultado

        patches = [mock.patch.object(rt, "reservar", reservar),
                   mock.patch.object(rt, "PaginaSelenium", lambda driver, url, cargar: self.paginas.append(types.SimpleNamespace()) or self.paginas[-1])]
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
        self.assertFalse(r[0].ok)
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

    def test_el_orden_de_las_palabras_es_la_prioridad_no_el_del_catalogo(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4, "sectores": ["gramilla", "norte", "sur"]}}
        catalogo = ["SUR ALTA", "NORTE ALTA", "VIP (GRAMILLA)", "OCCIDENTAL BAJA"]
        self.m.intentar_reserva(DriverFalso(), BTS, catalogo, "BTS")
        self.assertEqual(self.llamadas, [(["VIP (GRAMILLA)", "NORTE ALTA", "SUR ALTA"], 4)])

    def test_a_igual_prioridad_se_conserva_el_orden_del_catalogo(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4, "sectores": ["norte"]}}
        self.m.intentar_reserva(DriverFalso(), BTS, ["NORTE BAJA", "NORTE ALTA"], "BTS")
        self.assertEqual(self.llamadas, [(["NORTE BAJA", "NORTE ALTA"], 4)])

    def test_el_maximo_sale_del_dict(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 2, "sectores": ["GRAMILLA"]}}
        self.m.intentar_reserva(DriverFalso(), BTS, ["VIP (GRAMILLA)"], "BTS")
        self.assertEqual(self.llamadas, [(["VIP (GRAMILLA)"], 2)])

    def test_un_dict_sin_sectores_reserva_todos_los_que_lleguen(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4}}
        self.m.intentar_reserva(DriverFalso(), BTS, ["A", "B"], "BTS")
        self.assertEqual(self.llamadas, [(["A", "B"], 4)])

    def test_las_palabras_llegan_a_la_pagina_para_elegir_la_seccion(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4, "sectores": ["back", "107"]}}
        self.m.intentar_reserva(DriverFalso(), BTS, ["Back Field", "101 - 103 - 105 - 107"], "E")
        self.assertEqual(self.paginas[-1].claves_seccion, ["back", "107"])

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


def listo(sector, cantidad=4):
    return rt.Reserva(True, sector, cantidad, 4, "$ 1.527.000", "04:59")


def fallo(sector):
    return rt.Reserva(False, sector, detalle="no hay boletas ni para 1")


def listo_sec(sector, seccion):
    return rt.Reserva(True, sector, 4, 4, "$ 2.668.000", "04:59", seccion=seccion)


def fallo_sec(sector, seccion):
    return rt.Reserva(False, sector, detalle="no hay asientos libres", seccion=seccion)


def sin_mas(sector):
    return rt.Reserva(False, sector, detalle="el sector no aparece o no se pudo abrir", sin_mas_secciones=True)


class TestVariasReservas(Base):
    """max_reservas > 1: una localidad por pestana, hasta el tope o hasta agotar la lista."""

    def setUp(self):
        super().setUp()
        self.config(8)

    def config(self, tope, sectores=("gramilla", "norte", "sur", "oriental")):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4, "sectores": list(sectores), "max_reservas": tope}}

    def lanzar(self, catalogo):
        d = DriverFalso()
        self.m.intentar_reserva(d, BTS, catalogo, "BTS")
        return d

    def test_una_pestana_y_una_llamada_por_localidad_en_orden_de_prioridad(self):
        d = self.lanzar(["SUR ALTA", "NORTE ALTA", "VIP (GRAMILLA)"])
        self.assertEqual([c[0] for c in self.llamadas],
                         [["VIP (GRAMILLA)"], ["NORTE ALTA"], ["SUR ALTA"]])
        self.assertEqual(sum(1 for e in d.eventos if e[0] == "nueva"), 3)
        self.assertEqual(d.actual, "monitor")

    def test_se_detiene_al_llegar_al_tope(self):
        self.config(2)
        self.lanzar(["VIP (GRAMILLA)", "NORTE ALTA", "SUR ALTA", "ORIENTAL BAJA"])
        self.assertEqual(len(self.llamadas), 2)

    def test_si_hay_menos_que_el_tope_reserva_las_que_haya(self):
        self.lanzar(["VIP (GRAMILLA)", "NORTE ALTA"])
        self.assertEqual(len(self.llamadas), 2)
        self.assertEqual(sum("RESERVA LISTA" in e for e in self.enviados), 2)

    def test_una_que_falla_no_cuenta_y_se_sigue_con_la_siguiente(self):
        self.config(2)
        self.cola = [fallo("VIP (GRAMILLA)"), listo("NORTE ALTA"), listo("SUR ALTA")]
        d = self.lanzar(["VIP (GRAMILLA)", "NORTE ALTA", "SUR ALTA", "ORIENTAL BAJA"])
        self.assertEqual([c[0][0] for c in self.llamadas], ["VIP (GRAMILLA)", "NORTE ALTA", "SUR ALTA"])
        self.assertIn(("cerrada", "reserva"), d.eventos)          # la fallida cierra su pestana

    def test_las_exitosas_dejan_su_pestana_abierta(self):
        d = self.lanzar(["VIP (GRAMILLA)", "NORTE ALTA"])
        self.assertEqual([e for e in d.eventos if e[0] == "cerrada"], [])

    def test_un_mensaje_por_reserva_y_un_resumen_final(self):
        self.cola = [listo("VIP (GRAMILLA)"), listo("NORTE ALTA"), listo("SUR ALTA")]
        self.lanzar(["VIP (GRAMILLA)", "NORTE ALTA", "SUR ALTA"])
        self.assertEqual(len(self.enviados), 4)
        resumen = self.enviados[-1]
        self.assertIn("3 RESERVA(S) LISTA(S)", resumen)
        for sector in ("VIP (GRAMILLA)", "NORTE ALTA", "SUR ALTA"):
            self.assertIn(sector, resumen)
        self.assertIn("vencen solas", resumen)

    def test_con_una_sola_localidad_no_hay_resumen(self):
        self.lanzar(["VIP (GRAMILLA)"])
        self.assertEqual(len(self.enviados), 1)

    def test_no_repite_una_localidad_ya_reservada_pero_si_reserva_las_nuevas(self):
        self.lanzar(["VIP (GRAMILLA)", "NORTE ALTA"])
        self.llamadas.clear()
        self.lanzar(["VIP (GRAMILLA)", "NORTE ALTA", "SUR ALTA"])         # aparece una nueva
        self.assertEqual([c[0][0] for c in self.llamadas], ["SUR ALTA"])
        self.reloj.ahora += self.m.INTERVALO_RECORDATORIO + 1
        self.llamadas.clear()
        self.lanzar(["VIP (GRAMILLA)"])                                    # pasado el enfriamiento
        self.assertEqual(len(self.llamadas), 1)

    def test_un_fallo_limpio_si_puede_reintentarse(self):
        self.cola = [fallo("VIP (GRAMILLA)")]
        self.lanzar(["VIP (GRAMILLA)"])
        self.llamadas.clear()
        self.lanzar(["VIP (GRAMILLA)"])
        self.assertEqual(len(self.llamadas), 1)

    def test_tope_de_tiempo_total(self):
        # Cada reserva tarda 200 s simulados y el tope es 300: tras la segunda ya no empieza otra.
        self.tarda = 200
        self.lanzar(["VIP (GRAMILLA)", "NORTE ALTA", "SUR ALTA", "ORIENTAL BAJA"])
        self.assertEqual(len(self.llamadas), 2)
        self.assertIn("se acabo el tiempo", self.leer_registro())

    def test_un_error_inesperado_en_una_no_impide_las_demas(self):
        self.lanza = RuntimeError("boom")
        d = self.lanzar(["VIP (GRAMILLA)", "NORTE ALTA"])
        self.assertEqual(len(self.llamadas), 2)
        self.assertEqual(d.actual, "monitor")

    def test_sin_max_reservas_sigue_siendo_una_sola_llamada_con_toda_la_lista(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4, "sectores": ["gramilla", "norte"]}}
        self.lanzar(["NORTE ALTA", "VIP (GRAMILLA)"])
        self.assertEqual(self.llamadas, [(["VIP (GRAMILLA)", "NORTE ALTA"], 4)])

    def test_puerto_cerrado_en_modo_varias_avisa_una_vez(self):
        self.m.RESERVA_PUERTO_DEPURACION = 9223
        self.m.puerto_depuracion_activo = lambda puerto=None: False
        self.lanzar(["VIP (GRAMILLA)", "NORTE ALTA"])
        self.assertEqual(self.llamadas, [])
        self.assertEqual(len(self.enviados), 1)
        self.assertIn("iniciar_comet_debug.bat", self.enviados[0])


class TestSeccionesComoReservas(Base):
    """Un sector numerado agrupa secciones (117, 119, 121, 123): cada libre es una reserva y una pestana."""

    GRUPO = "117 - 119 - 121 - 123"

    def setUp(self):
        super().setUp()
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4, "max_reservas": 8}}

    def lanzar(self, catalogo=None):
        d = DriverFalso()
        self.m.intentar_reserva(d, BTS, catalogo or [self.GRUPO], "Calvin Harris")
        return d

    def test_cada_seccion_libre_es_una_reserva_en_su_propia_pestana(self):
        g = self.GRUPO
        self.cola = [listo_sec(g, "117 (+18)"), listo_sec(g, "119 (+18)"), listo_sec(g, "121 (+18)"),
                     listo_sec(g, "123 (+18)"), sin_mas(g)]
        d = self.lanzar()
        self.assertEqual(len(self.llamadas), 5)                         # 4 secciones + la que ya no queda
        self.assertEqual(sum(1 for e in d.eventos if e[0] == "nueva"), 5)
        # cada pestana recibe las secciones ya hechas, para tomar otra
        self.assertEqual(self.exclusiones[0], set())
        self.assertEqual(self.exclusiones[1], {"117 (+18)"})
        self.assertEqual(self.exclusiones[4], {"117 (+18)", "119 (+18)", "121 (+18)", "123 (+18)"})
        self.assertEqual(sum("RESERVA LISTA" in e for e in self.enviados), 4)
        self.assertEqual(sum("NO PUDE RESERVAR" in e for e in self.enviados), 0)   # el fin del sector no es un fallo
        self.assertIn("4 RESERVA(S) LISTA(S)", self.enviados[-1])
        self.assertIn(("cerrada", "reserva"), d.eventos)                          # la ultima pestana vacia se cierra

    def test_los_mensajes_dicen_que_seccion_es_cada_una(self):
        g = self.GRUPO
        self.cola = [listo_sec(g, "117 (+18)"), listo_sec(g, "119 (+18)"), sin_mas(g)]
        self.lanzar()
        self.assertIn("117 (+18)", self.enviados[0])
        self.assertIn("119 (+18)", self.enviados[1])
        self.assertIn("117 (+18)", self.enviados[-1])
        self.assertIn("119 (+18)", self.enviados[-1])

    def test_el_tope_corta_aunque_queden_secciones(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4, "max_reservas": 2}}
        g = self.GRUPO
        self.cola = [listo_sec(g, f"{n} (+18)") for n in (117, 119, 121, 123)]
        self.lanzar()
        self.assertEqual(len(self.llamadas), 2)

    def test_las_secciones_cuentan_para_el_tope_junto_con_otros_sectores(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4, "max_reservas": 3}}
        g = self.GRUPO
        # El grupo da 2 secciones, la pagina dice que no hay mas, y entonces sigue Back Field (la 3a).
        self.cola = [listo_sec(g, "117 (+18)"), listo_sec(g, "119 (+18)"), sin_mas(g), listo("Back Field")]
        self.lanzar([g, "Back Field", "Otro"])
        self.assertEqual([c[0][0] for c in self.llamadas], [g, g, g, "Back Field"])
        self.assertEqual(sum("RESERVA LISTA" in e for e in self.enviados), 3)

    def test_una_seccion_que_falla_se_excluye_y_se_prueba_la_siguiente(self):
        g = self.GRUPO
        self.cola = [fallo_sec(g, "117 (+18)"), listo_sec(g, "119 (+18)"), sin_mas(g)]
        self.lanzar()
        self.assertEqual(len(self.llamadas), 3)
        self.assertEqual(self.exclusiones[1], {"117 (+18)"})            # no insiste con la que fallo
        self.assertEqual(sum("RESERVA LISTA" in e for e in self.enviados), 1)

    def test_un_sector_sin_secciones_se_reserva_una_sola_vez(self):
        self.cola = [listo("Back Field")]
        self.lanzar(["Back Field"])
        self.assertEqual(len(self.llamadas), 1)

    def test_las_secciones_ya_reservadas_no_se_repiten_en_otra_deteccion(self):
        g = self.GRUPO
        self.cola = [listo_sec(g, "117 (+18)"), sin_mas(g)]
        self.lanzar()
        self.llamadas.clear()
        self.exclusiones.clear()
        self.cola = [listo_sec(g, "119 (+18)"), sin_mas(g)]             # aparece otra seccion despues
        self.lanzar()
        self.assertEqual(self.exclusiones[0], {"117 (+18)"})            # la 117 ya estaba hecha

    def test_cota_de_pestanas_por_sector(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4, "max_reservas": 99}}
        g = self.GRUPO
        self.cola = [fallo_sec(g, f"{n} (+18)") for n in range(100)]
        self.lanzar()
        self.assertEqual(len(self.llamadas), self.m.MAX_INTENTOS_POR_SECTOR)

    def test_con_una_sola_reserva_sigue_siendo_la_primera_seccion(self):
        self.m.RESERVAR_TICKETMASTER = {BTS: {"maximo": 4}}              # max_reservas = 1
        self.cola = [listo_sec(self.GRUPO, "117 (+18)")]
        self.lanzar()
        self.assertEqual(len(self.llamadas), 1)


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
        self.assertFalse(r[0].ok)
        self.assertEqual(d.eventos, [])
        self.assertEqual(self.llamadas, [])
        self.assertIn("iniciar_comet_debug.bat", self.enviados[0])
        self.assertIn("9223", self.enviados[0])

    def test_fallo_de_conexion_no_tumba_el_monitor(self):
        self.m.puerto_depuracion_activo = lambda puerto=None: True
        with mock.patch.object(self.m.urllib.request, "urlopen", side_effect=OSError("sin red")):
            r = self.m.intentar_reserva(DriverFalso(), URL, [SECTOR], "E")
        self.assertFalse(r[0].ok)
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

    def test_la_reserva_no_depende_del_filtro_de_avisos(self):
        # El filtro de avisos solo deja pasar "otra cosa": no avisa del sector, pero se reserva igual.
        self.m.FILTROS_LOCALIDADES = {URL: ["otra cosa"]}
        self.correr(3)
        self.assertEqual(self.llamadas, [([SECTOR], 4)])
        # sin aviso de ESTA url (la otra url del bucle no tiene filtro y si avisa)
        self.assertFalse(any("DISPONIBILIDAD DETECTADA" in e and URL in e for e in self.enviados))
        self.assertTrue(any("RESERVA LISTA" in e for e in self.enviados))

    def test_el_filtro_de_avisos_no_se_toca_y_sigue_avisando_lo_suyo(self):
        self.m.FILTROS_LOCALIDADES = {URL: ["VIP"]}
        self.correr(1)
        self.assertTrue(any("DISPONIBILIDAD DETECTADA" in e for e in self.enviados))
        self.assertEqual(len(self.llamadas), 1)

    def test_la_reserva_guarda_su_propio_estado_sin_pisar_el_de_avisos(self):
        self.m.FILTROS_LOCALIDADES = {URL: ["VIP"]}
        self.correr(1)
        import json
        with open(self.m.ARCHIVO_ESTADO, encoding="utf-8") as f:
            claves = list(json.load(f))
        self.assertTrue(any(k.startswith(URL + "||") for k in claves))                      # avisos
        self.assertTrue(any(k.startswith(URL + self.m.CLAVE_RESERVA + "||") for k in claves))  # reserva

    def test_sin_url_activada_el_monitor_solo_observa(self):
        self.m.RESERVAR_TICKETMASTER = {}
        self.correr(1)
        self.assertEqual(self.llamadas, [])
        self.assertEqual(len(self.enviados), 2)               # un aviso por URL, nada mas
