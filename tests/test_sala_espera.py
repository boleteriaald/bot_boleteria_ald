"""Sala de espera: detecta colas reales sin confundirlas con texto fijo de un evento."""
from apoyo import CasoMonitor

TERMINOS_BTS = (
    "EVENTO FINALIZADO\nBTS WORLD TOUR ARIRANG - BOGOTA\nTERMINOS Y CONDICIONES\n"
    + "Texto de relleno de los terminos y condiciones. " * 80
    + "Cuando sea tu turno para comprar, se requerira tu NUMERO DE ARMY MEMBERSHIP."
)


class TestSalaEspera(CasoMonitor):

    def test_cola_real_se_detecta(self):
        en_cola, senal = self.m.detectar_sala_espera("Estas en la fila. Tu turno llegara pronto")
        self.assertTrue(en_cola)

    def test_alta_demanda_de_taquillalive_se_detecta(self):
        texto = ("Tiquetes: Sin disponibilidad por alta demanda del evento, en el momento "
                 "todos los tickets estan en proceso de compra por otros usuarios.")
        self.assertEqual(self.m.detectar_sala_espera(texto), (True, "alta demanda"))

    def test_terminos_largos_con_tu_turno_no_son_una_cola(self):
        self.assertGreater(len(TERMINOS_BTS), self.m.LONGITUD_MAXIMA_PAGINA_ESPERA)
        self.assertEqual(self.m.detectar_sala_espera(TERMINOS_BTS), (False, None))

    def test_texto_vacio(self):
        self.assertEqual(self.m.detectar_sala_espera(""), (False, None))
        self.assertEqual(self.m.detectar_sala_espera(None), (False, None))
