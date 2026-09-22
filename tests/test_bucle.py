"""
Bucle de monitoreo completo, con detectores y Chrome simulados.

Se ejecutan rondas reales de monitorear_urls() y se corta tras N rondas.
"""
from apoyo import CasoMonitor

A = "https://www.ticketmaster.co/event/a"
B = "https://www.ticketmaster.co/event/b"
C = "https://www.ticketmaster.co/event/c"


class DriverFalso:
    def __init__(self, nombre):
        self.nombre = nombre


class TestBucle(CasoMonitor):

    def setUp(self):
        super().setUp()
        self.m.configurar_registro()
        self.m.URLS_A_MONITOREAR = [A, B, C]
        self.m.FILTROS_LOCALIDADES = {}
        self.visitas = []
        self.lecturas = {A: ([], ["x"]), B: ([], ["x"]), C: ([], ["x"])}
        self.falla = set()
        self.muere_tras = None
        self.driver_vivo = {}
        self.m.detectar_bloqueo = lambda driver: (False, None)
        self.m.obtener_nombre_evento = lambda driver: "Evento"
        self.m.obtener_fecha_evento = lambda driver: None
        self.m.sesion_viva = lambda driver: self.driver_vivo.get(driver.nombre, True)
        self.recuperaciones = []

        def recuperar(driver):
            self.recuperaciones.append(driver.nombre)
            return DriverFalso("reconectado")
        self.m.recuperar_sesion = recuperar

        def detector(driver, url):
            self.visitas.append((url[-1], driver.nombre))
            if url == self.muere_tras:
                self.driver_vivo[driver.nombre] = False
            if url in self.falla:
                raise ValueError("fallo de codigo simulado")
            disponibles, agotadas = self.lecturas[url]
            return disponibles, agotadas, url
        self.m.verificar_disponibilidad_ticketmaster = detector

    def correr(self, rondas):
        guardar_real = self.m.guardar_estado
        total = rondas * len(self.m.URLS_A_MONITOREAR)

        def guardar(estado):
            guardar_real(estado)
            if len(self.visitas) >= total:
                raise KeyboardInterrupt          # corta tras la ultima ronda
        self.m.guardar_estado = guardar
        try:
            self.m.monitorear_urls(DriverFalso("inicial"))
        except KeyboardInterrupt:
            pass

    def test_un_error_en_una_url_no_impide_revisar_las_siguientes(self):
        self.falla = {A}
        self.correr(1)
        self.assertEqual([v[0] for v in self.visitas], ["a", "b", "c"])
        registro = self.leer_registro()
        self.assertIn("Error procesando " + A, registro)
        self.assertIn("ValueError: fallo de codigo simulado", registro)

    def test_cada_url_se_visita_una_vez_por_ronda(self):
        self.correr(3)
        self.assertEqual([v[0] for v in self.visitas], list("abc" * 3))

    def test_se_mantiene_la_pausa_tras_disponibilidad(self):
        # Regla del ritmo: la pausa que existia antes de la deduplicacion sigue
        # ocurriendo cada vez que hay disponibilidad, se avise o no.
        self.lecturas[B] = (["Platea 1"], [])
        self.correr(2)
        pausas = [s for s in self.reloj.esperas if s == self.m.PAUSA_TRAS_DISPONIBILIDAD]
        self.assertEqual(len(pausas), 2)

    def test_aviso_fallido_se_reintenta_en_la_ronda_siguiente(self):
        self.lecturas[B] = (["Platea 1"], [])
        resultados = iter([False, True])

        def enviar(mensaje):
            self.enviados.append(mensaje)
            return next(resultados, True)
        self.m.enviar_notificacion = enviar
        self.correr(3)
        self.assertEqual(len(self.enviados), 2)                 # falla, reintento, silencio
        self.assertIn("DISPONIBILIDAD DETECTADA", self.enviados[1])
        registro = self.leer_registro()
        self.assertIn("AVISO NO ENVIADO, se reintentara", registro)
        self.assertIn("AVISO enviado", registro)

    def test_chrome_muere_a_mitad_de_ronda(self):
        self.muere_tras = B
        self.correr(1)
        self.assertEqual(self.visitas, [("a", "inicial"), ("b", "inicial"), ("c", "reconectado")])
        self.assertEqual(self.recuperaciones, ["inicial"])       # B no se reintenta

    def test_registro_por_url_y_lectura_vacia(self):
        self.lecturas[C] = ([], [])
        self.correr(1)
        registro = self.leer_registro()
        self.assertIn("Ronda 1 - 3 URLs", registro)
        self.assertIn("disp=0 agot=1 filtradas=0 | " + A, registro)
        self.assertIn("LECTURA VACIA | " + C, registro)
