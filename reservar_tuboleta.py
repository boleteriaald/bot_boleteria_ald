"""
Anade al carrito boletas de un evento de Tuboleta, UNA vez, sin monitor ni Telegram.

Usa el navegador de reserva (iniciar_comet_debug.bat, puerto 9223). Abre la pagina en una
pestana nueva, elige la primera localidad a la venta que case con las palabras, marca la
mayor cantidad que deje la pagina (o MAXIMO) y pulsa "Anadir al carrito"; si la rechaza,
prueba con una menos. Ahi se detiene: NO paga. Paga tu desde "Mi cesta" en esa pestana.

    python reservar_tuboleta.py "<url de selection/event/seat o /date>"
    python reservar_tuboleta.py "<url>" "platea|tribuna" 6
    python reservar_tuboleta.py "<url>" "platea|segundo piso" 0 20     (0 = el maximo; hasta 20 en total)

Las palabras (por prioridad) se separan con "|"; vacio ("") = cualquier localidad.
"""
import importlib.util
import os
import sys
import time

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)


def cargar_monitor():
    spec = importlib.util.spec_from_file_location(
        "monitor", os.path.join(RAIZ, "main13_filters_all_urls lina.py"))
    monitor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(monitor)
    return monitor


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    url = sys.argv[1]
    sectores = [s for s in sys.argv[2].split("|") if s.strip()] if len(sys.argv) > 2 else []
    maximo = (int(sys.argv[3]) or None) if len(sys.argv) > 3 else None
    total = int(sys.argv[4]) if len(sys.argv) > 4 else None

    monitor = cargar_monitor()
    monitor.preparar_consola()
    import reserva_tuboleta as rtb

    navegador, motivo = monitor.navegador_reserva(None)
    if navegador is None:
        print(f"No hay navegador de reserva: {motivo}")
        return 1

    print(f"Añadiendo al carrito {maximo or 'el máximo'} x {' / '.join(sectores) or 'cualquier localidad'} en {url} ...")
    navegador.switch_to.new_window("tab")
    pagina = rtb.PaginaSelenium(navegador, url, monitor.navegar, al_verificar=lambda: print(
        "\n>>> Tuboleta pide verificar que no eres un robot: resuélvela YA en el Comet de reserva "
        f"(te espero {rtb.ESPERA_VERIFICACION // 60} min)\n"))
    reserva = rtb.reservar(pagina, sectores, maximo=maximo, total=total)

    print()
    print("RESULTADO:", "OK" if reserva.ok else "FALLO")
    print(reserva)
    print()
    print(rtb.mensaje(reserva, "Tuboleta", url, time.strftime("%H:%M:%S")))
    return 0 if reserva.ok else 2


if __name__ == "__main__":
    sys.exit(main())
