"""
Anade al carrito hasta 4 entradas de Eleventickets (Final Sudamericana), UNA vez.

Usa el Comet de reserva (iniciar_comet_debug.bat, puerto 9223) con la sesion de
Eleventickets iniciada y la verificacion de Cloudflare ya pasada en esa ventana.
Abre el evento en una pestana nueva, elige el primer sector libre de SECTORES, marca
hasta MAXIMO entradas y pulsa "Anadir al Carrito de Compras". Ahi se detiene: NO entra
al carrito ni al pago. La pestana queda abierta; paga tu desde "Carrito de Compras".
No manda Telegram.

    python reservar_eleventickets.py
    python reservar_eleventickets.py "<url>" "CAT2 - Oriental Tribuna Media" 4

Varios sectores (por prioridad) se separan con "|": "CAT2 - Oriental Tribuna Media|CAT2 - Oriental".
"""
import importlib.util
import os
import sys
import time

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

EVENTO = "Final CONMEBOL Sudamericana 2026"
URL = "https://sudamericana.eleventickets.com/#!/apresentacao/4bb1cb440b627393353ec181eb59a53056c9786c"
SECTORES = ["CAT2 - Oriental"]
MAXIMO = 4


def cargar_monitor():
    spec = importlib.util.spec_from_file_location(
        "monitor", os.path.join(RAIZ, "main13_filters_all_urls lina.py"))
    monitor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(monitor)
    return monitor


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else URL
    sectores = sys.argv[2].split("|") if len(sys.argv) > 2 else SECTORES
    maximo = int(sys.argv[3]) if len(sys.argv) > 3 else MAXIMO

    monitor = cargar_monitor()
    monitor.preparar_consola()
    import reserva_eleventickets as re11

    navegador, motivo = monitor.navegador_reserva(None)
    if navegador is None:
        print(f"No hay navegador de reserva: {motivo}")
        return 1

    print(f"Añadiendo al carrito hasta {maximo} x {' / '.join(sectores)} en {url} ...")
    navegador.switch_to.new_window("tab")
    pagina = re11.PaginaSelenium(navegador, url, monitor.navegar)
    reserva = re11.reservar(pagina, sectores, maximo=maximo)

    print()
    print("RESULTADO:", "OK" if reserva.ok else "FALLO")
    print(reserva)
    print()
    print(re11.mensaje(reserva, EVENTO, url, time.strftime("%H:%M:%S")))
    return 0 if reserva.ok else 2


if __name__ == "__main__":
    sys.exit(main())
