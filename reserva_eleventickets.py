"""
Reserva de entradas en Eleventickets (Final CONMEBOL Sudamericana) hasta el carrito.

El bot elige el sector en el mapa, marca hasta `maximo` entradas, pulsa "Anadir al
Carrito de Compras" y SE DETIENE: no entra al carrito ni al pago. El usuario paga
desde "Carrito de Compras" en la pestana que queda abierta.

Lo que se sabe de la pagina (leido en el Comet de reserva, 28-oct-2026, con la venta
aun cerrada: "VENTA DE ENTRADAS EN BREVE"):
  - Es AngularJS + Leaflet. Cada sector es una capa SVG del mapa con sus datos en
    `capa.dados`: nombre en `dscbloco` ("CAT2 - Oriental Tribuna Media - Sector 7"),
    `disabled` (1 = no se puede pulsar) y `m` (tipo de bloque).
  - CAT2 - Oriental son 41 bloques: Tribuna Alta/Media/Baja, Sector 1..15.
  - m >= 2: al pulsar el bloque aparece la lista de productos; la cantidad se sube con
    `button.botao-soma` ("+"), que se deshabilita en el tope (`limite_prod`), y luego
    "Anadir al Carrito de Compras" (`button.botao-avancar`). Es el flujo que conoce
    Aldemar. Sin reCAPTCHA: es un POST a tickets/booking.
  - m == 1 (asientos numerados): al pulsar el bloque y acercar el mapa se cargan los
    asientos; cada asiento abre su producto y su "+" lo reserva de inmediato, UNA entrada
    por asiento. Hoy los 90 bloques vienen con m = "1" y disabled = 1; puede cambiar al
    abrir la venta.
  - Reserva hecha: `$rootScope.qtdReserva` sube en la cantidad reservada. Error: dialogo
    `md-dialog` (Modal.error) o aviso `md-toast` con el texto.
  - Maximo 4 entradas por comprador (preguntas frecuentes del evento).

NADA de lo anterior se ha ejecutado aun con la venta abierta: ni el "+", ni "Anadir al
Carrito", ni los asientos. Esta escrito contra el codigo de la pagina (app.js y la
plantilla Siwprodutoslistagem), no contra una reserva real.

La logica (reservar) no conoce Selenium: habla con un objeto "pagina" con estos metodos:

    abrir()                 -> bool    carga el evento y espera el mapa (motivo si falla)
    bloques()               -> list    [{nombre, libre, numerado}]
    elegir_bloque(nombre)   -> bool    pulsa el bloque y espera productos o asientos
    productos()             -> list    [{nombre, agotado}] del bloque elegido
    fijar_cantidad(i, n)    -> int     cantidad que quedo marcada en el producto i
    anadir()                -> (bool, str)   "Anadir al Carrito" y su resultado
    asientos_libres()       -> list    [{id, fila, lugar}] del bloque elegido
    reservar_asiento(id)    -> (bool, str)
"""
import re
import time
from dataclasses import dataclass, field

from reserva_ticketmaster import _normalizar

MAXIMO_POR_COMPRADOR = 4       # Tope del evento por comprador
ESPERA_PASO = 15               # Segundos maximos esperando una pantalla nueva
ESPERA_RESPUESTA = 8           # Segundos antes de dar un clic por perdido
ESPERA_COMPRA = 60             # Segundos para la respuesta de "Anadir" (incluye la prueba de trabajo)
ESPERA_VERIFICACION = 45       # Segundos dejando que la verificacion de Cloudflare pase sola
TIEMPO_MAXIMO_RESERVA = 300    # Segundos para todo el intento

# Rechazo por falta de cupo: se reintenta en el mismo bloque con menos entradas. El texto real
# es "¡El producto está agotado!"; lo demas cubre variantes que aun no se han visto.
RE_LIMITE_CUENTA = re.compile(r"excedido el n.mero l.mite de entradas", re.I)
RE_SIN_CUPO = re.compile(r"agotad|no hay|sin disponib|no (esta|está) disponible|insuficiente|esgotad", re.I)


@dataclass
class Reserva:
    ok: bool
    sector: str = ""
    producto: str = ""
    cantidad: int = 0      # entradas reservadas
    pedidas: int = 0       # entradas que se querian
    asientos: list = field(default_factory=list)   # ['Fila C 12', ...] en bloques numerados
    detalle: str = ""
    intentos: list = field(default_factory=list)   # ['CAT2 - ... Sector 3: agotado', ...]
    conservar_pestana: bool = False   # no cerrarla: espera al usuario (verificacion de Cloudflare)
    completo: bool = False            # el carrito ya tiene el tope: no hay nada mas que intentar


def _prioridad(nombre, claves):
    """Posicion de la primera clave contenida en el nombre, o None si ninguna."""
    texto = _normalizar(nombre)
    for i, clave in enumerate(claves):
        if clave and clave in texto:
            return i
    return None


def ordenar_bloques(bloques, sectores):
    """
    Bloques que coinciden con `sectores`, por prioridad (el orden de `sectores`) y luego
    en el orden del mapa. Devuelve (libres, coinciden): coinciden incluye los no pulsables.
    """
    claves = [_normalizar(s) for s in sectores]
    coinciden = []
    for orden, b in enumerate(bloques):
        p = _prioridad(b["nombre"], claves)
        if p is not None:
            coinciden.append((p, orden, b))
    coinciden.sort(key=lambda t: (t[0], t[1]))
    todos = [b for _, _, b in coinciden]
    return [b for b in todos if b["libre"]], todos


def _numero(texto):
    m = re.search(r"\d+", str(texto))
    return int(m.group()) if m else None


def elegir_juntos(asientos, n):
    """
    Hasta n asientos, preferiblemente seguidos en la misma fila.

    Primero busca n numeros consecutivos en una fila; si no hay, la tanda seguida mas
    larga; y si los numeros no se pueden leer, los primeros n tal cual.
    """
    if n <= 0 or not asientos:
        return []
    filas = {}
    for a in asientos:
        filas.setdefault(str(a.get("fila", "")), []).append(a)
    mejor = []
    for fila in filas.values():
        con_numero = sorted((a for a in fila if _numero(a.get("lugar")) is not None),
                            key=lambda a: _numero(a["lugar"]))
        tanda = []
        for a in con_numero:
            if tanda and _numero(a["lugar"]) != _numero(tanda[-1]["lugar"]) + 1:
                tanda = []
            tanda.append(a)
            if len(tanda) >= n:
                return tanda[-n:]
            if len(tanda) > len(mejor):
                mejor = list(tanda)
    # Sin n seguidos: la tanda mas larga y, para completar, los sueltos que haya. Aldemar lo pidio
    # asi el 30-oct-2026, con Occidental libre de a 1: mejor separados que menos de 4.
    elegidos = mejor[:n]
    for a in asientos:
        if len(elegidos) >= n:
            break
        if a not in elegidos:
            elegidos.append(a)
    return elegidos


def _etiqueta(asiento):
    fila = asiento.get("fila") or ""
    return (f"Fila {fila} " if fila else "") + str(asiento.get("lugar") or asiento.get("id"))


def _reservar_cantidad(pagina, bloque, maximo, producto, intentos):
    productos = pagina.productos()
    claves = [_normalizar(producto)] if producto else []
    elegido = None
    for i, p in enumerate(productos):
        if p.get("agotado"):
            continue
        if claves and _prioridad(p["nombre"], claves) is None:
            continue
        elegido = i
        break
    if elegido is None:
        vistos = ", ".join(f"{p['nombre']}{' (agotado)' if p.get('agotado') else ''}" for p in productos)
        intentos.append(f"{bloque}: sin producto disponible [{vistos or 'lista vacia'}]")
        return None
    nombre = productos[elegido]["nombre"]
    n = maximo
    while n >= 1:
        marcadas = pagina.fijar_cantidad(elegido, n)
        if marcadas <= 0:
            intentos.append(f"{bloque}: el '+' no marco ninguna")
            return None
        ok, nota = pagina.anadir()
        if ok:
            intentos.append(f"{bloque}: {marcadas} ok")
            return Reserva(True, bloque, nombre, marcadas, maximo, detalle=nota, intentos=intentos)
        intentos.append(f"{bloque}: {marcadas} rechazada(s) [{nota}]")
        # El "+" deja subir a 4 aunque queden menos: el cupo real solo se sabe al anadir, y
        # el servidor contesta "El producto esta agotado!" (visto por Aldemar, 28-oct-2026,
        # pidiendo 2). Se repite en el mismo bloque con una menos. Sin respuesta o con la
        # pagina recargada (fila) no tiene sentido insistir.
        if not RE_SIN_CUPO.search(nota or ""):
            return None
        n = marcadas - 1
    return None


def _reservar_asientos(pagina, bloque, maximo, limite, reloj, intentos):
    libres = pagina.asientos_libres()
    if not libres:
        intentos.append(f"{bloque}: sin asientos libres")
        return None
    hechos, notas = [], []
    for asiento in elegir_juntos(libres, maximo):
        if reloj() > limite:
            break
        ok, nota = pagina.reservar_asiento(asiento["id"])
        if ok:
            hechos.append(_etiqueta(asiento))
        else:
            notas.append(f"{_etiqueta(asiento)}: {nota}")
    intentos.append(f"{bloque}: {len(hechos)} de {maximo} asiento(s)" + (f" [{'; '.join(notas)}]" if notas else ""))
    if not hechos:
        return None
    return Reserva(True, bloque, "", len(hechos), maximo, asientos=hechos,
                   detalle="; ".join(notas), intentos=intentos)


def _sumar(total, parte):
    """Acumula una reserva parcial de otro bloque en la Reserva total."""
    if total is None:
        return parte
    total.sector += " + " + parte.sector
    total.cantidad += parte.cantidad
    total.asientos += parte.asientos
    if parte.producto and parte.producto not in total.producto:
        total.producto = f"{total.producto} + {parte.producto}" if total.producto else parte.producto
    return total


def reservar(pagina, sectores, maximo=MAXIMO_POR_COMPRADOR, producto="", reloj=time.time, tope=None):
    """
    Reserva hasta `maximo` entradas en el primer bloque de `sectores` que se deje.

    `sectores` son palabras ("CAT2 - Oriental"); su orden es la prioridad. Un bloque sin
    entradas pasa al siguiente. Se para en cuanto uno reserva al menos una entrada: el
    evento no deja mas de 4 por comprador, asi que no se reparten entre bloques.
    `producto` (opcional) filtra el producto del bloque por nombre.

    Con `tope` (modo completar): se descuenta lo que el servidor ya tiene en el carrito y, si un
    bloque da menos de lo que falta, se sigue con los siguientes hasta completar. Las entradas
    pueden quedar en sectores distintos.
    """
    limite = reloj() + TIEMPO_MAXIMO_RESERVA
    if not pagina.abrir():
        motivo = getattr(pagina, "motivo", "")
        return Reserva(False, pedidas=maximo,
                       detalle="no se pudo abrir el mapa del evento" + (f": {motivo}" if motivo else ""),
                       conservar_pestana=bool(getattr(pagina, "conservar_pestana", False)))
    if tope:
        en_carrito = pagina.en_carrito() if hasattr(pagina, "en_carrito") else None
        if en_carrito is not None:
            maximo = min(maximo, tope - en_carrito)
            if maximo <= 0:
                return Reserva(False, pedidas=0, completo=True,
                               detalle=f"el carrito ya tiene {en_carrito} entrada(s), el tope es {tope}")
    libres, coinciden = ordenar_bloques(pagina.bloques(), sectores)
    if not coinciden:
        return Reserva(False, pedidas=maximo,
                       detalle=f"ningun sector del mapa coincide con {', '.join(sectores)}")
    if not libres:
        return Reserva(False, pedidas=maximo,
                       detalle=f"los {len(coinciden)} sectores de {', '.join(sectores)} estan "
                               "deshabilitados en el mapa (venta cerrada o agotados)")
    intentos = []
    total = None
    pedidas = maximo
    for bloque in libres:
        if reloj() > limite:
            intentos.append("se acabo el tiempo")
            break
        if not pagina.elegir_bloque(bloque["nombre"]):
            intentos.append(f"{bloque['nombre']}: no se abrio")
            continue
        if bloque.get("numerado"):
            resultado = _reservar_asientos(pagina, bloque["nombre"], maximo, limite, reloj, intentos)
        else:
            resultado = _reservar_cantidad(pagina, bloque["nombre"], maximo, producto, intentos)
        # La cuenta ya llego al tope, contando lo PAGADO, que no sale en el carrito (30-oct-2026, con
        # 4 CAT2 pagadas y carrito en 0). Ningun otro bloque va a dejar: se para.
        if intentos and RE_LIMITE_CUENTA.search(intentos[-1]):
            if total:
                total.pedidas, total.intentos = pedidas, intentos
                return total
            return Reserva(False, pedidas=pedidas, completo=True, intentos=intentos,
                           detalle="esta cuenta ya llego al limite de entradas por persona")
        if resultado:
            if not tope:
                return resultado
            total = _sumar(total, resultado)
            maximo = pedidas - total.cantidad
            if maximo <= 0:
                break
    if total:
        total.pedidas, total.intentos = pedidas, intentos
        return total
    return Reserva(False, pedidas=maximo, intentos=intentos,
                   detalle=f"ningun sector de {', '.join(sectores)} se dejo reservar")


def mensaje(reserva, evento, url, hora):
    """Texto del resultado, para la consola o Telegram."""
    if reserva.ok:
        texto = (f"🎟️ EN EL CARRITO - ENTRA A PAGAR\n\n📌 {evento}\n"
                 f"  • {reserva.cantidad} x {reserva.sector}" + (f" ({reserva.producto})" if reserva.producto else "") + "\n")
        if reserva.asientos:
            texto += f"  • Asientos: {', '.join(reserva.asientos)}\n"
        if reserva.cantidad < reserva.pedidas:
            texto += f"  • Solo se pudieron {reserva.cantidad} de {reserva.pedidas}\n"
        return (texto + "\nLa pestana sigue abierta en el navegador de reserva: ve a\n"
                f"'Carrito de Compras' y paga.\n🔗 {url}\n\n⏰ {hora}")
    texto = f"⚠️ NO PUDE AÑADIR AL CARRITO\n\n📌 {evento}\nMotivo: {reserva.detalle}\n"
    if reserva.intentos:
        texto += "Intentos:\n" + "".join(f"  • {i}\n" for i in reserva.intentos[:12])
    return texto + f"🔗 {url}\n\n⏰ {hora}"


# ----------------------------------------------------------------------------
# Pagina real (Selenium). Los selectores salen del codigo de la pagina; ver arriba
# que esta verificado y que no.
# ----------------------------------------------------------------------------
_JS_MAPA = ("var M=(window.L&&window.map instanceof L.Map)?window.map:null;"
            "if(!M&&window.L){for(var k in window){try{if(window[k] instanceof L.Map){M=window[k];break;}}catch(e){}}}")
_JS_VISIBLE = ("var vis=function(e){var r=e.getBoundingClientRect();"
               "return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden';};")
_JS_RAIZ = "var R=angular.element(document.body).injector().get('$rootScope');"

JS_ESTADO = _JS_MAPA + """
if (!window.angular || !M) { return null; }
""" + _JS_RAIZ + """
return {usuario: !!R.User, reservas: Number(R.qtdReserva) || 0, pow: !!R.powProcessing};
"""

JS_BLOQUES = _JS_MAPA + """
if (!M) { return null; }
var out = [];
M.eachLayer(function (l) {
    var d = l.dados;
    if (!d || !d.dscbloco || d.idmapa_assento_fis) { return; }
    out.push({nombre: d.dscbloco, libre: String(d.disabled) !== '1' && d.disabled !== true,
              numerado: String(d.m) === '1'});
});
return out;
"""

# Clic de Leaflet sobre la capa: el centro del recuadro de un poligono irregular puede caer
# fuera de el, y un clic nativo ahi pulsaria el bloque vecino. fire('click') llama al mismo
# manejador de la pagina, que ya comprueba si el bloque esta deshabilitado.
JS_PULSAR_BLOQUE = _JS_MAPA + """
var nombre = arguments[0], capa = null;
var mirar = function (l) { if (!capa && l && l.dados && l.dados.dscbloco === nombre && !l.dados.idmapa_assento_fis) { capa = l; } };
M.eachLayer(mirar);
// Al acercarse a un bloque, el mapa quita a sus vecinos de las capas visibles y carga sus asientos:
// el Sector 315 ya no aparecia tras abrir el 313 (30-oct-2026). Esta lista los tiene todos.
(window.g_mapa_groupBlocos || []).forEach(mirar);
if (!capa) { return null; }
// Los productos del bloque anterior quedan marcados: asi no se confunden con los nuevos.
document.querySelectorAll('.ingressos').forEach(function (e) { e.setAttribute('data-bot-visto', '1'); });
var centro = capa.getBounds().getCenter();
capa.fire('click', {latlng: centro, target: capa});
if (String(capa.dados.m) === '1') {
    // Los asientos solo se cargan con zoom suficiente (g_mapa_zoom_cadeira).
    // Sin animacion y sin fitBounds: este aleja el mapa al terminar su animacion, despues de mirar
    // el zoom, y en el segundo bloque de una pagina los asientos ya no cargaban (Sector 315 "no
    // se abrio" en cada pasada, 30-oct-2026, con la pagina recien cargada si abria).
    var zoom = window.g_mapa_zoom_cadeira || 5;
    M.setView(centro, Math.max(zoom, M.getZoom()), {animate: false});
    setTimeout(function () { try { mapaAdicionarAssentos(capa); } catch (e) {} }, 800);
}
return capa.dados.idmapa_bloco_fis;
"""

JS_PRODUCTOS = _JS_VISIBLE + """
return [...document.querySelectorAll('.ingressos:not([data-bot-visto])')].filter(vis).map(function (el) {
    var s = angular.element(el).isolateScope() || angular.element(el).scope() || {};
    var p = s.produto || {};
    return {nombre: p.dscproduto || (el.innerText || '').trim().split('\\n')[0],
            agotado: !!p.esgotado || !!el.querySelector('.ingresso-esgotado'),
            cantidad: Number(p.qtd_select) || 0};
});
"""

# "+" (botao-soma) o "-" (botao-subtracao) del producto i; null si esta deshabilitado.
JS_BOTON_CANTIDAD = _JS_VISIBLE + """
var el = [...document.querySelectorAll('.ingressos:not([data-bot-visto])')].filter(vis)[arguments[0]];
if (!el) { return null; }
var b = el.querySelector(arguments[1]);
if (!b || b.disabled || !vis(b)) { return null; }
return b;
"""

JS_ANADIR = _JS_VISIBLE + """
var b = [...document.querySelectorAll('button.botao-avancar')].filter(function (b) { return vis(b) && !b.disabled; });
return b[0] || null;
"""

# Texto de un dialogo (Modal.error y Modal.dialog son ngDialog: .ngdialog-content) o de un
# aviso flotante (Modal.showToast: md-toast). El primer intento real (28-oct-2026) buscaba
# solo md-dialog y no vio nada en 15 s.
JS_AVISO = _JS_VISIBLE + """
var t = [...document.querySelectorAll('.ngdialog-content, md-dialog, md-toast')].filter(vis)
    .map(function (e) { return (e.innerText || '').trim().replace(/\\s+/g, ' '); }).filter(Boolean);
return t.join(' / ').slice(0, 200);
"""

JS_CERRAR_DIALOGO = """
var inj = angular.element(document.body).injector();
try { inj.get('ngDialog').closeAll(); } catch (e) {}
try { inj.get('$mdDialog').cancel(); } catch (e) {}
"""

# Entradas en el carrito segun el servidor: qtdReserva puede no haber cargado aun.
JS_CARRITO = """
var cb = arguments[arguments.length - 1];
try {
    angular.element(document.body).injector().get('Common')
        .ajaxmg('SuperIngressoWeb', 'getCarrinhoQtdReservados', [])
        .then(function (r) { cb(Number(r) || 0); }, function () { cb(null); });
} catch (e) { cb(null); }
"""

JS_ASIENTOS = _JS_MAPA + """
var bloque = arguments[0], out = [];
M.eachLayer(function (l) {
    var d = l.dados;
    if (!d || !d.idmapa_assento_fis || d.idmapa_bloco_fis !== bloque) { return; }
    if (['B', 'R', 'O'].indexOf(d.idstatus) >= 0 || d.proprio || d.bloqueio_equipamento) { return; }
    out.push({id: d.idmapa_assento_fis, fila: d.localizador_fila || '', lugar: d.localizador_lugar || ''});
});
return out;
"""

JS_ASIENTOS_CARGADOS = _JS_MAPA + """
var bloque = arguments[0], hay = false;
M.eachLayer(function (l) { if (l.dados && l.dados.idmapa_assento_fis && l.dados.idmapa_bloco_fis === bloque) { hay = true; } });
return hay;
"""

JS_PULSAR_ASIENTO = _JS_MAPA + """
var id = arguments[0], capa = null;
M.eachLayer(function (l) { if (!capa && l.dados && l.dados.idmapa_assento_fis === id) { capa = l; } });
if (!capa) { return false; }
document.querySelectorAll('.ingressos').forEach(function (e) { e.setAttribute('data-bot-visto', '1'); });
var centro = capa.getLatLng ? capa.getLatLng() : capa.getBounds().getCenter();
capa.fire('click', {latlng: centro, target: capa});
return true;
"""

# "+" del producto de un asiento recien abierto (las listas anteriores quedan marcadas).
JS_SUMAR_ASIENTO = _JS_VISIBLE + """
var el = [...document.querySelectorAll('.ingressos:not([data-bot-visto])')].filter(vis)
    .find(function (e) { var b = e.querySelector('button.botao-soma'); return b && !b.disabled && vis(b); });
return el ? el.querySelector('button.botao-soma') : null;
"""


class PaginaSelenium:
    """Pagina real sobre un driver de Selenium, en la pestana que este activa."""

    def __init__(self, driver, url, cargar, ya_cargada=False):
        self.driver = driver
        self.url = url
        self.cargar = cargar   # navegar() del monitor: respeta el limite de carga
        # La pestana ya tiene el evento (p. ej. la que se dejo en la verificacion de Cloudflare y
        # el usuario ya paso): no se recarga, se reserva sobre lo que hay.
        self.ya_cargada = ya_cargada
        self.motivo = ""
        self.id_bloque = ""
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

    def _clic(self, script, *args):
        """Clic nativo sobre el elemento que devuelve el script; JS si algo lo tapa."""
        for _ in range(3):
            elemento = self._js(script, *args)
            if not elemento:
                return False
            try:
                try:
                    elemento.click()
                except Exception as e:
                    if type(e).__name__ == "StaleElementReferenceException":
                        raise
                    self.driver.execute_script("arguments[0].click();", elemento)
                return True
            except Exception as e:
                if type(e).__name__ != "StaleElementReferenceException":
                    raise
                time.sleep(0.3)
        return False

    def _reservas(self):
        estado = self._js(JS_ESTADO) or {}
        return estado.get("reservas", 0)

    def _resultado(self, antes, previo=""):
        """
        Espera a que suba el contador de reservas o salga un aviso NUEVO (distinto de
        `previo`, el que ya habia antes del clic: un md-toast dura 30 s). (ok, nota).

        La reserva (POST tickets/booking) puede volver con el codigo 1111: la propia pagina
        resuelve entonces una prueba de trabajo ($rootScope.powProcessing) y repite la
        peticion sola. Mientras tanto se sigue esperando, hasta ESPERA_COMPRA. Si la
        respuesta es de fila, la pagina se recarga sola y el estado desaparece.
        """
        def listo():
            estado = self._js(JS_ESTADO)
            if not estado:
                return "recarga"
            if estado.get("reservas", 0) > antes:
                return "ok"
            if estado.get("pow"):
                return None
            aviso = self._js(JS_AVISO) or ""
            return aviso if aviso and aviso != previo else None
        nota = self._esperar(listo, ESPERA_COMPRA)
        if nota == "ok":
            return True, f"{self._reservas() - antes} reservada(s)"
        if nota == "recarga":
            return False, "la pagina se recargo sola (posible fila de espera)"
        return False, nota or f"sin respuesta en {ESPERA_COMPRA}s"

    def _en_verificacion(self):
        """Pagina de Cloudflare ("Un momento… Verificación de seguridad en curso")."""
        texto = (self._js("return (document.title || '') + ' ' + "
                          "(document.body ? document.body.innerText.slice(0, 400) : '');") or "").lower()
        return "un momento" in texto or "verificación de seguridad" in texto or "just a moment" in texto

    def abrir(self):
        self.motivo = ""
        self.conservar_pestana = False
        if not self.ya_cargada:
            self.cargar(self.driver, self.url)
        # Cloudflare a veces se resuelve solo tras unos segundos (el navegador del monitor lo hizo
        # el 28-oct-2026); otras se queda esperando a una persona (el Comet de reserva, la misma
        # tarde, 30 s parado). No se toca: se espera y, si sigue, se deja la pestana al usuario.
        espera = ESPERA_VERIFICACION if self._esperar(self._en_verificacion, 3) else ESPERA_PASO * 2
        estado = self._esperar(lambda: self._js(JS_ESTADO), espera)
        if not estado:
            if self._en_verificacion():
                self.conservar_pestana = True
                self.motivo = (f"Cloudflare pide la verificacion de seguridad en el navegador de reserva y "
                               f"no paso sola en {espera}s. La pestana queda abierta: pasala a mano ahi "
                               "(sirve para las siguientes reservas)")
            else:
                self.motivo = f"el mapa no cargo en {espera}s"
            return False
        if not estado.get("usuario"):
            self.motivo = "no hay sesion iniciada en Eleventickets en este navegador"
            return False
        return bool(self._esperar(lambda: self._js(JS_BLOQUES), ESPERA_PASO))

    def en_carrito(self):
        """Entradas reservadas en el carrito de esta cuenta, o None si no se pudo saber."""
        try:
            return self.driver.execute_async_script(JS_CARRITO)
        except Exception:
            return None

    def bloques(self):
        return self._js(JS_BLOQUES) or []

    def elegir_bloque(self, nombre):
        self._js(JS_CERRAR_DIALOGO)
        self.id_bloque = self._js(JS_PULSAR_BLOQUE, nombre) or ""
        if not self.id_bloque:
            return False
        # Un bloque numerado sin asientos libres tambien "abrio": si solo se esperaran los libres,
        # se perderian 15 s por bloque (Occidental 313 y 315, 30-oct-2026: todos B, O o R) con
        # otros bloques esperando, y el aviso diria "no se abrio".
        return bool(self._esperar(
            lambda: self._js(JS_PRODUCTOS) or self._js(JS_ASIENTOS_CARGADOS, self.id_bloque), ESPERA_PASO))

    def productos(self):
        return self._js(JS_PRODUCTOS) or []

    def fijar_cantidad(self, indice, n):
        """
        Deja n en el producto: sube con el "+" (se frena donde la pagina lo deshabilita) o
        baja con el "-" (tras un "agotado" la cantidad rechazada sigue marcada).
        """
        def actual():
            lista = self.productos()
            return lista[indice]["cantidad"] if indice < len(lista) else 0
        marcadas = actual()
        while marcadas != n:
            boton = "button.botao-soma" if marcadas < n else "button.botao-subtracao"
            if not self._clic(JS_BOTON_CANTIDAD, indice, boton):
                break
            previa = marcadas
            if not self._esperar(lambda: actual() != previa, ESPERA_RESPUESTA):
                break
            marcadas = actual()
        return marcadas

    def anadir(self):
        self._js(JS_CERRAR_DIALOGO)
        antes, previo = self._reservas(), self._js(JS_AVISO) or ""
        if not self._clic(JS_ANADIR):
            return False, "el boton 'Añadir al Carrito de Compras' no esta activo"
        ok, nota = self._resultado(antes, previo)
        if not ok:
            # El aviso ("¡El producto está agotado!" con su OK) tapa la lista de productos.
            self._js(JS_CERRAR_DIALOGO)
            self._esperar(lambda: not self._js(JS_AVISO), ESPERA_RESPUESTA)
        return ok, nota

    def asientos_libres(self):
        return self._js(JS_ASIENTOS, self.id_bloque) or []

    def reservar_asiento(self, id_asiento):
        # El dialogo de "producto anadido" del asiento anterior tapa el mapa.
        self._js(JS_CERRAR_DIALOGO)
        antes, previo = self._reservas(), self._js(JS_AVISO) or ""
        if not self._js(JS_PULSAR_ASIENTO, id_asiento):
            return False, "el asiento ya no esta en el mapa"
        if not self._esperar(lambda: self._js(JS_SUMAR_ASIENTO) or self._js(JS_AVISO), ESPERA_PASO):
            return False, f"el asiento no mostro su producto en {ESPERA_PASO}s"
        aviso = self._js(JS_AVISO)
        if aviso and not self._js(JS_SUMAR_ASIENTO):
            return False, aviso
        if not self._clic(JS_SUMAR_ASIENTO):
            return False, "el '+' del asiento no esta activo"
        return self._resultado(antes, previo)
