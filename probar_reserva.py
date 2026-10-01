"""
Prueba la reserva de Ticketmaster UNA vez, sin el monitor ni el estado de avisos.

Usa el Comet de reserva (iniciar_comet_debug.bat, puerto 9223) con su sesion de
Ticketmaster. Reserva de verdad: deja la pestana abierta en la pantalla de pago
(o donde se quede) con el contador corriendo. NO paga ni toca ningun medio de pago.
No manda Telegram.

    python probar_reserva.py
    python probar_reserva.py "<url>" "<sector>" 4

No lo ejecutes con el monitor corriendo y reservando la misma URL: se pisarian.
Para cancelar la reserva de prueba: "Cancelar compra" y luego "Aceptar".
"""
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

# URL = "https://www.ticketmaster.co/event/carlos-vives-bucaramanga-venta-general"
# SECTOR = "VIP (silletería no numerada)"

URL = "https://www.ticketmaster.co/event/iron-maiden-venta-general"
SECTOR = "111 - 113 - 115"


def cargar_monitor():
    spec = importlib.util.spec_from_file_location(
        "monitor", os.path.join(RAIZ, "main13_filters_all_urls lina.py"))
    monitor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(monitor)
    return monitor


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else URL
    sector = sys.argv[2] if len(sys.argv) > 2 else SECTOR
    maximo = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    monitor = cargar_monitor()
    monitor.preparar_consola()
    import reserva_ticketmaster as rt

    navegador, motivo = monitor.navegador_reserva(None)
    if navegador is None:
        print(f"No hay navegador de reserva: {motivo}")
        return 1

    print(f"Reservando hasta {maximo} x {sector} en {url} ...")
    navegador.switch_to.new_window("tab")
    pagina = rt.PaginaSelenium(navegador, url, monitor.navegar)
    reserva = rt.reservar(pagina, [sector], maximo=maximo)

    print()
    print("RESULTADO:", "OK" if reserva.ok else "FALLO")
    print(reserva)
    print()
    print(rt.mensaje(reserva, "Prueba", url, "--:--:--"))
    return 0 if reserva.ok else 2


if __name__ == "__main__":
    sys.exit(main())
