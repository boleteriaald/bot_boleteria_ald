"""
Reserva de boletas en Ticketmaster: cuantas pedir, que elegir y donde parar.

PaginaFalsa reproduce el orden de pantallas observado en Carlos Vives
(sep-2026): sectores -> tarifa -> boletas listadas -> garantia -> entrega ->
confirmar -> pago. `cupo` son las boletas realmente libres; la pagina solo lo
delata rechazando la seleccion al pulsar Continuar.
"""
import unittest
from unittest import mock

import apoyo  # noqa: F401  (pone la raiz del proyecto en sys.path)
import reserva_ticketmaster as rt

SECTOR = "VIP (silletería no numerada)"
TEXTO_ERROR = "No hay boletas disponibles en esta sección"


class PaginaFalsa:
    numerada = False        # True: "Buscar mejores asientos" en vez de Continuar, y el contador corre desde ahi

    def __init__(self, cupo=4, tope=4, entregas=("Boleto Digital en la App (más seguro)",),
                 garantia=True, mapa_abre=True, sectores=(SECTOR,), se_atasca_en=None, numerada=False):
        self.cupo, self.tope, self.entregas = cupo, tope, entregas
        self.garantia_paso, self.mapa_abre, self.sectores = garantia, mapa_abre, sectores
        self.se_atasca_en = se_atasca_en
        self.numerada = numerada
        self.estado = "evento"
        self.cantidad = 0
        self.sector = None
        self.quiere_garantia = True
        self.clics = []
        self.limpiezas = 0
        self.intentos = []          # cantidad con la que se pulso Continuar

    # --- interfaz que usa reservar() ---
    def abrir_mapa(self):
        if not self.mapa_abre:
            return False
        self.estado = "mapa"
        return True

    def elegir_sector(self, nombre):
        if nombre not in self.sectores or self.estado != "mapa":
            return False
        self.sector, self.cantidad, self.estado = nombre, 0, "tarifa"
        return True

    def fijar_cantidad(self, n):
        self.cantidad = min(n, self.tope)
        self.aviso_limite = "Límite de cantidad: máximo disponible para esta tarifa" if self.tope < n else ""
        return self.cantidad

    def limpiar(self):
        self.limpiezas += 1
        self.estado, self.cantidad = "mapa", 0
        return True

    def clic(self, texto):
        self.clics.append(texto)
        if self.estado == "evento":
            return False
        if texto == rt.BOTON_ASIENTOS:
            return self.estado == "tarifa" and self.numerada and self._continuar()
        if texto == "Continuar":
            if self.estado == "tarifa" and self.numerada:
                return False                    # en una numerada no hay Continuar en este paso
            return self._continuar()
        if texto == "no gracias" and self.estado == "garantia":
            self.quiere_garantia = False
            return True
        if texto == rt.ENTREGA_OBLIGATORIA and self.estado == "entrega":
            if not any(e.startswith(texto) for e in self.entregas):
                return False
            self.estado = "confirmar"
            return True
        if texto == "Confirmar reserva" and self.estado == "confirmar":
            self.estado = "pago"
            return True
        return False

    def esperar(self, condicion, segundos):
        t = self.texto()
        return t if condicion(t) else None

    def texto(self):
        n = self.cantidad
        total = f"$ {n * 380000 + 7000:,}".replace(",", ".")
        resumen = (f"Resumen de compra\n{n} x VIP\n"
                   + ("GARANTIA EXTENDIDA\n$ 106.400\n" if self.quiere_garantia and self.estado != "tarifa" else "")
                   + f"{n} Total\n{total}\n")
        if self.estado == "mapa":
            return "Seleccionar sector\n" + "\n".join(self.sectores)
        if self.estado == "tarifa":
            boton = rt.BOTON_ASIENTOS if self.numerada else "Continuar"
            return (f"Seleccionar tarifa\nEntrada | Etapa 1\n$ 329.000 + $ 51.000\n{n}\n"
                    f"{boton}")
        if self.estado == "error":
            if self.numerada:
                return "Seleccionar tarifa\nLo sentimos!\nNo hay asientos libres para esta sección.\nelige otra sección."
            return f"Seleccionar tarifa\n{TEXTO_ERROR}\nLimpiar selección\nContinuar"
        if self.estado == "lista":
            # En las numeradas el contador de la reserva corre desde que se asignan los asientos.
            reloj = "La reserva expira en 02:54\n" if self.numerada else ""
            return reloj + "Seleccionar tarifa\n" + "VIP\nCambiar tarifa\n" * n + "Continuar"
        if self.estado == "garantia":
            return ("¿Quieres recuperar el total de tu compra?\nno gracias\n$ 0\nContinuar\n" + resumen)
        if self.estado == "entrega":
            return ("Selecciona cómo deseas recibir tus entradas\n"
                    + "\n".join(self.entregas) + "\n" + resumen)
        if self.estado == "confirmar":
            return f"Confirma la operación\nBoleto Digital en la App (más seguro)\n$ 7.000\n{resumen}Confirmar reserva"
        if self.estado == "pago":
            return ("La reserva expira en 04:52\nSelecciona cómo deseas abonar tus entradas\n"
                    "Efectivo\nDébito Bancario PSE\nTarjeta de Crédito o Débito\nArmatuvaca\n" + resumen)
        return "Evento"

    def _continuar(self):
        if self.se_atasca_en == self.estado:
            return True                         # el clic "funciona" pero la pagina no cambia
        if self.estado == "tarifa":
            self.intentos.append(self.cantidad)
            self.estado = "lista" if self.cantidad <= self.cupo else "error"
        elif self.estado == "lista":
            self.estado = "garantia" if self.garantia_paso else "entrega"
        elif self.estado == "garantia":
            if self.quiere_garantia:
                return False                    # la garantia bloquea el avance si se deja marcada
            self.estado = "entrega"
        else:
            return False
        return True


def reservar(pagina, sectores=(SECTOR,), **kw):
    return rt.reservar(pagina, list(sectores), **kw)


class TestCantidad(unittest.TestCase):

    def test_hay_cuatro_reserva_cuatro(self):
        p = PaginaFalsa(cupo=4)
        r = reservar(p)
        self.assertTrue(r.ok)
        self.assertEqual((r.cantidad, r.pedidas), (4, 4))
        self.assertEqual(p.intentos, [4])
        self.assertEqual(p.limpiezas, 0)

    def test_si_no_hay_cuatro_baja_de_uno_en_uno_hasta_las_que_haya(self):
        p = PaginaFalsa(cupo=2)
        r = reservar(p)
        self.assertTrue(r.ok)
        self.assertEqual(r.cantidad, 2)
        self.assertEqual(p.intentos, [4, 3, 2])      # 4 y 3 rechazadas, 2 aceptada
        self.assertEqual(p.limpiezas, 2)             # se deshace la seleccion tras cada rechazo

    def test_deja_registro_de_cada_intento_con_el_texto_real_del_rechazo(self):
        # El aviso real de "no hay boletas" nunca se ha visto: debe quedar en el registro.
        r = reservar(PaginaFalsa(cupo=2))
        self.assertEqual(len(r.intentos), 3)
        self.assertTrue(r.intentos[0].startswith("4: rechazada ["))
        self.assertIn(TEXTO_ERROR, r.intentos[0])
        self.assertTrue(r.intentos[1].startswith("3: rechazada ["))
        self.assertEqual(r.intentos[2], "2: ok")

    def test_a_la_primera_un_solo_intento(self):
        self.assertEqual(reservar(PaginaFalsa(cupo=4)).intentos, ["4: ok"])

    def test_sin_boletas_registra_todos_los_intentos_rechazados(self):
        r = reservar(PaginaFalsa(cupo=0))
        self.assertEqual([i.split(":")[0] for i in r.intentos], ["4", "3", "2", "1"])
        self.assertTrue(all("rechazada" in i for i in r.intentos))

    def test_queda_una_sola_boleta(self):
        p = PaginaFalsa(cupo=1)
        r = reservar(p)
        self.assertEqual((r.ok, r.cantidad), (True, 1))
        self.assertEqual(p.intentos, [4, 3, 2, 1])

    def test_sin_boletas_no_reserva_nada_y_dice_por_que(self):
        p = PaginaFalsa(cupo=0)
        r = reservar(p)
        self.assertFalse(r.ok)
        self.assertFalse(r.retenidas)
        self.assertIn("ni para 1", r.detalle)
        self.assertEqual(p.intentos, [4, 3, 2, 1])

    def test_minimo_configurable(self):
        p = PaginaFalsa(cupo=1)
        r = reservar(p, minimo=2)
        self.assertFalse(r.ok)
        self.assertEqual(p.intentos, [4, 3, 2])      # no intenta 1

    def test_si_el_selector_no_sube_de_la_cuenta_no_repite_ese_numero(self):
        # El "+" se queda en 2 (la pagina lo frena): se pide con 2, no se insiste con 4 y 3.
        p = PaginaFalsa(cupo=2, tope=2)
        r = reservar(p)
        self.assertEqual((r.ok, r.cantidad, r.pedidas), (True, 2, 4))
        self.assertEqual(p.intentos, [2])

    def test_selector_frenado_deja_el_aviso_real_en_los_intentos(self):
        # Iron Maiden sector 107 (real): pedir 4, el "+" se frena en 2 con "Limite de cantidad".
        r = reservar(PaginaFalsa(cupo=2, tope=2))
        self.assertTrue(r.ok)
        self.assertEqual(r.cantidad, 2)
        self.assertTrue(r.intentos[0].startswith("4: selector frenado en 2 [Límite de cantidad"))
        self.assertEqual(r.intentos[-1], "2: ok")

    def test_selector_frenado_y_ademas_rechazado_baja_desde_lo_marcado(self):
        # El "+" frena en 2 y aun asi sobra: el siguiente intento es 1, no otra vez 2 (ni 3).
        p = PaginaFalsa(cupo=1, tope=2)
        r = reservar(p)
        self.assertEqual((r.ok, r.cantidad), (True, 1))
        self.assertEqual(p.intentos, [2, 1])

    def test_selector_atascado_en_cero(self):
        p = PaginaFalsa(tope=0)
        r = reservar(p)
        self.assertFalse(r.ok)
        self.assertIn("no pasa de 0", r.detalle)
        self.assertEqual(p.intentos, [])


class TestNumeradas(unittest.TestCase):
    """Localidad numerada (Iron Maiden): Buscar mejores asientos, contador temprano, otro error."""

    PERMITIDOS = {"Continuar", "no gracias", rt.ENTREGA_OBLIGATORIA, "Confirmar reserva", rt.BOTON_ASIENTOS}

    def test_busca_los_asientos_y_sigue_hasta_el_pago(self):
        p = PaginaFalsa(cupo=4, numerada=True)
        r = reservar(p)
        self.assertTrue(r.ok)
        self.assertEqual(r.cantidad, 4)
        self.assertIn(rt.BOTON_ASIENTOS, p.clics)
        self.assertLessEqual(set(p.clics), self.PERMITIDOS)

    def test_el_contador_temprano_no_se_confunde_con_el_pago(self):
        # Tras asignar asientos ya dice "La reserva expira en": aun faltan garantia, entrega y confirmar.
        p = PaginaFalsa(cupo=4, numerada=True)
        r = reservar(p)
        self.assertEqual(p.estado, "pago")
        self.assertIn("no gracias", p.clics)
        self.assertIn("Confirmar reserva", p.clics)
        self.assertTrue(r.ok)

    def test_sin_asientos_para_4_baja_hasta_los_que_haya(self):
        p = PaginaFalsa(cupo=2, numerada=True)
        r = reservar(p)
        self.assertTrue(r.ok)
        self.assertEqual(r.cantidad, 2)
        self.assertEqual(p.intentos, [4, 3, 2])
        self.assertIn("No hay asientos libres", r.intentos[0])

    def test_sin_asientos_en_la_seccion_falla_con_el_motivo(self):
        r = reservar(PaginaFalsa(cupo=0, numerada=True))
        self.assertFalse(r.ok)
        self.assertFalse(r.retenidas)
        self.assertTrue(all("No hay asientos libres" in i for i in r.intentos))


class TestSectores(unittest.TestCase):

    def test_sector_que_no_aparece_no_prueba_cantidades(self):
        p = PaginaFalsa(sectores=("Otro",))
        r = reservar(p)
        self.assertFalse(r.ok)
        self.assertIn("no aparece", r.detalle)
        self.assertEqual(p.intentos, [])

    def test_pasa_al_siguiente_sector_si_el_primero_no_tiene(self):
        class DosSectores(PaginaFalsa):
            def _continuar(self):
                if self.estado == "tarifa" and self.sector == "A":
                    self.intentos.append(self.cantidad)
                    self.estado = "error"
                    return True
                return super()._continuar()
        p = DosSectores(sectores=("A", "B"))
        r = reservar(p, sectores=("A", "B"))
        self.assertTrue(r.ok)
        self.assertEqual(r.sector, "B")

    def test_mapa_que_no_abre(self):
        r = reservar(PaginaFalsa(mapa_abre=False))
        self.assertFalse(r.ok)
        self.assertIn("mapa", r.detalle)


class TestLimites(unittest.TestCase):
    """Lo que el usuario fijo: nunca garantia, siempre Boleto Digital, parar antes de pagar."""

    def test_rechaza_la_garantia_y_no_la_acepta_nunca(self):
        p = PaginaFalsa()
        r = reservar(p)
        self.assertTrue(r.ok)
        self.assertIn("no gracias", p.clics)
        self.assertFalse(p.quiere_garantia)
        self.assertNotIn("$ 106.400", r.total)
        self.assertEqual(r.total, "$ 1.527.000")

    def test_evento_sin_paso_de_garantia(self):
        r = reservar(PaginaFalsa(garantia=False))
        self.assertTrue(r.ok)

    def test_elige_boleto_digital_aunque_haya_otras_entregas(self):
        p = PaginaFalsa(entregas=("Entrega a domicilio", "Boleto Digital en la App (más seguro)", "Recoger en taquilla"))
        r = reservar(p)
        self.assertTrue(r.ok)
        self.assertIn(rt.ENTREGA_OBLIGATORIA, p.clics)
        for otra in ("Entrega a domicilio", "Recoger en taquilla"):
            self.assertNotIn(otra, p.clics)

    def test_si_no_hay_boleto_digital_avisa_y_no_elige_otra_entrega(self):
        p = PaginaFalsa(entregas=("Entrega a domicilio",))
        r = reservar(p)
        self.assertFalse(r.ok)
        self.assertTrue(r.retenidas)
        self.assertIn("no elegi otra entrega", r.detalle)
        self.assertNotIn("Entrega a domicilio", p.clics)

    def test_el_formulario_de_tarjeta_directo_tambien_es_el_pago(self):
        class TarjetaDirecta(PaginaFalsa):
            def texto(self):
                if self.estado == "pago":
                    return ("La reserva expira en 04:26\nIngresa los datos de tu tarjeta\n"
                            "Número de tarjeta\nResumen de compra\n4 Total\n$ 1.527.000\n")
                return super().texto()
        p = TarjetaDirecta()
        r = reservar(p)
        self.assertTrue(r.ok)
        self.assertEqual((r.expira, r.total), ("04:26", "$ 1.527.000"))
        self.assertLessEqual(set(p.clics), {"Continuar", "no gracias", rt.ENTREGA_OBLIGATORIA, "Confirmar reserva"})

    def test_se_detiene_en_el_pago_sin_tocar_ningun_medio(self):
        p = PaginaFalsa()
        r = reservar(p)
        self.assertEqual(p.estado, "pago")
        self.assertEqual(r.expira, "04:52")
        permitidos = {"Continuar", "no gracias", rt.ENTREGA_OBLIGATORIA, "Confirmar reserva"}
        self.assertLessEqual(set(p.clics), permitidos)
        for medio in ("Tarjeta", "PSE", "Efectivo", "Armatuvaca", "Sí, quiero"):
            self.assertFalse(any(medio in c for c in p.clics))

    def test_el_enlace_de_terminos_no_se_confunde_con_la_garantia_puesta(self):
        p = PaginaFalsa()
        r = reservar(p)
        self.assertTrue(r.ok)
        self.assertEqual(p.clics.count("no gracias"), 1)     # se rechaza una vez, no en bucle

    def test_un_fallo_deja_en_el_detalle_lo_que_mostraba_la_pantalla(self):
        p = PaginaFalsa(se_atasca_en="lista")
        r = reservar(p)
        self.assertIn("Pantalla:", r.detalle)
        self.assertIn("Cambiar tarifa", r.detalle)

    def test_pagina_que_no_avanza_falla_sin_dar_vueltas_eternas(self):
        p = PaginaFalsa(se_atasca_en="lista")
        r = reservar(p)
        self.assertFalse(r.ok)
        self.assertTrue(r.retenidas)
        self.assertIn("no avanza", r.detalle)
        self.assertLess(len(p.clics), 20)

    def test_se_respeta_el_tiempo_maximo(self):
        ahora = iter([0, 0, 1000, 1000, 1000, 1000])
        r = reservar(PaginaFalsa(cupo=0), reloj=lambda: next(ahora))
        self.assertFalse(r.ok)
        self.assertIn("tiempo", r.detalle)


class TestContinuarSinRespuesta(unittest.TestCase):

    def test_un_clic_perdido_se_repite_una_vez_en_la_misma_pantalla(self):
        class ClicPerdido(PaginaFalsa):
            perdidos = 1

            def _continuar(self):
                if self.estado == "tarifa" and self.perdidos:
                    self.perdidos -= 1
                    return True                 # el primer clic no hace nada
                return super()._continuar()
        p = ClicPerdido()
        r = reservar(p)
        self.assertTrue(r.ok)
        self.assertEqual(r.cantidad, 4)
        self.assertEqual(p.limpiezas, 0)        # no se bajo de cantidad por un clic perdido


class StaleElementReferenceException(Exception):
    """El modulo la reconoce por su NOMBRE, sin importar selenium."""


class Elemento:
    def __init__(self, falla_clic=False, caduco=False):
        self.clics = 0
        self.falla_clic = falla_clic
        self.caduco = caduco

    def click(self):
        if self.caduco:
            raise StaleElementReferenceException("elemento caduco")
        if self.falla_clic:
            raise RuntimeError("otro elemento lo tapa")
        self.clics += 1


class DriverTexto:
    """Driver minimo: da el texto de la pagina y un Elemento a cualquier busqueda."""

    def __init__(self, texto="", garantia=None, activa=()):
        self.texto = texto
        self.current_url = "https://www.ticketmaster.co/event/x"
        self.scripts = []
        self.elemento = Elemento()
        self.garantia = garantia
        self.activa = iter(activa)
        self.clics_js = []
        self.cola = []      # elementos que devuelven las proximas busquedas, en orden

    def execute_script(self, script, *args):
        self.scripts.append(script)
        if script == rt.JS_GARANTIA:
            return self.garantia
        if script == rt.JS_GARANTIA_ACTIVA:
            return next(self.activa, False)
        if "document.body.innerText" in script:
            return self.texto
        if script.startswith("arguments[0].click"):
            if args[0].caduco:
                raise StaleElementReferenceException("elemento caduco")
            self.clics_js.append(args[0])
            return None
        return self.cola.pop(0) if self.cola else self.elemento


class TestAbrirMapaReal(unittest.TestCase):

    def pagina(self, texto):
        return rt.PaginaSelenium(DriverTexto(texto), "https://x", lambda driver, url: None)

    def test_sin_sesion_lo_dice_desde_el_principio(self):
        p = self.pagina("Soporte\nIngresar / Registrarse\nVer entradas")
        r = rt.reservar(p, [SECTOR])
        self.assertFalse(r.ok)
        self.assertIn("no hay sesion iniciada", r.detalle)
        self.assertIn("mapa", r.detalle)

    def pagina_con(self, driver):
        return rt.PaginaSelenium(driver, "https://x", lambda d, u: None)

    def test_los_clics_son_nativos_y_no_de_javascript(self):
        # Un clic de JavaScript sobre la garantia no la activo (2a reserva real).
        driver = DriverTexto()
        self.assertTrue(self.pagina_con(driver).clic("Continuar"))
        self.assertEqual(driver.elemento.clics, 1)
        self.assertEqual(driver.clics_js, [])

    def test_si_algo_tapa_el_elemento_cae_al_clic_de_javascript(self):
        driver = DriverTexto()
        driver.elemento = Elemento(falla_clic=True)
        self.assertTrue(self.pagina_con(driver).clic("Continuar"))
        self.assertEqual(driver.clics_js, [driver.elemento])

    def test_elemento_caduco_se_vuelve_a_buscar_y_no_aborta(self):
        # 5a reserva real: la pagina se repinto entre buscar y pulsar "Ver entradas".
        caduco, bueno = Elemento(caduco=True), Elemento()
        driver = DriverTexto()
        driver.cola = [caduco, bueno]
        self.assertTrue(self.pagina_con(driver).clic("Ver entradas"))
        self.assertEqual(bueno.clics, 1)

    def test_si_caduca_siempre_devuelve_falso_en_vez_de_lanzar(self):
        driver = DriverTexto()
        driver.cola = [Elemento(caduco=True) for _ in range(3)]
        self.assertFalse(self.pagina_con(driver).clic("Ver entradas"))

    def test_garantia_con_elemento_caduco_tambien_reintenta(self):
        caduco, bueno = Elemento(caduco=True), Elemento()
        driver = DriverTexto(garantia={"ya": False, "el": [caduco]}, activa=[True])
        driver.garantia = {"ya": False, "el": [caduco]}
        original = driver.execute_script

        llamadas = {"n": 0}

        def script(s, *a):
            if s == rt.JS_GARANTIA:
                llamadas["n"] += 1
                # la 1a vez (comprobar) y la 2a (comprobar ya) devuelven lo normal;
                # la 3a (buscar candidato) da el caduco; la 4a, el bueno
                return {"ya": False, "el": [caduco if llamadas["n"] <= 3 else bueno]}
            return original(s, *a)
        driver.execute_script = script
        with mock.patch.object(rt, "ESPERA_ACTIVA", 0):
            self.assertTrue(self.pagina_con(driver).clic(rt.RECHAZO_GARANTIA))
        self.assertEqual(bueno.clics, 1)

    def test_fila_de_queue_it_se_detecta_y_conserva_la_pestana(self):
        driver = DriverTexto("Estas en la fila")
        driver.current_url = "https://ticketmasterco.queue-it.net/?c=x"
        p = self.pagina_con(driver)
        r = rt.reservar(p, [SECTOR])
        self.assertFalse(r.ok)
        self.assertTrue(r.conservar_pestana)
        self.assertIn("Queue-it", r.detalle)

    def test_un_fallo_normal_no_conserva_la_pestana(self):
        driver = DriverTexto("Soporte\nIngresar / Registrarse\nVer entradas")
        driver.current_url = "https://www.ticketmaster.co/event/x"
        r = rt.reservar(self.pagina_con(driver), [SECTOR])
        self.assertFalse(r.conservar_pestana)

    def test_el_aviso_de_limite_detiene_el_plus_sin_clics_de_mas(self):
        # Texto real de la pagina con el "+" ya frenado en 2.
        NL = chr(92) + "n"
        texto = NL.join(["Seleccionar tarifa", "Entrada", "$ 700.000 + $ 142.000", "2", "Límite de cantidad",
                         "Has seleccionado el máximo disponible para esta tarifa", "Continuar"]) 
        texto = texto.replace(NL, chr(10))
        driver = DriverTexto(texto)
        p = self.pagina_con(driver)
        with mock.patch.object(rt, "ESPERA_RESPUESTA", 0):
            self.assertEqual(p.fijar_cantidad(4), 2)
        # No insiste con el "+"; su unico clic es el "Continuar" del dialogo, que lo cierra.
        self.assertNotIn(rt.JS_SUMAR, driver.scripts)
        self.assertIn(rt.JS_CERRAR_AVISO, driver.scripts)
        self.assertEqual(driver.elemento.clics, 1)
        self.assertIn("Límite de cantidad", p.aviso_limite)

    def test_evento_sin_ver_entradas_ya_muestra_los_sectores(self):
        # Iron Maiden: la pagina abre directamente en "Seleccionar sector".
        driver = DriverTexto(chr(10).join(["Mis entradas", "Cerrar sesión", "Seleccionar sector", "Front Field Sur"]))
        p = self.pagina_con(driver)
        self.assertTrue(p.abrir_mapa())
        self.assertNotIn("Ver entradas", [a for a in driver.scripts if a == "Ver entradas"])

    def pagina_con_secciones(self, filas, claves=()):
        """Driver cuyo paso de seccion devuelve `filas`; devuelve (pagina, elementos por nombre)."""
        driver_ref = []

        class Fila(Elemento):
            def click(self):
                super().click()
                driver_ref[0].texto = "Seleccionar tarifa"     # como la pagina: avanza al elegir

        elementos = {nombre: Fila() for nombre, _ in filas}

        class Secciones(DriverTexto):
            def execute_script(self, script, *args):
                if script == rt.JS_ELEGIR_SECTOR:
                    self.texto = "Seleccionar sección"
                    return self.elemento
                if script == rt.JS_SECCIONES:
                    return [{"el": elementos[n], "texto": n, "libre": libre} for n, libre in filas]
                return super().execute_script(script, *args)
        driver = Secciones("Seleccionar sección")
        driver_ref.append(driver)
        pagina = self.pagina_con(driver)
        pagina.claves_seccion = list(claves)
        return pagina, elementos

    def test_sector_numerado_sin_claves_elige_la_primera_seccion_libre(self):
        p, el = self.pagina_con_secciones([("101 (+12)", False), ("103 (+12)", True), ("105 (+12)", True)])
        self.assertTrue(p.elegir_sector("101 - 103 - 105 - 107"))
        self.assertEqual([el[n].clics for n in el], [0, 1, 0])

    def test_la_palabra_107_elige_la_seccion_107_y_no_la_primera_libre(self):
        filas = [("101 (+12)", True), ("103 (+12)", True), ("105 (+12)", True), ("107 (+12)", True)]
        p, el = self.pagina_con_secciones(filas, claves=["back", "107"])
        self.assertTrue(p.elegir_sector("101 - 103 - 105 - 107"))
        self.assertEqual([el[n].clics for n in el], [0, 0, 0, 1])

    def test_si_la_seccion_pedida_esta_agotada_no_reserva_otra(self):
        filas = [("101 (+12)", True), ("107 (+12)", False)]
        p, el = self.pagina_con_secciones(filas, claves=["107"])
        self.assertFalse(p.elegir_sector("101 - 103 - 105 - 107"))
        self.assertEqual([el[n].clics for n in el], [0, 0])      # no cae en la 101

    def test_palabra_que_no_nombra_ninguna_seccion_no_restringe(self):
        # "back" es de otro sector: aqui vale la primera libre.
        p, el = self.pagina_con_secciones([("111 (+18)", True), ("113 (+18)", True)], claves=["back"])
        self.assertTrue(p.elegir_sector("111 - 113 - 115"))
        self.assertEqual([el[n].clics for n in el], [1, 0])

    def test_todas_las_secciones_agotadas(self):
        p, el = self.pagina_con_secciones([("101 (+12)", False), ("103 (+12)", False)])
        self.assertFalse(p.elegir_sector("101 - 103 - 105 - 107"))

    def test_tras_no_hay_asientos_libres_se_vuelve_con_elige_otra_seccion(self):
        textos = []

        class Error(DriverTexto):
            def execute_script(self, script, *args):
                if script == rt.JS_CLIC_TEXTO:
                    textos.append(args[0])
                    if args[0] == "elige otra sección":
                        self.texto = "Seleccionar sector"
                    return self.elemento
                return super().execute_script(script, *args)
        driver = Error("Lo sentimos! No hay asientos libres para esta sección. elige otra sección.")
        self.assertTrue(self.pagina_con(driver).limpiar())
        self.assertEqual(textos[0], "elige otra sección")      # el primero que se prueba

    def test_las_secciones_excluidas_no_se_eligen_y_se_anota_la_elegida(self):
        filas = [("101 (+12)", True), ("103 (+12)", True), ("105 (+12)", True)]
        p, el = self.pagina_con_secciones(filas)
        p.excluir_secciones = {"101 (+12)"}
        self.assertTrue(p.elegir_sector("101 - 103 - 105 - 107"))
        self.assertEqual([el[n].clics for n in el], [0, 1, 0])
        self.assertEqual(p.seccion, "103 (+12)")
        self.assertFalse(p.sin_secciones)

    def test_cuando_ya_no_queda_ninguna_se_avisa_que_el_sector_se_acabo(self):
        filas = [("101 (+12)", True), ("103 (+12)", True)]
        p, el = self.pagina_con_secciones(filas)
        p.excluir_secciones = {"101 (+12)", "103 (+12)"}
        self.assertFalse(p.elegir_sector("101 - 103 - 105 - 107"))
        self.assertTrue(p.sin_secciones)
        self.assertEqual([el[n].clics for n in el], [0, 0])

    def test_reservar_copia_la_seccion_y_el_fin_de_secciones_a_la_reserva(self):
        class ConSeccion(PaginaFalsa):
            seccion = "117 (+18)"
            sin_secciones = False
        r = reservar(ConSeccion())
        self.assertEqual(r.seccion, "117 (+18)")
        self.assertFalse(r.sin_mas_secciones)

        class SinMas(PaginaFalsa):
            seccion = ""
            sin_secciones = True

            def elegir_sector(self, nombre):
                return False
        r = reservar(SinMas())
        self.assertTrue(r.sin_mas_secciones)
        self.assertFalse(r.ok)

    def test_el_mensaje_de_reserva_dice_la_seccion(self):
        r = rt.Reserva(True, "117-118-119-120", 4, 4, "$ 2.668.000", "04:59", seccion="117 (+18)")
        self.assertIn("117-118-119-120 [seccion 117 (+18)]", rt.mensaje(r, "Calvin", "https://x", "10:00:00"))

    def test_texto_sin_elemento_no_hace_clic(self):
        driver = DriverTexto()
        driver.elemento = None
        self.assertFalse(self.pagina_con(driver).clic("Continuar"))

    def test_garantia_prueba_del_elemento_mas_interno_al_mas_externo_hasta_que_quede_activa(self):
        strong, cabecera, li = Elemento(), Elemento(), Elemento()
        driver = DriverTexto(garantia={"ya": False, "el": [strong, cabecera, li]}, activa=[False, True])
        with mock.patch.object(rt, "ESPERA_ACTIVA", 0):
            self.assertTrue(self.pagina_con(driver).clic(rt.RECHAZO_GARANTIA))
        self.assertEqual((strong.clics, cabecera.clics, li.clics), (1, 1, 0))

    def test_garantia_que_no_se_activa_devuelve_falso(self):
        elementos = [Elemento(), Elemento(), Elemento()]
        driver = DriverTexto(garantia={"ya": False, "el": elementos})
        with mock.patch.object(rt, "ESPERA_ACTIVA", 0):
            self.assertFalse(self.pagina_con(driver).clic(rt.RECHAZO_GARANTIA))
        self.assertEqual([e.clics for e in elementos], [1, 1, 1])

    def test_garantia_ya_rechazada_no_se_toca(self):
        elemento = Elemento()
        driver = DriverTexto(garantia={"ya": True, "el": [elemento]})
        self.assertTrue(self.pagina_con(driver).clic(rt.RECHAZO_GARANTIA))
        self.assertEqual(elemento.clics, 0)

    def test_garantia_que_no_esta_en_la_pagina(self):
        self.assertFalse(self.pagina_con(DriverTexto(garantia=None)).clic(rt.RECHAZO_GARANTIA))

    def test_con_sesion_no_se_queja_de_la_sesion(self):
        p = self.pagina("Mis entradas\nCerrar sesión\nVer entradas\nSeleccionar sector")
        self.assertTrue(p.abrir_mapa())
        self.assertEqual(p.motivo, "")


class TestMensaje(unittest.TestCase):

    def test_reserva_completa(self):
        m = rt.mensaje(rt.Reserva(True, SECTOR, 4, 4, "$ 1.527.000", "04:52"), "Carlos Vives", "https://x", "10:00:00")
        for parte in ("RESERVA LISTA", "4 x " + SECTOR, "$ 1.527.000", "04:52", "https://x"):
            self.assertIn(parte, m)
        self.assertNotIn("Solo se pudieron", m)

    def test_reserva_parcial_lo_dice(self):
        m = rt.mensaje(rt.Reserva(True, SECTOR, 2, 4, "$ 767.000", "04:50"), "Evento", "https://x", "10:00:00")
        self.assertIn("Solo se pudieron reservar 2 de 4", m)

    def test_resumen_de_varias_reservas(self):
        r1 = rt.Reserva(True, "VIP (GRAMILLA)", 4, 4, "$ 4.324.000", "04:59")
        r2 = rt.Reserva(True, "NORTE ALTA", 2, 4, "$ 792.000", "04:51")
        r3 = rt.Reserva(False, "SUR ALTA", detalle="sin boletas")
        m = rt.mensaje_resumen([r1, r2, r3], "BTS", "https://x", "10:00:00")
        for parte in ("2 RESERVA(S) LISTA(S)", "4 x VIP (GRAMILLA)", "2 x NORTE ALTA", "$ 792.000", "04:51",
                      "1 no se pudieron", "vencen solas"):
            self.assertIn(parte, m)
        self.assertNotIn("SUR ALTA", m.split("(1 no se pudieron")[0])

    def test_resumen_sin_ninguna_lista(self):
        m = rt.mensaje_resumen([rt.Reserva(False, "A"), rt.Reserva(False, "B")], "BTS", "https://x", "10:00:00")
        self.assertIn("NINGUNA RESERVA LISTA", m)

    def test_mensaje_parcial_resume_la_bajada(self):
        r = rt.Reserva(True, SECTOR, 2, 4, "$ 767.000", "04:50",
                       intentos=["4: rechazada [x]", "3: rechazada [x]", "2: ok"])
        self.assertIn("Intentos: 4 no, 3 no, 2 si", rt.mensaje(r, "E", "https://x", "10:00:00"))

    def test_mensaje_de_fallo_resume_los_intentos(self):
        r = rt.Reserva(False, SECTOR, detalle="no hay boletas ni para 1",
                       intentos=["4: rechazada [x]", "3: rechazada [x]", "2: rechazada [x]", "1: rechazada [x]"])
        self.assertIn("Intentos: 4 no, 3 no, 2 no, 1 no", rt.mensaje(r, "E", "https://x", "10:00:00"))

    def test_fallo_limpio_y_fallo_con_boletas_retenidas(self):
        limpio = rt.mensaje(rt.Reserva(False, SECTOR, detalle="no hay boletas ni para 1"), "E", "https://x", "10:00:00")
        self.assertIn("NO PUDE RESERVAR", limpio)
        self.assertNotIn("retenidas", limpio)
        retenido = rt.mensaje(rt.Reserva(False, SECTOR, 3, 4, detalle="la pagina no avanza", retenidas=True),
                              "E", "https://x", "10:00:00")
        self.assertIn("3 boleta(s) retenidas", retenido)


if __name__ == "__main__":
    unittest.main()
