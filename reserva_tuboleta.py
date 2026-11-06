"""
Anade boletas de Tuboleta al carrito ("Mejor sitio") y SE DETIENE: nunca paga.

El bot abre la pagina de seleccion del evento en el navegador de reserva, elige la
localidad, marca en "Cantidad de boletas" la mayor cantidad que deje la pagina (o
`maximo`, si se fija) y pulsa "Anadir al carrito". Si la pagina lo rechaza, repite con
una menos (10 -> 9 -> ... -> 1): asi se queda con las que haya. Luego avisa; el pago lo
hace el usuario desde "Mi cesta" en la pestana que queda abierta.

Lo que se sabe de la pagina (Tuboleta es SecuTix; leido el 6-nov-2026 en
`gencolvschl.checkout.tuboleta.com` con Colombia vs Chile a la venta, y en
`tbpgpal.checkout.tuboleta.com` con Reykon agotado):
  - `selection/event/seat?...&table=1` muestra la tabla "Mejor sitio" dentro de
    `form#event_form` (POST a /selection/event/submit). Sin `table=1` puede salir el plano.
  - Cada fila `tr` de `tbody`: la localidad en `th.category` ("OCCIDENTAL 3er PISO"), la
    tarifa en `.audience-subcat-name` ("PRECIO FULL") y la cantidad en
    `td.quantity select[name="eventFormData[i].quantity"]`, con opciones 0..N (N = el tope
    por compra; en Colombia vs Chile, 4). Una localidad agotada es una sola fila
    `category_sold_out_waiting_list` con "Agotado" y "Inscribirme en la lista de espera",
    sin selector.
  - "Preferencia" (`select[name^="preferredAreas"]`) se deja en "Automatico".
  - "Anadir al carrito" es `a#book` (functions.validateQuantities). Errores en
    `.main_content_notification` con `section.message.error`; con 0 marcadas sale
    "Olvidaste seleccionar la cantidad de boletas que deseas comprar."
  - La cesta: `#account_cart` con aria-label "Ir a la cesta de compra, N productos en la
    cesta" y `#account_cart_button.empty_cart` si esta vacia.

SIN VERIFICAR en vivo (no se ha pulsado "Anadir al carrito" con boletas reales): a que
pantalla lleva el exito, el texto exacto del rechazo por falta de boletas y si el tope
del selector ya refleja lo que queda. Por eso el exito se decide por la cesta (sube el
numero de productos) y, si la pagina cambia sin poder confirmarlo, se avisa igual con la
pestana abierta: un aviso de mas molesta, uno de menos cuesta la boleta.

La logica (reservar) no conoce Selenium: habla con un objeto "pagina":

    abrir()                 -> bool    carga la pagina y espera la tabla (motivo si falla)
    filas()                 -> list    [{categoria, tarifa, nombre, opciones, agotada}]
    fijar_cantidad(nombre, n) -> int   cantidad que quedo marcada en ese selector
    anadir()                -> (bool, str)   "Anadir al carrito" y su resultado
    detenida                -> bool    la pagina ya no es la de seleccion: no insistir
"""
import re
import time
from dataclasses import dataclass, field

from reserva_ticketmaster import _normalizar

ESPERA_PASO = 15               # Segundos maximos esperando la tabla de localidades
ESPERA_COMPRA = 30             # Segundos para la respuesta de "Anadir al carrito"
ESPERA_VERIFICACION = 180      # Segundos esperando a que la persona pase la verificacion de DataDome
TIEMPO_MAXIMO_RESERVA = 300    # Segundos para todo el intento

# Tarifas que piden algo que el comprador quiza no tiene (convenio, socio, edad...). Se
# prefiere la primera que no lo sea; si todas lo son, la primera.
RE_TARIFA_RESTRINGIDA = re.compile(
    r"descuento|compensar|convenio|afiliad|colsubsidio|cafam|comfama|socio|abonad|"
    r"ni[nñ]o|menor|cortes[ií]a|estudiante|adulto mayor|discapacidad|movilidad|promoc", re.I)


@dataclass
class Reserva:
    ok: bool
    sector: str = ""
    tarifa: str = ""
    cantidad: int = 0          # boletas en el carrito (todas las tandas)
    pedidas: int = 0           # la primera cantidad probada o, con `total`, el total buscado
    detalle: str = ""
    intentos: list = field(default_factory=list)   # ['OCCIDENTAL: 10 rechazada(s) [...]', ...]
    conservar_pestana: bool = False   # no cerrarla (fila de Queue-it o pagina desconocida)
    sin_disponibles: bool = False     # no habia nada que reservar: no merece un Telegram
    tandas: list = field(default_factory=list)     # [(localidad, tarifa, n), ...] que entraron
    tope_compra: int = 0       # "el numero maximo permitido es N" de Tuboleta, si salio
    en_cesta: int = None       # boletas en la cesta cuando salio ese tope


# Tope de "Anadir al carrito" rechazados en una reserva: cada uno es un POST y puede traer la
# verificacion de DataDome. Bajar de 10 a 1 en una localidad son 10.
MAX_RECHAZOS = 15
# Rechazo por tope de la compra (no por falta de boletas): bajar de una en una no sirve. El texto
# real de Tuboleta aun no se ha visto; esto es una suposicion.
RE_LIMITE_COMPRA = re.compile(r"l[ií]mite|m[aá]ximo (de|por)|exced", re.I)
# Tope por compra del evento, visto en Hamilton (6-nov-2026, con 10 PLATEA ya en la cesta): "Lo
# sentimos, el numero seleccionado de entradas no puede anadirse a la cesta: el numero maximo
# permitido es 10." Segun Aldemar, en otros eventos es 12, 15 o hasta 50. Cuenta lo que ya hay
# en la cesta: bajar de una en una no sirve; se prueba con lo que falta para el tope o se para.
RE_MAXIMO_PERMITIDO = re.compile(r"m[aá]ximo permitido es (?:de )?(\d+)", re.I)


def _prioridad(nombre, claves):
    texto = _normalizar(nombre)
    for i, clave in enumerate(claves):
        if clave and clave in texto:
            return i
    return None


def ordenar_categorias(filas, sectores=None):
    """
    Localidades con boletas a la venta, por prioridad: el orden de `sectores` (palabras) y,
    a igual prioridad, el de la pagina. Sin `sectores`, todas en el orden de la pagina.
    """
    vistas = []
    for f in filas:
        if not f.get("agotada") and f.get("opciones") and f["categoria"] not in vistas:
            vistas.append(f["categoria"])
    if not sectores:
        return vistas
    claves = [_normalizar(s) for s in sectores if _normalizar(s)]
    con_prioridad = [(_prioridad(c, claves), i, c) for i, c in enumerate(vistas)]
    return [c for p, _, c in sorted(t for t in con_prioridad if t[0] is not None)]


def elegir_fila(filas, categoria):
    """Fila (tarifa) de la localidad a usar: la primera sin restriccion, o la primera."""
    candidatas = [f for f in filas if f["categoria"] == categoria and not f.get("agotada") and f.get("opciones")]
    for f in candidatas:
        if not RE_TARIFA_RESTRINGIDA.search(f.get("tarifa") or ""):
            return f
    return candidatas[0] if candidatas else None


def _rechazos(intentos):
    return sum(1 for i in intentos if "rechazada" in i)


def _reservar_categoria(pagina, categoria, techo, intentos, limite, reloj, compra=None):
    """
    Una tanda en una localidad: la mayor cantidad que deje (como mucho `techo`), bajando de una
    en una si la rechaza. Devuelve (Reserva o None, parar_todo). En `compra` se apunta el tope
    por compra del evento si Tuboleta lo dice.
    """
    compra = {} if compra is None else compra
    pedidas = 0
    while True:
        if reloj() > limite:
            intentos.append(f"{categoria}: se acabo el tiempo")
            return None, True
        if _rechazos(intentos) >= MAX_RECHAZOS:
            intentos.append(f"{categoria}: demasiados rechazos ({MAX_RECHAZOS}); no se insiste")
            return None, True
        fila = elegir_fila(pagina.filas(), categoria)
        if fila is None:
            intentos.append(f"{categoria}: ya no aparece a la venta")
            return None, False
        opciones = [o for o in fila["opciones"] if techo is None or o <= techo]
        if not opciones:
            return None, False
        n = max(opciones)
        pedidas = pedidas or n
        marcadas = pagina.fijar_cantidad(fila["nombre"], n)
        if marcadas != n:
            intentos.append(f"{categoria}: no se pudo marcar {n} (quedo {marcadas})")
            return None, False
        ok, nota = pagina.anadir()
        if ok:
            intentos.append(f"{categoria}: {n} ok")
            return Reserva(True, categoria, fila.get("tarifa", ""), n, pedidas, detalle=nota, intentos=intentos,
                           conservar_pestana=True, tandas=[(categoria, fila.get("tarifa", ""), n)]), False
        intentos.append(f"{categoria}: {n} rechazada(s) [{nota}]")
        if getattr(pagina, "detenida", False):
            return None, True
        tope = RE_MAXIMO_PERMITIDO.search(nota or "")
        if tope:
            compra["tope"] = int(tope.group(1))
            compra["cesta"] = pagina.en_cesta() if hasattr(pagina, "en_cesta") else None
            cabe = compra["tope"] - compra["cesta"] if compra["cesta"] is not None else 0
            if 0 < cabe < n:
                intentos.append(f"{categoria}: tope de {compra['tope']} por compra y la cesta tiene "
                                f"{compra['cesta']}; pruebo con {cabe}")
                techo = cabe
                continue
            return None, True
        if RE_LIMITE_COMPRA.search(nota or ""):
            return None, True
        # No se sabe cuantas quedan hasta que la pagina acepta: una menos y otra vez, como
        # pidio Aldemar ("si no hay esa cantidad, elige las que puedas").
        techo = n - 1


def _sumar(total, parte):
    if total is None:
        return parte
    total.cantidad += parte.cantidad
    total.tandas += parte.tandas
    total.detalle = parte.detalle
    return total


def _resumen(tandas):
    """[(PLATEA, t, 10), (PLATEA, t, 10)] -> 'PLATEA x20', agrupado por localidad y en orden."""
    suma = {}
    for categoria, _, n in tandas:
        suma[categoria] = suma.get(categoria, 0) + n
    return " + ".join(f"{c} x{n}" for c, n in suma.items())


def reservar(pagina, sectores=None, maximo=None, reloj=time.time, total=None):
    """
    Anade al carrito la mayor cantidad posible, por localidades en orden de prioridad.

    `sectores` (opcional) son palabras; su orden es la prioridad. Sin ellas vale cualquier
    localidad a la venta. `maximo` (opcional) limita cada tanda; sin el, la mayor que ofrezca
    el selector (6-10 en Tuboleta).
      - Sin `total`: una sola tanda, en la primera localidad que se deje.
      - Con `total`: sigue anadiendo hasta llegar a `total` boletas. Repite la MISMA localidad
        mientras acepte (PLATEA primero, como pidio Aldemar el 6-nov-2026) y solo cuando la
        rechaza pasa a la siguiente.
    """
    limite = reloj() + TIEMPO_MAXIMO_RESERVA
    if not pagina.abrir():
        motivo = getattr(pagina, "motivo", "")
        return Reserva(False, detalle="no se pudo abrir la seleccion de boletas" + (f": {motivo}" if motivo else ""),
                       conservar_pestana=bool(getattr(pagina, "conservar_pestana", False)))
    filas = pagina.filas()
    categorias = ordenar_categorias(filas, sectores)
    if not categorias:
        a_la_venta = ordenar_categorias(filas)
        if a_la_venta:
            detalle = f"ninguna localidad a la venta coincide con {', '.join(sectores)}: {', '.join(a_la_venta)}"
        else:
            detalle = "no hay localidades a la venta en la pagina"
        return Reserva(False, detalle=detalle, sin_disponibles=True)
    intentos = []
    conseguido = None
    parar = False
    compra = {}
    for categoria in categorias:
        while not parar:
            falta = None if total is None else total - (conseguido.cantidad if conseguido else 0)
            if falta is not None and falta <= 0:
                parar = True
                break
            techo = falta if maximo is None else (maximo if falta is None else min(maximo, falta))
            if conseguido and not pagina.volver():
                intentos.append(f"{categoria}: no se pudo volver a la tabla para otra tanda")
                parar = True
                break
            parte, parar = _reservar_categoria(pagina, categoria, techo, intentos, limite, reloj, compra)
            if not parte:
                break
            conseguido = _sumar(conseguido, parte)
            if compra.get("tope"):
                # Ya se sabe el tope por compra: con la cesta llena, otra tanda es otro rechazo.
                compra["cesta"] = pagina.en_cesta() if hasattr(pagina, "en_cesta") else None
                if compra["cesta"] is None or compra["cesta"] >= compra["tope"]:
                    parar = True
                    break
            if total is None:
                parar = True
            elif parte.cantidad < parte.pedidas:
                # Tuvo que bajar para entrar: ya no quedan mas aqui. Repetirla seria otra
                # bajada entera de rechazos (y de POST) para nada.
                break
        if parar:
            break
    if conseguido:
        conseguido.intentos = intentos
        if len(conseguido.tandas) > 1:
            conseguido.sector = _resumen(conseguido.tandas)
        conseguido.tarifa = " / ".join(dict.fromkeys(t for _, t, _ in conseguido.tandas if t))
        if total is not None:
            conseguido.pedidas = total
        conseguido.tope_compra, conseguido.en_cesta = compra.get("tope", 0), compra.get("cesta")
        return conseguido
    if compra.get("tope"):
        en_cesta = compra.get("cesta")
        return Reserva(False, intentos=intentos, tope_compra=compra["tope"], en_cesta=en_cesta,
                       detalle=(f"Tuboleta permite maximo {compra['tope']} boletas por compra en este evento"
                               + (f" y la cesta ya tiene {en_cesta}" if en_cesta is not None else "")))
    detenida = getattr(pagina, "detenida", False)
    return Reserva(False, intentos=intentos, conservar_pestana=bool(getattr(pagina, "conservar_pestana", False)),
                   detalle=(getattr(pagina, "motivo", "") or "la pagina dejo de mostrar la seleccion") if detenida
                   else "ninguna localidad se dejo anadir al carrito")


def mensaje(reserva, evento, url, hora):
    """Texto del resultado, para la consola o Telegram."""
    if reserva.ok:
        texto = f"🎟️ TUBOLETA: EN EL CARRITO - ENTRA A PAGAR\n\n📌 {evento}\n"
        tandas = reserva.tandas or [(reserva.sector, reserva.tarifa, reserva.cantidad)]
        for categoria, tarifa, n in tandas:
            texto += f"  • {n} x {categoria}" + (f" ({tarifa})" if tarifa else "") + "\n"
        if len(tandas) > 1:
            texto += f"  • Total: {reserva.cantidad} boletas\n"
        if reserva.cantidad < reserva.pedidas:
            texto += f"  • Solo se pudieron {reserva.cantidad} de {reserva.pedidas}\n"
        if reserva.tope_compra:
            texto += f"  • Tuboleta permite máximo {reserva.tope_compra} por compra en este evento\n"
        if reserva.detalle:
            texto += f"  • {reserva.detalle}\n"
        return (texto + "\nLa pestaña sigue abierta en el navegador de reserva: abre\n"
                f"'Mi cesta' y paga ahí (el carrito vence solo).\n🔗 {url}\n\n⏰ {hora}")
    texto = f"⚠️ TUBOLETA: NO PUDE AÑADIR AL CARRITO\n\n📌 {evento}\nMotivo: {reserva.detalle}\n"
    if reserva.intentos:
        texto += "Intentos:\n" + "".join(f"  • {i}\n" for i in reserva.intentos[:12])
    if reserva.conservar_pestana:
        texto += "La pestaña queda abierta en el navegador de reserva.\n"
    return texto + f"🔗 {url}\n\n⏰ {hora}"


def url_con_tabla(url):
    """La pagina de asientos con la tabla "Mejor sitio" (table=1) en vez del plano."""
    if "/selection/event/seat" in url and not re.search(r"[?&]table=1(&|$)", url):
        return url + ("&" if "?" in url else "?") + "table=1"
    return url


# ----------------------------------------------------------------------------
# Pagina real (Selenium)
# ----------------------------------------------------------------------------

_JS_VISIBLE = "var vis=function(e){return !!(e && e.getClientRects().length);};"

JS_TABLA = "return !!document.querySelector('#event_form .table_container tbody tr');"

# Dos formas de "Agotado" vistas: `.sold_out_text` con "lista de espera" (Reykon) y una capa
# `.category_unavailable_overlay` encima de la fila (Hamilton, 6-nov-2026). Ninguna es parte
# del nombre, y una fila con la capa a la vista no se cuenta aunque tenga selector.
JS_FILAS = _JS_VISIBLE + r"""
var filas = [], cat = '';
var trs = document.querySelectorAll('#event_form .table_container tbody tr');
for (var i = 0; i < trs.length; i++) {
    var tr = trs[i], th = tr.querySelector('th.category');
    if (th) {
        var c = th.cloneNode(true);
        c.querySelectorAll('.sold_out_text, .button, .category_unavailable_overlay, script')
            .forEach(function (e) { e.remove(); });
        cat = c.textContent.replace(/\s+/g, ' ').replace(/[\s\-–]+$/, '').trim();
    }
    var capa = tr.querySelector('.category_unavailable_overlay');
    var sel = tr.querySelector('td.quantity select[name$=".quantity"]');
    if (!sel) {
        if (th && cat) filas.push({categoria: cat, tarifa: '', nombre: '', opciones: [], agotada: true});
        continue;
    }
    var ops = [].map.call(sel.options, function (o) { return parseInt(o.value, 10); })
        .filter(function (n) { return n > 0; });
    var t = tr.querySelector('.audience-subcat-name');
    filas.push({categoria: cat, tarifa: t ? t.textContent.replace(/\s+/g, ' ').trim() : '',
                nombre: sel.name, opciones: ops, agotada: sel.disabled || !ops.length || vis(capa)});
}
return filas;
"""

# Una pagina de fechas (selection/event/date) con una sola funcion muestra el plano y enlaza la
# tabla en "Mejor sitio": /selection/event/seat?perfId=...&table=1 (Hamilton, 6-nov-2026).
JS_ENLACE_TABLA = """
var a = document.querySelector('a[href*="/selection/event/seat"][href*="table=1"]');
return a ? a.href : null;
"""

JS_CESTA = r"""
var a = document.querySelector('#account_cart'), b = document.querySelector('#account_cart_button');
var m = /(\d+)\s*product/i.exec((a && a.getAttribute('aria-label')) || '');
if (m) return parseInt(m[1], 10);
if (b && /empty_cart/.test(b.className)) return 0;
return null;
"""

JS_AVISOS = _JS_VISIBLE + r"""
var textos = [];
document.querySelectorAll('.main_content_notification, .ui-dialog, [role="dialog"], [role="alertdialog"]').forEach(function (e) {
    if (vis(e)) { var t = e.innerText.replace(/\s+/g, ' ').trim(); if (t && textos.indexOf(t) < 0) textos.push(t); }
});
return textos.join(' | ').slice(0, 400);
"""

# DataDome (js.datadome.co/tags.js en todas las paginas de Tuboleta, con
# "replayAfterChallenge": true). Su verificacion es un iframe de captcha-delivery.com, a
# pagina completa tras el POST de "Anadir al carrito" (6-nov-2026, Hamilton, en el Comet de
# reserva) o como capa encima. Lo que se ve dentro del iframe no se ha leido.
JS_VERIFICACION = _JS_VISIBLE + r"""
var f = document.querySelector('iframe[src*="captcha-delivery.com"], iframe[src*="datadome"]');
if (vis(f)) return true;
if (window.dd && /captcha-delivery/.test(String(window.dd.host || ''))) return true;
var h = document.documentElement ? document.documentElement.innerHTML.slice(0, 20000) : '';
return !document.querySelector('#event_form') && /captcha-delivery\.com/.test(h);
"""

JS_ESTADO_ENVIO = """
return {marca: !!window.__reservaTuboleta, listo: document.readyState, url: location.href};
"""

JS_BOTON_ANADIR = _JS_VISIBLE + """
var b = document.querySelector('#event_form a#book') || document.querySelector('a#book');
return vis(b) ? b : null;
"""


class PaginaSelenium:
    """Pagina real sobre un driver de Selenium, en la pestana que este activa."""

    def __init__(self, driver, url, cargar, al_verificar=None):
        self.driver = driver
        self.url = url_con_tabla(url)
        self.cargar = cargar   # navegar() del monitor: respeta el limite de carga
        # Se llama en cuanto DataDome pide la verificacion (el monitor manda un Telegram):
        # el resultado final de la reserva llega despues, cuando ya puede ser tarde.
        self.al_verificar = al_verificar
        self.url_tabla = ""   # la de "Mejor sitio" cuando se entra por la de fechas
        self.motivo = ""
        self.detenida = False
        self.conservar_pestana = False

    def _js(self, script, *args):
        try:
            return self.driver.execute_script(script, *args)
        except Exception:
            return None

    def _esperar(self, condicion, segundos):
        limite = time.time() + segundos
        while True:
            valor = condicion()
            if valor:
                return valor
            if time.time() >= limite:
                return None
            time.sleep(0.4)

    def _url(self):
        try:
            return self.driver.current_url or ""
        except Exception:
            return ""

    def _en_fila(self):
        return "queue-it" in self._url()

    def abrir(self):
        self.motivo, self.detenida, self.conservar_pestana = "", False, False
        self.cargar(self.driver, self.url)
        if self._en_verificacion() and not self._esperar_verificacion():
            return False
        if "/selection/event/date" in self.url and not self._en_fila():
            # Una carga mas, solo al reservar: de la pagina de fechas a su tabla "Mejor sitio".
            enlace = self._esperar(lambda: self._js(JS_TABLA) or self._js(JS_ENLACE_TABLA), ESPERA_PASO)
            if isinstance(enlace, str):
                self.url_tabla = enlace
                self.cargar(self.driver, enlace)
        if self._esperar(lambda: self._en_fila() or self._js(JS_TABLA), ESPERA_PASO) and not self._en_fila():
            return True
        if self._en_fila():
            # Cerrar la pestana perderia el puesto en la fila.
            self.conservar_pestana = True
            self.motivo = "Tuboleta tiene fila de espera (Queue-it); la pestaña queda abierta en la fila"
        else:
            self.motivo = f"la tabla de localidades no aparecio en {ESPERA_PASO}s ({self._url()})"
        return False

    def volver(self):
        """
        Tras una tanda que entro, de vuelta a la tabla para la siguiente. Si la respuesta ya es
        la tabla (con la cesta al dia) no se carga nada; si no, una carga mas de la pagina.
        """
        if self._js(JS_TABLA) and "/selection/event/seat" in self._url():
            return True
        self.cargar(self.driver, self.url_tabla or self.url)
        if self._en_verificacion() and not self._esperar_verificacion():
            return False
        return bool(self._esperar(lambda: self._js(JS_TABLA), ESPERA_PASO))

    def filas(self):
        return self._js(JS_FILAS) or []

    def fijar_cantidad(self, nombre, n):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select
        try:
            for el in self.driver.find_elements(By.CSS_SELECTOR, 'td.quantity select[name$=".quantity"]'):
                lista = Select(el)
                nombre_el = el.get_attribute("name")
                if nombre_el == nombre:
                    lista.select_by_value(str(n))
                elif lista.first_selected_option.get_attribute("value") not in ("", "0"):
                    lista.select_by_value("0")   # lo marcado en otra localidad iria en el mismo pedido
            el = self.driver.find_element(By.NAME, nombre)
            return int(Select(el).first_selected_option.get_attribute("value") or 0)
        except Exception:
            return 0

    def en_cesta(self):
        return self._cesta()

    def _cesta(self):
        return self._js(JS_CESTA)

    def anadir(self):
        antes = self._cesta()
        previo = self._js(JS_AVISOS) or ""
        boton = self._js(JS_BOTON_ANADIR)
        if not boton:
            return False, "el boton 'Añadir al carrito' no esta a la vista"
        # Marca en la pagina actual: si desaparece, el navegador ya cargo la respuesta.
        self._js("window.__reservaTuboleta = 1;")
        try:
            try:
                boton.click()
            except Exception as e:
                if type(e).__name__ == "StaleElementReferenceException":
                    raise
                self.driver.execute_script("arguments[0].click();", boton)
        except Exception as e:
            return False, f"no se pudo pulsar 'Añadir al carrito' ({type(e).__name__})"

        def respuesta():
            estado = self._js(JS_ESTADO_ENVIO)
            if not estado:
                return None                        # cargando
            if not estado.get("marca"):
                return "pagina" if estado.get("listo") != "loading" else None
            if self._en_verificacion():
                return "verificacion"              # DataDome tambien puede salir encima de la pagina
            cesta = self._cesta()
            if antes is not None and cesta is not None and cesta > antes:
                return "cesta"                     # sin recargar (por si el envio es AJAX)
            aviso = self._js(JS_AVISOS) or ""
            return "aviso" if aviso and aviso != previo else None

        que = self._esperar(respuesta, ESPERA_COMPRA)
        if que is None:
            self.detenida = True
            self.conservar_pestana = True
            self.motivo = f"sin respuesta de 'Añadir al carrito' en {ESPERA_COMPRA}s"
            return False, self.motivo
        if que == "pagina":
            # Que termine de pintar la cesta antes de leerla.
            self._esperar(lambda: self._js("return document.readyState === 'complete' || null;"), 5)
        if self._en_verificacion():
            if not self._esperar_verificacion():
                return False, self.motivo
            self._esperar(lambda: self._js("return document.readyState === 'complete' || null;"), 5)
        return self._evaluar(antes)

    # -- verificacion anti-robot (DataDome) -----------------------------------------------

    def _en_verificacion(self):
        """Pagina o capa de DataDome ("verifica que no eres un robot")."""
        return bool(self._js(JS_VERIFICACION))

    def _esperar_verificacion(self):
        """
        DataDome pidio la verificacion: la pestana se trae al frente, se avisa YA (al_verificar,
        el Telegram del monitor) y se espera a que la persona la pase. El bot no la toca. Con
        `replayAfterChallenge` la pagina repite sola el envio al pasarla. True si paso.
        """
        self.conservar_pestana = True
        try:
            self.driver.execute_cdp_cmd("Page.bringToFront", {})
        except Exception:
            pass
        if self.al_verificar:
            try:
                self.al_verificar()
            except Exception:
                pass
        if self._esperar(lambda: not self._en_verificacion(), ESPERA_VERIFICACION):
            return True
        self.detenida = True
        self.motivo = (f"Tuboleta (DataDome) pidio verificar que no eres un robot y no se resolvio en "
                       f"{ESPERA_VERIFICACION}s. La pestaña sigue abierta en el navegador de reserva: si "
                       "la pasas, la pagina repite el pedido sola; revisa 'Mi cesta'")
        return False

    def _evaluar(self, antes):
        """Resultado de un envio ya respondido: (ok, nota)."""
        cesta = self._cesta()
        url = self._url()
        if antes is not None and cesta is not None and cesta > antes:
            return True, f"la cesta tiene {cesta} producto(s)"
        if self._en_fila():
            self.detenida, self.conservar_pestana = True, True
            self.motivo = "Tuboleta mando a la fila de espera (Queue-it) al añadir; la pestaña queda abierta"
            return False, self.motivo
        if "/selection/event/seat" in url or "/selection/event/submit" in url:
            if self._js(JS_TABLA):
                return False, self._js(JS_AVISOS) or "rechazada sin mensaje"
            # Pagina desconocida: no se cierra, puede tener el pedido a medias (asi se perdio la
            # verificacion de DataDome el 6-nov-2026, antes de reconocerla).
            self.detenida, self.conservar_pestana = True, True
            self.motivo = "tras añadir, la pagina ya no muestra la tabla de localidades; la pestaña queda abierta"
            return False, self.motivo
        if re.search(r"login|signin|identif", url, re.I):
            self.detenida, self.conservar_pestana = True, True
            self.motivo = "Tuboleta pide iniciar sesion en el navegador de reserva"
            return False, self.motivo
        # Otra pantalla (cesta, extras...). No se pudo leer la cesta pero lo normal es que
        # el pedido haya entrado: se avisa como exito con la pestana abierta para revisarlo.
        return True, f"la pagina paso a {url}; no pude leer la cesta, revisala en la pestaña"
