"""
Reserva de boletas en Ticketmaster.co hasta la pantalla de pago.

El bot llega hasta "Selecciona como deseas abonar" y SE DETIENE ahi: no elige
medio de pago ni escribe datos de tarjeta. El usuario paga en la pestana que
queda abierta, dentro del tiempo que da la reserva (unos 5 minutos).

Decisiones fijas (pedidas por el usuario, no las cambies sin preguntar):
  - Nunca se acepta la Garantia Extendida: siempre "no gracias".
  - La entrega es siempre "Boleto Digital en la App", aunque el evento ofrezca
    otras opciones. Si no existe, se avisa y NO se elige otra.

La logica (reservar) no conoce Selenium: habla con un objeto "pagina" con estos
metodos, para poder probarla con una pagina simulada:

    abrir_mapa()            -> bool   carga el evento y abre el panel de sectores
    elegir_sector(nombre)   -> bool
    fijar_cantidad(n)       -> int    cantidad que quedo marcada (puede ser < n)
    limpiar()               -> bool   deshace la seleccion y vuelve a los sectores
    clic(texto)             -> bool   clic en el elemento visible con ese texto
    texto()                 -> str    texto visible de la pagina
    esperar(condicion, s)   -> str|None   texto en cuanto condicion(texto) sea cierto

Fuente de los textos y del orden de pantallas: flujo real de Carlos Vives
Bucaramanga (sep-2026). Lo que NO esta verificado en vivo esta marcado abajo.
"""
import re
import time
import unicodedata
from dataclasses import dataclass

MAXIMO_POR_LOCALIDAD = 4       # Tope de Ticketmaster por localidad
ESPERA_RESPUESTA = 8           # Segundos antes de dar un clic por perdido
ESPERA_PASO = 15               # Segundos maximos esperando una pantalla nueva
PASOS_MAXIMOS = 12             # Pantallas entre la seleccion y el pago
TIEMPO_MAXIMO_RESERVA = 150    # Segundos para todo el intento

ENTREGA_OBLIGATORIA = "Boleto Digital en la App"
RECHAZO_GARANTIA = "no gracias"

RE_EXPIRA = re.compile(r"La reserva expira en\s*(\d{1,2}:\d{2})", re.I)
RE_PAGO = re.compile(r"Selecciona c.mo deseas abonar", re.I)
RE_GARANTIA = re.compile(r"recuperar el total de tu compra", re.I)
RE_ENTREGA = re.compile(r"Selecciona c.mo deseas recibir", re.I)
RE_TOTAL = re.compile(r"Total\s*\$\s*([\d.]+)")
# NO verificado en vivo: el texto exacto del aviso de "no hay boletas en esa
# seccion". Por eso solo cuenta si aparece DESPUES del clic (no estaba antes),
# y la falta de respuesta se trata igual que un error.
RE_SIN_BOLETAS = re.compile(
    r"no hay (boletas|entradas|tickets)|sin disponibilidad|ya no (hay|est.n)|no est. disponible", re.I)
# Conteo que muestra el selector: va en la linea justo despues del precio.
RE_CANTIDAD = re.compile(r"\$\s*[\d.]+\s*\+\s*\$\s*[\d.]+\s*\n\s*(\d+)\s*\n")


@dataclass
class Reserva:
    ok: bool
    sector: str = ""
    cantidad: int = 0      # boletas reservadas
    pedidas: int = 0       # boletas que se querian
    total: str = ""
    expira: str = ""
    detalle: str = ""
    retenidas: bool = False  # hay boletas retenidas aunque no se llegara al pago


def _sin_acentos(texto):
    base = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in base if unicodedata.category(c) != "Mn").lower()


def _continuar_seleccion(pagina):
    """Pulsa Continuar con la cantidad elegida. True si las boletas quedaron listadas."""
    antes = pagina.texto()

    def resuelto(t):
        if "Cambiar tarifa" in t:
            return True
        return bool(RE_SIN_BOLETAS.search(t)) and not RE_SIN_BOLETAS.search(antes)

    # Observado en vivo: el primer clic a veces no hace nada y el segundo si.
    # Es un unico reintento de clic en la misma pantalla, nunca una recarga.
    for espera in (ESPERA_RESPUESTA, ESPERA_PASO):
        pagina.clic("Continuar")
        t = pagina.esperar(resuelto, espera)
        if t is not None:
            return "Cambiar tarifa" in t
    return False


def _hasta_pago(pagina, sector, cantidad, pedidas, limite, reloj):
    """Recorre garantia, entrega y confirmacion hasta la pantalla de pago."""

    def fallo(detalle):
        return Reserva(False, sector, cantidad, pedidas, detalle=detalle, retenidas=True)

    estancados = 0
    for _ in range(PASOS_MAXIMOS):
        if reloj() > limite:
            return fallo("se acabo el tiempo antes de llegar al pago")
        t = pagina.texto()

        if RE_PAGO.search(t):
            expira = RE_EXPIRA.search(t)
            total = RE_TOTAL.findall(t)
            return Reserva(True, sector, cantidad, pedidas,
                           total=f"$ {total[-1]}" if total else "",
                           expira=expira.group(1) if expira else "")

        if "Confirmar reserva" in t:
            accion = "Confirmar reserva"
        elif RE_ENTREGA.search(t):
            accion = ENTREGA_OBLIGATORIA
        elif RE_GARANTIA.search(t):
            # La garantia viene marcada de fabrica y suma su linea al resumen:
            # mientras siga ahi, hay que rechazarla; cuando desaparece, se sigue.
            accion = RECHAZO_GARANTIA if "GARANTIA EXTENDIDA" in _sin_acentos(t).upper() else "Continuar"
        elif "Cambiar tarifa" in t:
            accion = "Continuar"
        else:
            accion = None

        if accion is None:
            estancados += 1
            pagina.esperar(lambda nuevo: nuevo != t, ESPERA_RESPUESTA)
        elif not pagina.clic(accion):
            if accion == ENTREGA_OBLIGATORIA:
                return fallo(f"el evento no ofrece '{ENTREGA_OBLIGATORIA}'; no elegi otra entrega")
            estancados += 1
        elif pagina.esperar(lambda nuevo: nuevo != t, ESPERA_PASO) is None:
            estancados += 1
        else:
            estancados = 0
        if estancados >= 2:
            return fallo(f"la pagina no avanza (ultimo paso: {accion or 'pantalla desconocida'})")
    return fallo("demasiados pasos sin llegar al pago")


def _reservar_sector(pagina, sector, maximo, minimo, limite, reloj):
    """Prueba 4, 3, 2, 1: la pagina no dice cuantas hay, solo rechaza las que sobran."""
    n = maximo
    while n >= minimo:
        if reloj() > limite:
            return Reserva(False, sector, pedidas=maximo, detalle="se acabo el tiempo")
        if not pagina.elegir_sector(sector):
            return Reserva(False, sector, pedidas=maximo, detalle="el sector no aparece o no se pudo abrir")

        marcadas = pagina.fijar_cantidad(n)
        if marcadas < minimo:
            pagina.limpiar()
            return Reserva(False, sector, pedidas=maximo,
                           detalle=f"el selector no pasa de {marcadas} boleta(s)")

        if _continuar_seleccion(pagina):
            return _hasta_pago(pagina, sector, marcadas, maximo, limite, reloj)

        pagina.limpiar()
        # Si el selector ya se quedo corto (marco 2 de 4), no se repite ese numero.
        n = min(n, marcadas) - 1
    return Reserva(False, sector, pedidas=maximo,
                   detalle=f"no hay boletas ni para {minimo} en este momento")


def reservar(pagina, sectores, maximo=MAXIMO_POR_LOCALIDAD, minimo=1, reloj=time.time):
    """
    Reserva boletas del primer sector de `sectores` que se deje, hasta el pago.

    Una sola reserva por llamada: en cuanto una funciona se devuelve. Un sector
    sin boletas ni para `minimo` pasa al siguiente.
    """
    limite = reloj() + TIEMPO_MAXIMO_RESERVA
    if not pagina.abrir_mapa():
        motivo = getattr(pagina, "motivo", "")
        return Reserva(False, detalle="no se pudo abrir el mapa del evento" + (f": {motivo}" if motivo else ""))
    ultimo = Reserva(False, detalle="sin sectores que reservar")
    for sector in sectores:
        ultimo = _reservar_sector(pagina, sector, maximo, minimo, limite, reloj)
        if ultimo.ok or ultimo.retenidas or reloj() > limite:
            break
    return ultimo


def mensaje(reserva, evento, url, hora):
    """Texto del aviso de Telegram con el resultado de la reserva."""
    if reserva.ok:
        texto = (f"🎟️ RESERVA LISTA - ENTRA A PAGAR\n\n📌 {evento}\n"
                 f"  • {reserva.cantidad} x {reserva.sector}\n")
        if reserva.cantidad < reserva.pedidas:
            texto += f"  • Solo se pudieron reservar {reserva.cantidad} de {reserva.pedidas}\n"
        if reserva.total:
            texto += f"💰 Total: {reserva.total}\n"
        if reserva.expira:
            texto += f"⏳ La reserva vence en {reserva.expira}\n"
        return (texto + "\nLa pestana de pago esta abierta en Chrome. Elige el medio de pago y paga.\n"
                f"🔗 {url}\n\n⏰ {hora}")
    texto = f"⚠️ NO PUDE RESERVAR\n\n📌 {evento}\n"
    if reserva.sector:
        texto += f"  • {reserva.sector}\n"
    texto += f"Motivo: {reserva.detalle}\n"
    if reserva.retenidas:
        texto += (f"Ojo: hay {reserva.cantidad} boleta(s) retenidas en la pestana abierta; "
                  "termina a mano o se liberan solas.\n")
    return texto + f"🔗 {url}\n\n⏰ {hora}"


# ----------------------------------------------------------------------------
# Pagina real (Selenium). NO verificada en vivo: los selectores salen del flujo
# observado (textos, .sectorOption, botones sin texto del selector), pero no se
# ha ejecutado contra la pagina desde Selenium. Comprobarlo con una reserva real
# supervisada antes de dejarlo activo sin vigilancia.
# ----------------------------------------------------------------------------
_JS_VISIBLE = ("var vis=function(e){var r=e.getBoundingClientRect();"
               "return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden';};")

JS_CLIC_TEXTO = _JS_VISIBLE + """
var t = arguments[0].toLowerCase();
var c = Array.from(document.querySelectorAll('button,a,[role=button],label,h1,h2,h3,h4,h5,h6,span,div,p,li'))
  .filter(function (e) {
      if (!vis(e)) { return false; }
      var x = (e.innerText || '').trim().toLowerCase();
      return x === t || (x.indexOf(t) === 0 && x.length < t.length + 40);
  });
c = c.filter(function (e) { return !c.some(function (o) { return o !== e && e.contains(o); }); });
if (!c.length) { return false; }
c[0].scrollIntoView({block: 'center'});
c[0].click();
return true;
"""

JS_ELEGIR_SECTOR = _JS_VISIBLE + """
var sin = function (s) { return (s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').trim().toLowerCase(); };
var n = sin(arguments[0]);
var o = Array.from(document.querySelectorAll('.sectorOption')).filter(function (e) {
    var h = e.querySelector('h5');
    return sin(h ? h.innerText : e.innerText) === n;
});
if (!o.length) { return false; }
o[0].click();
return true;
"""

# Garantia: "no gracias" NO es un elemento propio, es un nodo de texto suelto junto
# a un <strong>, asi que JS_CLIC_TEXTO no lo encuentra (asi fallo la primera
# reserva real). Las opciones son <li> de ul.insurance-options y la elegida lleva la
# clase "active" (verificado en vivo, sep-2026). Se hace clic en la cabecera de la
# opcion "no gracias"; si ya esta activa no se toca.
JS_RECHAZAR_GARANTIA = """
var li = Array.from(document.querySelectorAll('ul.insurance-options > li')).filter(function (e) {
    return /no gracias/i.test(e.innerText || '');
})[0];
if (!li) { return false; }
if (li.classList.contains('active')) { return true; }
(li.querySelector('.insurance-header') || li).click();
return true;
"""

# El "+" es el ultimo boton sin texto del panel "Seleccionar tarifa" (el "-" va
# antes). Se sube desde el titulo del panel hasta el primer contenedor que tenga
# esos dos botones, para no confundirlo con el zoom del mapa.
JS_SUMAR = _JS_VISIBLE + """
var titulo = Array.from(document.querySelectorAll('*')).filter(function (e) {
    return vis(e) && (e.innerText || '').trim() === 'Seleccionar tarifa';
})[0];
var cont = titulo;
for (var i = 0; cont && i < 6; i++) {
    var bs = Array.from(cont.querySelectorAll('button')).filter(function (b) {
        return vis(b) && !(b.innerText || '').trim();
    });
    if (bs.length >= 2) {
        var mas = bs[bs.length - 1];
        if (mas.disabled || mas.getAttribute('aria-disabled') === 'true') { return false; }
        mas.click();
        return true;
    }
    cont = cont.parentElement;
}
return false;
"""


class PaginaSelenium:
    """Pagina real sobre un driver de Selenium, en la pestana que este activa."""

    def __init__(self, driver, url, cargar):
        self.driver = driver
        self.url = url
        self.cargar = cargar  # navegar() del monitor: respeta el limite de carga
        self.motivo = ""      # por que fallo abrir_mapa(), para el aviso de Telegram

    def texto(self):
        try:
            return self.driver.execute_script(
                "return document.body ? document.body.innerText : '';") or ""
        except Exception:
            return ""

    def esperar(self, condicion, segundos):
        limite = time.time() + segundos
        while True:
            t = self.texto()
            if condicion(t):
                return t
            if time.time() >= limite:
                return None
            time.sleep(0.5)

    def clic(self, texto):
        if texto == RECHAZO_GARANTIA:
            return bool(self.driver.execute_script(JS_RECHAZAR_GARANTIA))
        return bool(self.driver.execute_script(JS_CLIC_TEXTO, texto))

    def abrir_mapa(self):
        self.motivo = ""
        self.cargar(self.driver, self.url)
        texto = self.esperar(lambda t: "Ver entradas" in t, ESPERA_PASO)
        if texto is None:
            self.motivo = (f"la pagina no mostro 'Ver entradas' en {ESPERA_PASO}s "
                           "(carga lenta o bloqueada en este navegador)")
            return False
        # Sin sesion la reserva no pasa del primer Continuar: se dice desde ya.
        if "Cerrar sesión" not in texto and "Ingresar" in texto:
            self.motivo = "no hay sesion iniciada en Ticketmaster en este navegador"
            return False
        self.clic("Ver entradas")
        if self.esperar(lambda t: "Seleccionar sector" in t, ESPERA_PASO) is None:
            self.motivo = (f"tras 'Ver entradas' no aparecio el panel de sectores en {ESPERA_PASO}s "
                           "(el mapa no cargo)")
            return False
        return True

    def elegir_sector(self, nombre):
        if not self.driver.execute_script(JS_ELEGIR_SECTOR, nombre):
            return False
        return self.esperar(lambda t: "Seleccionar tarifa" in t, ESPERA_PASO) is not None

    def _cantidad(self):
        m = RE_CANTIDAD.search(self.texto())
        return int(m.group(1)) if m else 0

    def fijar_cantidad(self, n):
        actual = self._cantidad()
        while actual < n:
            if not self.driver.execute_script(JS_SUMAR):
                break
            if self.esperar(lambda t: self._cantidad() > actual, ESPERA_RESPUESTA) is None:
                break
            actual = self._cantidad()
        return actual

    def limpiar(self):
        # Se deshace la seleccion desde la propia pagina; recargar es el ultimo recurso.
        if self.clic("Limpiar selección") and \
                self.esperar(lambda t: "Seleccionar sector" in t, ESPERA_RESPUESTA) is not None:
            return True
        return self.abrir_mapa()
