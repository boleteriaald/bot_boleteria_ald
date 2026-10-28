"""
Reserva en Eleventickets: que bloque elegir, cuantas marcar y cuando parar.

PaginaFalsa reproduce lo leido en el codigo de la pagina (28-oct-2026): bloques del mapa
con `disabled` y `m`; en los de cantidad, productos con un "+" que se frena en el tope y
"Anadir al Carrito"; en los numerados, asientos que se reservan de uno en uno.
"""
import unittest

import apoyo  # noqa: F401  (pone la raiz del proyecto en sys.path)
import reserva_eleventickets as re11

ORIENTAL_MEDIA_3 = "CAT2 - Oriental Tribuna Media - Sector 3"
ORIENTAL_ALTA_1 = "CAT2 - Oriental Tribuna Alta - Sector 1"
OCCIDENTAL = "CAT1 - Occidental Tribuna Baja - Sector 1"


class PaginaFalsa:
    def __init__(self, bloques, productos=None, tope=4, rechaza=(), asientos=None,
                 asientos_fallan=(), abre=True, cupo=None, error="No hay entradas disponibles"):
        self._bloques = bloques               # [{nombre, libre, numerado}]
        self._productos = productos or {}     # bloque -> [{nombre, agotado}]
        self.tope = tope                      # donde se frena el "+"
        self.rechaza = set(rechaza)           # bloques cuyo "Anadir" falla siempre
        self.error = error                    # texto de ese rechazo
        self.cupo = cupo                      # entradas que de verdad quedan (None = sin limite)
        self.pedidas = []                     # cantidad con la que se pulso "Anadir"
        self._asientos = asientos or {}       # bloque -> [{id, fila, lugar}]
        self.asientos_fallan = set(asientos_fallan)
        self.abre = abre
        self.motivo = "" if abre else "no hay sesion iniciada en Eleventickets en este navegador"
        self.bloque = None
        self.cantidad = 0
        self.abiertos, self.anadidos, self.asientos_pulsados = [], [], []

    def abrir(self):
        return self.abre

    def bloques(self):
        return self._bloques

    def elegir_bloque(self, nombre):
        self.bloque, self.cantidad = nombre, 0
        self.abiertos.append(nombre)
        return True

    def productos(self):
        return self._productos.get(self.bloque, [])

    def fijar_cantidad(self, indice, n):
        self.cantidad = min(n, self.tope)
        return self.cantidad

    def anadir(self):
        self.pedidas.append(self.cantidad)
        if self.bloque in self.rechaza:
            return False, self.error
        if self.cupo is not None and self.cantidad > self.cupo:
            # El "+" deja subir a 4, pero el servidor rechaza todo el pedido.
            return False, "Atención ¡El producto está agotado! OK"
        self.anadidos.append((self.bloque, self.cantidad))
        return True, f"{self.cantidad} reservada(s)"

    def asientos_libres(self):
        return self._asientos.get(self.bloque, [])

    def reservar_asiento(self, id_asiento):
        self.asientos_pulsados.append(id_asiento)
        if id_asiento in self.asientos_fallan:
            return False, "Asiento reservado"
        return True, "1 reservada(s)"


def bloque(nombre, libre=True, numerado=False):
    return {"nombre": nombre, "libre": libre, "numerado": numerado}


GENERAL = [{"nombre": "Entrada General", "agotado": False}]


class TestCantidad(unittest.TestCase):
    def test_marca_cuatro_y_anade_al_carrito(self):
        pagina = PaginaFalsa([bloque(OCCIDENTAL), bloque(ORIENTAL_MEDIA_3)],
                             productos={ORIENTAL_MEDIA_3: GENERAL})
        r = re11.reservar(pagina, ["CAT2 - Oriental"], maximo=4)
        self.assertTrue(r.ok)
        self.assertEqual((r.sector, r.cantidad), (ORIENTAL_MEDIA_3, 4))
        self.assertEqual(pagina.anadidos, [(ORIENTAL_MEDIA_3, 4)])
        self.assertEqual(pagina.abiertos, [ORIENTAL_MEDIA_3])  # el CAT1 ni se toca

    def test_nunca_mas_de_cuatro(self):
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3)], productos={ORIENTAL_MEDIA_3: GENERAL}, tope=10)
        self.assertEqual(re11.reservar(pagina, ["CAT2 - Oriental"]).cantidad, 4)

    def test_si_el_mas_se_frena_sigue_con_las_que_haya(self):
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3)], productos={ORIENTAL_MEDIA_3: GENERAL}, tope=2)
        r = re11.reservar(pagina, ["CAT2 - Oriental"], maximo=4)
        self.assertTrue(r.ok)
        self.assertEqual((r.cantidad, r.pedidas), (2, 4))
        self.assertIn("Solo se pudieron 2 de 4", re11.mensaje(r, "Final", "url", "10:00"))

    def test_sin_tildes_ni_mayusculas_ni_guiones(self):
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3)], productos={ORIENTAL_MEDIA_3: GENERAL})
        self.assertTrue(re11.reservar(pagina, ["cat2 oriental"]).ok)

    def test_salta_el_producto_agotado(self):
        productos = [{"nombre": "Hincha Boca", "agotado": True}, {"nombre": "General", "agotado": False}]
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3)], productos={ORIENTAL_MEDIA_3: productos})
        self.assertEqual(re11.reservar(pagina, ["CAT2 - Oriental"]).producto, "General")

    def test_si_un_bloque_rechaza_pasa_al_siguiente(self):
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3), bloque(ORIENTAL_ALTA_1)],
                             productos={ORIENTAL_MEDIA_3: GENERAL, ORIENTAL_ALTA_1: GENERAL},
                             rechaza={ORIENTAL_MEDIA_3})
        r = re11.reservar(pagina, ["CAT2 - Oriental"])
        self.assertEqual(r.sector, ORIENTAL_ALTA_1)
        self.assertEqual(len(pagina.anadidos), 1)
        self.assertIn("rechazada", r.intentos[0])

    def test_agotado_baja_la_cantidad_en_el_mismo_bloque(self):
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3), bloque(ORIENTAL_ALTA_1)],
                             productos={ORIENTAL_MEDIA_3: GENERAL, ORIENTAL_ALTA_1: GENERAL}, cupo=2)
        r = re11.reservar(pagina, ["CAT2 - Oriental"], maximo=4)
        self.assertTrue(r.ok)
        self.assertEqual((r.sector, r.cantidad), (ORIENTAL_MEDIA_3, 2))
        self.assertEqual(pagina.pedidas, [4, 3, 2])
        self.assertEqual(pagina.abiertos, [ORIENTAL_MEDIA_3])

    def test_agotado_hasta_una_pasa_al_siguiente_bloque(self):
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3), bloque(ORIENTAL_ALTA_1)],
                             productos={ORIENTAL_MEDIA_3: GENERAL, ORIENTAL_ALTA_1: GENERAL},
                             rechaza={ORIENTAL_MEDIA_3}, error="¡El producto está agotado!")
        r = re11.reservar(pagina, ["CAT2 - Oriental"], maximo=4)
        self.assertEqual((r.sector, r.cantidad), (ORIENTAL_ALTA_1, 4))
        self.assertEqual(pagina.pedidas, [4, 3, 2, 1, 4])

    def test_un_error_que_no_es_de_cupo_no_baja_la_cantidad(self):
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3), bloque(ORIENTAL_ALTA_1)],
                             productos={ORIENTAL_MEDIA_3: GENERAL, ORIENTAL_ALTA_1: GENERAL},
                             rechaza={ORIENTAL_MEDIA_3}, error="sin respuesta en 60s")
        re11.reservar(pagina, ["CAT2 - Oriental"], maximo=4)
        self.assertEqual(pagina.pedidas, [4, 4])

    def test_el_orden_de_las_palabras_es_la_prioridad(self):
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3), bloque(ORIENTAL_ALTA_1)],
                             productos={ORIENTAL_MEDIA_3: GENERAL, ORIENTAL_ALTA_1: GENERAL})
        r = re11.reservar(pagina, ["Oriental Tribuna Alta", "CAT2 - Oriental"])
        self.assertEqual(r.sector, ORIENTAL_ALTA_1)


class TestSinReserva(unittest.TestCase):
    def test_venta_cerrada_no_pulsa_nada(self):
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3, libre=False), bloque(ORIENTAL_ALTA_1, libre=False)])
        r = re11.reservar(pagina, ["CAT2 - Oriental"])
        self.assertFalse(r.ok)
        self.assertIn("deshabilitados", r.detalle)
        self.assertEqual(pagina.abiertos, [])

    def test_nombre_que_no_existe(self):
        r = re11.reservar(PaginaFalsa([bloque(OCCIDENTAL)]), ["CAT2 - Oriental"])
        self.assertIn("ningun sector del mapa coincide", r.detalle)

    def test_sin_sesion(self):
        r = re11.reservar(PaginaFalsa([], abre=False), ["CAT2 - Oriental"])
        self.assertFalse(r.ok)
        self.assertIn("sesion", r.detalle)


class TestNumerados(unittest.TestCase):
    def test_elige_cuatro_seguidos_en_la_misma_fila(self):
        asientos = [{"id": f"a{n}", "fila": "A", "lugar": str(n)} for n in (1, 3, 5)]
        asientos += [{"id": f"b{n}", "fila": "B", "lugar": str(n)} for n in (7, 8, 9, 10, 11)]
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3, numerado=True)], asientos={ORIENTAL_MEDIA_3: asientos})
        r = re11.reservar(pagina, ["CAT2 - Oriental"], maximo=4)
        self.assertTrue(r.ok)
        self.assertEqual(pagina.asientos_pulsados, ["b7", "b8", "b9", "b10"])
        self.assertEqual(r.asientos, ["Fila B 7", "Fila B 8", "Fila B 9", "Fila B 10"])

    def test_sin_cuatro_juntos_toma_la_tanda_mas_larga(self):
        asientos = [{"id": n, "fila": "A", "lugar": n} for n in ("1", "2", "5", "9")]
        self.assertEqual([a["id"] for a in re11.elegir_juntos(asientos, 4)], ["1", "2"])

    def test_un_asiento_perdido_no_tumba_los_demas(self):
        asientos = [{"id": f"c{n}", "fila": "C", "lugar": str(n)} for n in range(1, 5)]
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3, numerado=True)], asientos={ORIENTAL_MEDIA_3: asientos},
                             asientos_fallan={"c2"})
        r = re11.reservar(pagina, ["CAT2 - Oriental"])
        self.assertTrue(r.ok)
        self.assertEqual(r.cantidad, 3)
        self.assertIn("Asiento reservado", r.detalle)

    def test_bloque_sin_asientos_pasa_al_siguiente(self):
        pagina = PaginaFalsa([bloque(ORIENTAL_MEDIA_3, numerado=True), bloque(ORIENTAL_ALTA_1)],
                             productos={ORIENTAL_ALTA_1: GENERAL})
        r = re11.reservar(pagina, ["CAT2 - Oriental"])
        self.assertEqual(r.sector, ORIENTAL_ALTA_1)


if __name__ == "__main__":
    unittest.main()
