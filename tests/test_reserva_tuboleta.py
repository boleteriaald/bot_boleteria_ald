"""
Reserva en Tuboleta: que localidad elegir, cuantas marcar, cuando bajar y cuando parar; y su
disparo desde el monitor.

PaginaFalsa reproduce la tabla "Mejor sitio" leida el 6-nov-2026: filas con localidad,
tarifa y un selector de cantidad 0..N; las agotadas, sin selector. El cupo real solo se sabe
al pulsar "Anadir al carrito" (lo que hace la pagina real con mas de las que quedan aun no
se ha visto).
"""
import unittest
from unittest import mock

import apoyo  # noqa: F401  (pone la raiz del proyecto en sys.path)
import reserva_tuboleta as rtb
from apoyo import CasoMonitor

URL = "https://tbpgpal.checkout.tuboleta.com/selection/event/seat?perfId=1&table=1&productId=2"


def fila(categoria, tope=10, tarifa="PRECIO FULL", nombre=None):
    return {"categoria": categoria, "tarifa": tarifa, "nombre": nombre or f"q-{categoria}-{tarifa}",
            "opciones": list(range(1, tope + 1)), "agotada": False}


def agotada(categoria):
    return {"categoria": categoria, "tarifa": "", "nombre": "", "opciones": [], "agotada": True}


class PaginaFalsa:
    def __init__(self, filas, cupo=None, abre=True, deja_de_mostrar=False, error="¡Lo sentimos! No hay suficientes boletas",
                 tope_compra=None, cesta=0):
        self._filas = filas
        self.cupo = cupo or {}          # categoria -> boletas que de verdad quedan
        self.abre = abre
        self.motivo = "" if abre else "la tabla de localidades no aparecio"
        self.deja_de_mostrar = deja_de_mostrar
        self.detenida = False
        self.marcada = None
        self.pedidos = []               # (nombre del selector, cantidad) de cada "Anadir"
        self.error = error
        self.vueltas = 0
        self.tope_compra = tope_compra  # "el numero maximo permitido es N" (cuenta la cesta)
        self.cesta = cesta

    def abrir(self):
        return self.abre

    def filas(self):
        return self._filas

    def fijar_cantidad(self, nombre, n):
        self.marcada = (nombre, n)
        return n

    def anadir(self):
        self.pedidos.append(self.marcada)
        if self.deja_de_mostrar:
            self.detenida = True
            self.motivo = "Tuboleta pide iniciar sesion en el navegador de reserva"
            return False, self.motivo
        nombre, n = self.marcada
        categoria = next(f["categoria"] for f in self._filas if f["nombre"] == nombre)
        if self.tope_compra is not None and self.cesta + n > self.tope_compra:
            return False, ("Lo sentimos, el número seleccionado de entradas no puede añadirse a la cesta: "
                           f"el número máximo permitido es {self.tope_compra}.")
        if n > self.cupo.get(categoria, 99):
            return False, self.error
        self.cupo[categoria] = self.cupo.get(categoria, 99) - n
        self.cesta += n
        return True, "la cesta tiene 1 producto(s)"

    def volver(self):
        self.vueltas += 1
        return True

    def en_cesta(self):
        return self.cesta


class TestReservar(unittest.TestCase):

    def test_marca_la_mayor_cantidad_que_deja_la_pagina(self):
        p = PaginaFalsa([agotada("TRIBUNA FAN SUR"), fila("OCCIDENTAL 3er PISO", tope=8)])
        r = rtb.reservar(p)
        self.assertTrue(r.ok)
        self.assertEqual((r.sector, r.cantidad, r.pedidas), ("OCCIDENTAL 3er PISO", 8, 8))
        self.assertTrue(r.conservar_pestana)

    def test_sin_esa_cantidad_baja_de_una_en_una_hasta_las_que_haya(self):
        p = PaginaFalsa([fila("PLATEA", tope=10)], cupo={"PLATEA": 7})
        r = rtb.reservar(p)
        self.assertTrue(r.ok)
        self.assertEqual([n for _, n in p.pedidos], [10, 9, 8, 7])
        self.assertEqual((r.cantidad, r.pedidas), (7, 10))
        self.assertIn("Solo se pudieron 7 de 10", rtb.mensaje(r, "Reykon", URL, "20:00"))

    def test_maximo_limita_la_cantidad(self):
        p = PaginaFalsa([fila("PLATEA", tope=10)])
        r = rtb.reservar(p, maximo=6)
        self.assertEqual([n for _, n in p.pedidos], [6])
        self.assertEqual(r.cantidad, 6)

    def test_sectores_dan_la_prioridad(self):
        p = PaginaFalsa([fila("SEGUNDO PISO 206-214"), fila("PLATEA ADMISIÓN GENERAL")])
        r = rtb.reservar(p, ["platea admision", "206"])
        self.assertEqual(r.sector, "PLATEA ADMISIÓN GENERAL")

    def test_si_una_localidad_no_tiene_nada_pasa_a_la_siguiente(self):
        p = PaginaFalsa([fila("PLATEA", tope=2), fila("TRIBUNA", tope=2)], cupo={"PLATEA": 0})
        r = rtb.reservar(p, ["platea", "tribuna"])
        self.assertEqual((r.sector, r.cantidad), ("TRIBUNA", 2))
        self.assertEqual([n for _, n in p.pedidos], [2, 1, 2])   # PLATEA 2 y 1 rechazadas, TRIBUNA 2 ok

    def test_ninguna_coincide_no_pulsa_nada(self):
        p = PaginaFalsa([fila("NORTE")])
        r = rtb.reservar(p, ["platea"])
        self.assertFalse(r.ok)
        self.assertTrue(r.sin_disponibles)
        self.assertEqual(p.pedidos, [])
        self.assertIn("NORTE", r.detalle)

    def test_todo_agotado_no_pulsa_nada(self):
        p = PaginaFalsa([agotada("PLATEA"), agotada("TRIBUNA")])
        r = rtb.reservar(p)
        self.assertTrue(r.sin_disponibles)
        self.assertEqual(p.pedidos, [])

    def test_prefiere_la_tarifa_sin_restriccion(self):
        p = PaginaFalsa([fila("PLATEA", tarifa="DESCUENTO COMPENSAR"), fila("PLATEA", tarifa="PRECIO FULL")])
        r = rtb.reservar(p)
        self.assertEqual(r.tarifa, "PRECIO FULL")

    def test_si_la_pagina_se_va_no_insiste(self):
        p = PaginaFalsa([fila("PLATEA"), fila("TRIBUNA")], deja_de_mostrar=True)
        r = rtb.reservar(p)
        self.assertFalse(r.ok)
        self.assertEqual(len(p.pedidos), 1)
        self.assertIn("iniciar sesion", r.detalle)

    def test_no_abre(self):
        r = rtb.reservar(PaginaFalsa([], abre=False))
        self.assertFalse(r.ok)
        self.assertIn("no se pudo abrir", r.detalle)

    def test_url_con_tabla(self):
        sin = "https://x.checkout.tuboleta.com/selection/event/seat?perfId=1&productId=2"
        self.assertEqual(rtb.url_con_tabla(sin), sin + "&table=1")
        self.assertEqual(rtb.url_con_tabla(URL), URL)


class TestMonitor(CasoMonitor):

    def setUp(self):
        super().setUp()
        self.m.RESERVAR_TUBOLETA = {URL: {"sectores": ["platea"]}}
        self.m.navegador_reserva = lambda driver: ("navegador", None)

    def reservar(self, nuevas, resultado):
        with mock.patch.object(self.m, "_tuboleta_en_pestana", return_value=resultado) as pestana:
            r = self.m.intentar_reserva_tuboleta(None, URL, nuevas, "Reykon")
        return r, pestana

    def test_dispara_con_una_localidad_nueva_que_casa(self):
        r, pestana = self.reservar(["PLATEA ADMISIÓN GENERAL"], rtb.Reserva(True, "PLATEA", cantidad=6, pedidas=6))
        pestana.assert_called_once_with("navegador", URL, ["platea"], None, "Reykon", None)
        self.assertTrue(r.ok)
        self.assertIn("EN EL CARRITO", self.enviados[-1])

    def test_no_dispara_si_ninguna_nueva_casa(self):
        r, pestana = self.reservar(["TRIBUNA FAN SUR"], rtb.Reserva(True))
        self.assertIsNone(r)
        pestana.assert_not_called()

    def test_no_repite_tras_un_exito_reciente(self):
        self.reservar(["PLATEA"], rtb.Reserva(True, "PLATEA", cantidad=6, pedidas=6))
        r, pestana = self.reservar(["PLATEA"], rtb.Reserva(True))
        self.assertIsNone(r)
        pestana.assert_not_called()

    def test_sin_nada_a_la_venta_no_manda_telegram(self):
        self.reservar(["PLATEA"], rtb.Reserva(False, detalle="no hay", sin_disponibles=True))
        self.assertEqual(self.enviados, [])

    def test_un_fallo_si_se_avisa(self):
        self.reservar(["PLATEA"], rtb.Reserva(False, detalle="ninguna localidad se dejo anadir al carrito"))
        self.assertIn("NO PUDE AÑADIR", self.enviados[-1])

    def test_completar_usa_maximo_como_total(self):
        self.m.RESERVAR_TUBOLETA = {URL: {"sectores": ["platea"], "maximo": 20, "completar": True}}
        _, pestana = self.reservar(["PLATEA"], rtb.Reserva(True, "PLATEA", cantidad=20, pedidas=20))
        pestana.assert_called_once_with("navegador", URL, ["platea"], None, "Reykon", 20)

    def test_sin_completar_maximo_limita_la_unica_tanda(self):
        self.m.RESERVAR_TUBOLETA = {URL: {"sectores": ["platea"], "maximo": 6}}
        _, pestana = self.reservar(["PLATEA"], rtb.Reserva(True, "PLATEA", cantidad=6, pedidas=6))
        pestana.assert_called_once_with("navegador", URL, ["platea"], 6, "Reykon", None)

    def test_la_url_de_asientos_es_de_tuboleta_y_pasala_no(self):
        self.assertTrue(self.m.es_url_tuboleta_asientos(URL))
        self.assertFalse(self.m.es_url_tuboleta_asientos(
            "https://pasala.checkout.tuboleta.com/selection/resale/item?performanceId=1"))



class BotonFalso:
    def __init__(self, driver):
        self.driver = driver

    def click(self):
        self.driver.pulsado = True


class DriverDataDome:
    """
    Pagina real simulada tras "Anadir al carrito": DataDome tapa la respuesta hasta que la
    persona pasa la verificacion (`pasa_tras` consultas) y luego la cesta tiene 10.
    """

    def __init__(self, pasa_tras=None):
        self.pulsado = False
        self.pasa_tras = pasa_tras     # None = nunca la pasa
        self.consultas = 0
        self.al_frente = False
        self.current_url = URL

    def execute_cdp_cmd(self, cmd, args):
        self.al_frente = cmd == "Page.bringToFront"

    def _verificando(self):
        if not self.pulsado:
            return False
        self.consultas += 1
        return self.pasa_tras is None or self.consultas <= self.pasa_tras

    def execute_script(self, script, *args):
        if script == rtb.JS_BOTON_ANADIR:
            return BotonFalso(self)
        if script == rtb.JS_ESTADO_ENVIO:
            return {"marca": not self.pulsado, "listo": "complete", "url": self.current_url}
        if script == rtb.JS_VERIFICACION:
            return self._verificando()
        if script == rtb.JS_CESTA:
            return 10 if self.pulsado and not self._verificando() else 0
        if script == rtb.JS_TABLA:
            return True
        if script == rtb.JS_AVISOS:
            return ""
        return True


class TestVerificacion(unittest.TestCase):

    def pagina(self, driver):
        avisos = []
        p = rtb.PaginaSelenium(driver, URL, lambda d, u: None, al_verificar=lambda: avisos.append(1))
        return p, avisos

    def test_avisa_al_instante_espera_y_cuenta_la_cesta(self):
        d = DriverDataDome(pasa_tras=2)
        p, avisos = self.pagina(d)
        ok, nota = p.anadir()
        self.assertTrue(ok, nota)
        self.assertEqual(avisos, [1])
        self.assertTrue(d.al_frente)
        self.assertTrue(p.conservar_pestana)

    def test_si_nadie_la_pasa_deja_la_pestana_abierta(self):
        d = DriverDataDome(pasa_tras=None)
        p, avisos = self.pagina(d)
        with mock.patch.object(rtb, "ESPERA_VERIFICACION", 1):
            ok, nota = p.anadir()
        self.assertFalse(ok)
        self.assertEqual(avisos, [1])
        self.assertTrue(p.detenida and p.conservar_pestana)
        self.assertIn("robot", nota)
        r = rtb.Reserva(False, detalle=nota, conservar_pestana=True)
        self.assertIn("queda abierta", rtb.mensaje(r, "Hamilton", URL, "15:54"))


class TestTotal(unittest.TestCase):
    """Modo `total` (pedido el 6-nov-2026): llenar el carrito hasta 20, PLATEA siempre primero."""

    def localidades(self):
        return [fila("PLATEA"), fila("SEGUNDO PISO")]

    def test_repite_platea_mientras_acepte(self):
        p = PaginaFalsa(self.localidades())
        r = rtb.reservar(p, ["platea", "segundo piso"], total=20)
        self.assertEqual([n for _, n in p.pedidos], [10, 10])
        self.assertEqual((r.ok, r.cantidad, r.pedidas, r.sector), (True, 20, 20, "PLATEA x20"))
        self.assertEqual(p.vueltas, 1)

    def test_cuando_platea_no_da_mas_completa_con_segundo_piso(self):
        p = PaginaFalsa(self.localidades(), cupo={"PLATEA": 13})
        r = rtb.reservar(p, ["platea", "segundo piso"], total=20)
        self.assertEqual([n for _, n in p.pedidos], [10, 10, 9, 8, 7, 6, 5, 4, 3, 7])
        self.assertEqual((r.cantidad, r.sector), (20, "PLATEA x13 + SEGUNDO PISO x7"))
        texto = rtb.mensaje(r, "Hamilton", URL, "16:12")
        self.assertIn("Total: 20 boletas", texto)
        self.assertIn("7 x SEGUNDO PISO", texto)

    def test_si_no_llega_al_total_avisa_cuantas(self):
        p = PaginaFalsa(self.localidades(), cupo={"PLATEA": 10, "SEGUNDO PISO": 0})
        r = rtb.reservar(p, ["platea", "segundo piso"], total=20)
        self.assertTrue(r.ok)
        self.assertEqual(r.cantidad, 10)
        self.assertIn("Solo se pudieron 10 de 20", rtb.mensaje(r, "Hamilton", URL, "16:12"))

    def test_tope_de_rechazos(self):
        p = PaginaFalsa([fila("PLATEA"), fila("SEGUNDO PISO"), fila("TERCER PISO")],
                        cupo={"PLATEA": 0, "SEGUNDO PISO": 0, "TERCER PISO": 0})
        r = rtb.reservar(p, total=20)
        self.assertFalse(r.ok)
        self.assertEqual(len(p.pedidos), rtb.MAX_RECHAZOS)

    def test_rechazo_por_limite_de_compra_no_sigue_bajando(self):
        p = PaginaFalsa(self.localidades(), cupo={"PLATEA": 10},
                        error="Has alcanzado el límite de boletas por compra")
        r = rtb.reservar(p, ["platea", "segundo piso"], total=20)
        self.assertEqual([n for _, n in p.pedidos], [10, 10])
        self.assertEqual(r.cantidad, 10)

    def test_sin_total_es_una_sola_tanda(self):
        p = PaginaFalsa(self.localidades())
        r = rtb.reservar(p, ["platea", "segundo piso"])
        self.assertEqual([n for _, n in p.pedidos], [10])
        self.assertEqual(p.vueltas, 0)


class TestTopePorCompra(unittest.TestCase):
    """"el numero maximo permitido es N" (Hamilton, 6-nov-2026: 10; en otros eventos 12, 15, 50)."""

    def localidades(self):
        return [fila("PLATEA"), fila("SEGUNDO PISO")]

    def test_con_la_cesta_en_el_tope_para_sin_bajar(self):
        p = PaginaFalsa(self.localidades(), tope_compra=10)
        r = rtb.reservar(p, ["platea", "segundo piso"], total=20)
        self.assertEqual([n for _, n in p.pedidos], [10, 10])   # antes: 10, 10, 9, 8 ... 1, y SEGUNDO PISO igual
        self.assertEqual((r.ok, r.cantidad, r.tope_compra), (True, 10, 10))
        self.assertIn("máximo 10 por compra", rtb.mensaje(r, "Hamilton", URL, "16:31"))

    def test_si_cabe_algo_prueba_con_lo_que_falta_y_para(self):
        p = PaginaFalsa(self.localidades(), tope_compra=15)
        r = rtb.reservar(p, ["platea", "segundo piso"], total=20)
        self.assertEqual([n for _, n in p.pedidos], [10, 10, 5])
        self.assertEqual((r.cantidad, r.tope_compra), (15, 15))

    def test_cesta_ya_llena_de_antes(self):
        p = PaginaFalsa(self.localidades(), tope_compra=10, cesta=10)
        r = rtb.reservar(p, ["platea", "segundo piso"], total=20)
        self.assertEqual([n for _, n in p.pedidos], [10])
        self.assertFalse(r.ok)
        self.assertIn("ya tiene 10", r.detalle)

    def test_tope_alto_no_estorba(self):
        p = PaginaFalsa(self.localidades(), tope_compra=50)
        r = rtb.reservar(p, ["platea", "segundo piso"], total=20)
        self.assertEqual([n for _, n in p.pedidos], [10, 10])
        self.assertEqual((r.cantidad, r.tope_compra), (20, 0))


if __name__ == "__main__":
    unittest.main()
