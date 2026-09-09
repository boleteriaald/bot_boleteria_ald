"""
Prueba aislada del detector de Ticketmaster.

Visita UNA sola vez la URL indicada, muestra las localidades disponibles y
agotadas, y aplica el filtro configurado para esa URL. No envia nada por
Telegram y no toca el bucle de monitoreo.

Requisito: Chrome en modo debug ya abierto (iniciar_chrome_debug.bat).

Uso:
    python probar_ticketmaster.py
    python probar_ticketmaster.py "https://www.ticketmaster.co/event/otro-evento"
"""
import importlib.util
import sys

URL_POR_DEFECTO = "https://www.ticketmaster.co/event/calvin-harris-venta-general"

spec = importlib.util.spec_from_file_location("monitor", "main13_filters_all_urls lina.py")
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

url = sys.argv[1] if len(sys.argv) > 1 else URL_POR_DEFECTO

print("=" * 70)
print("PRUEBA DEL DETECTOR DE TICKETMASTER")
print("=" * 70)
print(f"URL: {url}")

driver = monitor.conectar_chrome()
if not driver:
    sys.exit("No se pudo conectar a Chrome. Ejecuta primero iniciar_chrome_debug.bat")

disponibles, agotadas, url_final = monitor.verificar_disponibilidad_ticketmaster(driver, url)

print()
print("=" * 70)
print("RESULTADO")
print("=" * 70)
print(f"DISPONIBLES ({len(disponibles)}): {', '.join(disponibles) if disponibles else 'ninguna'}")
print(f"AGOTADAS    ({len(agotadas)}): {', '.join(agotadas) if agotadas else 'ninguna'}")

filtro = monitor.FILTROS_LOCALIDADES.get(url_final)
print()
if filtro:
    print(f"Filtro configurado para esta URL: {', '.join(filtro)}")
    coinciden = monitor.filtrar_localidades(disponibles, url_final)
    if coinciden:
        print(f"AVISARIA por: {', '.join(coinciden)}")
    else:
        print("NO avisaria: hay disponibilidad, pero ninguna coincide con el filtro")
else:
    print("Sin filtro para esta URL: avisaria de cualquier disponibilidad")
    if disponibles:
        print(f"AVISARIA por: {', '.join(disponibles)}")

print()
print("Nota: esta URL debe estar en URLS_A_MONITOREAR para que el bot la revise")
print("en cada ronda. Ahora mismo solo aparece en FILTROS_LOCALIDADES.")
