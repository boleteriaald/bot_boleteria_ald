"""
Prueba manual del canal de Telegram: envia mensajes REALES a tu chat.

A diferencia de las pruebas de tests/, que sustituyen el envio por un doble,
esta usa tu config.py y tu bot de verdad, porque lo que comprueba es justamente
que el mensaje llegue al telefono.

No abre Chrome ni visita ninguna boletera.

Uso:
    python probar_telegram.py          # un aviso de disponibilidad de ejemplo
    python probar_telegram.py todos    # ademas, los avisos de Chrome y de bloqueo
"""
import importlib.util
import sys
import time

spec = importlib.util.spec_from_file_location("monitor", "main13_filters_all_urls lina.py")
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)
monitor.preparar_consola()

HORA = time.strftime("%H:%M:%S")
SALTO = chr(10)

AVISO_DISPONIBILIDAD = (
    "🧪 PRUEBA DEL BOT (no hay boletas, es un ensayo)" + SALTO * 2
    + "🎉 ¡DISPONIBILIDAD DETECTADA!" + SALTO * 2
    + "📌 Evento de prueba" + SALTO
    + "📅 13 de noviembre de 2026 a las 21:30" + SALTO * 2
    + "📍 TICKETMASTER - 2 disponibles" + SALTO
    + "  • 117-118-119-120 (Mayores +18)" + SALTO
    + "  • Platea 1 (Mayores +18)" + SALTO
    + "  🔗 https://www.ticketmaster.co/event/ejemplo" + SALTO * 2
    + f"⏰ {HORA}"
)

AVISO_CHROME = (
    "🧪 PRUEBA DEL BOT (Chrome no se cayo, es un ensayo)" + SALTO * 2
    + "🔄 Chrome se cerró o dejó de responder y lo relancé automáticamente. "
    + "El monitor vuelve a vigilar (8 s sin conexión)." + SALTO * 2
    + f"⏰ {HORA}"
)

AVISO_BLOQUEO = (
    "🧪 PRUEBA DEL BOT (no hay bloqueo, es un ensayo)" + SALTO * 2
    + "ATENCION: posible bloqueo anti-bot" + SALTO * 2
    + "Sitio: www.ticketmaster.co" + SALTO
    + "Motivo: titulo de la pagina: 'Just a moment...'" + SALTO * 2
    + "El monitor NO puede leer disponibilidad en este sitio mientras dure." + SALTO * 2
    + f"⏰ {HORA}"
)

mensajes = [("aviso de disponibilidad", AVISO_DISPONIBILIDAD)]
if len(sys.argv) > 1 and sys.argv[1] == "todos":
    mensajes += [("aviso de Chrome relanzado", AVISO_CHROME), ("aviso de bloqueo", AVISO_BLOQUEO)]

print("=" * 70)
print("PRUEBA DEL CANAL DE TELEGRAM")
print("=" * 70)
print(f"Chat ID configurado: {monitor.TELEGRAM_CHAT_ID}")
print(f"Mensajes a enviar  : {len(mensajes)}")

fallos = 0
for nombre, mensaje in mensajes:
    print()
    print(f"→ Enviando {nombre}...")
    if monitor.enviar_notificacion(mensaje):
        print(f"   ✓ {nombre}: ENTREGADO a Telegram")
    else:
        fallos += 1
        print(f"   ✗ {nombre}: NO se pudo enviar")

print()
print("=" * 70)
if fallos:
    print(f"✗ {fallos} de {len(mensajes)} no salieron. Revisa el token y el chat id en config.py,")
    print("  y que le hayas escrito al menos una vez a tu bot desde Telegram.")
    sys.exit(1)
print(f"✓ Los {len(mensajes)} mensajes salieron. Compruébalo en tu Telegram.")
