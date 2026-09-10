# Monitor de boletas — convenciones del proyecto

Complementa las reglas globales de `~/.claude/CLAUDE.md`, que siguen aplicando.

## Qué es esto

Monitor con Selenium que revisa URLs de Tuboleta/checkout, Pásala (reventa),
Ticketmaster.co y TaquillaLive, y avisa por Telegram cuando aparecen localidades
disponibles. **No compra**: solo observa y notifica. Ver `README.md`.

Repositorio: `boleteriaald/bot_boleteria_ald` — **es público**.

## Archivos que nunca se suben

- `config.py` — token de Telegram y credenciales. Está en `.gitignore` y **debe
  seguir estándolo**. El repo es público: una credencial subida por error queda
  indexada y la recogen bots en minutos.
- `estado_notificaciones.json` — estado local de avisos ya enviados.
- `.venv/`, `.idea/`, `__pycache__/`.

Antes de cada `git add`, revisar `git status` y confirmar que ninguno aparece.

## Ejecución y pruebas

El script necesita Chrome en modo debug (`iniciar_chrome_debug.bat`, puerto 9222) y
sesión ya iniciada en las plataformas. Se lanza así:

```bash
python "main13_filters_all_urls lina.py"
```

El nombre del archivo lleva un espacio, así que siempre va entre comillas.

No hay suite de tests. Para probar lógica sin navegador, cargar el módulo con
`importlib` y sustituir `config` por un doble; nunca usar el `config.py` real ni el
bot de Telegram real en una prueba.

Verificación mínima tras editar el script:

```bash
python -m py_compile "main13_filters_all_urls lina.py"
```

## Cómo se edita este código

- `URLS_A_MONITOREAR` y `FILTROS_LOCALIDADES` son **datos del usuario**, no código:
  Aldemar añade y comenta eventos ahí a mano y con frecuencia. No reordenarlos,
  no "limpiar" las URLs comentadas y no tocarlos salvo petición explícita.
- Las claves de `FILTROS_LOCALIDADES` deben coincidir **carácter por carácter** con
  las URLs de `URLS_A_MONITOREAR`, o el filtro se ignora en silencio.
- Antes de tocar el script, comprobar si hay cambios sin commitear del usuario en
  esas dos estructuras y preservarlos.

## Criterio para las notificaciones

Un mensaje de más molesta; **uno de menos cuesta la boleta**. Ante la duda, notificar.

Por eso la deduplicación tolera lecturas fallidas: una localidad no se da por agotada
hasta 3 lecturas consecutivas sin verla (`LECTURAS_VACIAS_PARA_OLVIDAR`). Sin esa
histéresis, un parpadeo de la página reintroduce el spam que la deduplicación vino a
resolver. No bajar ese umbral a 1.

Configuración vigente: aviso al aparecer, recordatorio cada 10 minutos mientras siga
disponible, sin aviso cuando se agota.

## Ritmo de peticiones: no aumentarlo nunca

La configuración actual —una visita por URL y ronda, en secuencia, con espera fija
de 3-4 s tras cada carga, sin pausa entre rondas, más `PAUSA_TRAS_DISPONIBILIDAD`— lleva **más de 6 meses
ejecutándose 24/7 sin un solo bloqueo** por parte de las boleteras. Es una línea base
probada empíricamente y es la referencia a preservar.

Regla dura: **ningún cambio puede aumentar la huella de peticiones** — ni esperas más
cortas, ni reintentos automáticos, ni recargas extra de página, ni más visitas por
ronda. Si un cambio lo implicara, avisar antes y no hacerlo por iniciativa propia.
Añadir URLs a la lista no cuenta: las visitas son secuenciales, así que la ronda se
alarga pero el ritmo de peticiones por minuto no cambia.

Los límites de tiempo (`TIEMPO_MAXIMO_SCRIPT`, `TIEMPO_MAXIMO_CARGA`) solo acotan
esperas; nunca reintentan. Si una carga se agota, `navegar()` detiene la página y lee
lo que haya llegado: el contenido que importa llega mucho antes que el evento de
carga completa, y descartar la página sería un falso "no hay disponibilidad".

Lo contrario tampoco se hace a la ligera: frenar el bucle "por precaución" cuesta
capacidad de reacción, y aquí eso cuesta boletas. No añadir pausas entre rondas,
aleatorización de tiempos ni escalonado de URLs sin que el usuario lo pida.

Contexto que evita repetir un error de diagnóstico: el usuario **sí** sufrió un bloqueo
de IP, pero fue con **otro código, en otro repositorio**, modificado por otra IA. Nunca
con este. No atribuir aquel incidente a este código ni usarlo para justificar cambios
de ritmo aquí.

## Ticketmaster: lo que ya se sabe

Descubierto contra páginas reales; conviene no volver a aprenderlo a golpes.

- La página publica su catálogo en el objeto global `App`, ya en el HTML inicial. No
  hace falta pulsar "Ver entradas": algunos eventos ni siquiera tienen ese botón.
- La unidad de aviso es el **sector**, no la sección. Las secciones no significan lo
  mismo en cada recinto: en Calvin Harris son localidades (`119`), en Anuel AA son
  asientos numerados (251 elementos llamados `1`, `2`…).
- `sector.available` vale `true` siempre: es un dato de catálogo. La disponibilidad
  real está en `sector.sections[].available`.
- El catálogo aparece a distinta profundidad según el evento (nivel 6 en Calvin, 9
  en Anuel). El recorrido necesita control de ciclos: `App` es Backbone con
  referencias circulares, y en un evento agotado no hay catálogo y se recorre todo.
- Los nombres de la página informativa (`evento/x-2026`) **no coinciden** con los de
  venta (`evento/x-2026-venta-general`): los rangos se parten en pares e impares, las
  comas pasan a guiones, se añaden sufijos de edad y hay espacios dobles escritos a
  mano. `normalizar_nombre()` absorbe lo tipográfico; lo estructural no.
- En estadios (BTS en El Campín) la numeración de bloques se reinicia en cada
  tribuna: filtrar por número no sirve, hay que filtrar por nombre de tribuna.
- Ticketmaster carga Cloudflare Turnstile y AWS WAF en **todas** sus páginas. Su
  presencia no indica bloqueo.
- `probar_ticketmaster.py` y el monitor comparten la misma pestaña de Chrome: no
  ejecutar la prueba con el monitor corriendo, se pisan.

## Pendientes acordados

Hechos: README real, deduplicación, detector de Ticketmaster por sector, detección de
bloqueo y de sala de espera, normalización de nombres en los filtros, límites de
tiempo en scripts y cargas de página, registro en `logs/monitor.log`, sin `except:`
desnudos, cada URL aislada en su propio `try`, emojis seguros en consolas cp1252 y
reintento de los avisos que Telegram no pudo entregar (`deshacer_avisos()`).

Por orden:

1. Sin reconexión: si Chrome se cierra, el bucle gira registrando errores.
2. Limpieza: `es_pagina_de_fechas` y `obtener_primera_fecha_disponible` no se llaman
   nunca (`buscar_disponibilidad_pasala` está dormida, no muerta: se conserva);
   `requirements.txt` sin versión de `python-telegram-bot` y con `requests` sin uso;
   el nombre del script lleva espacio y número de versión; restos de git de la
   reescritura del historial (rama `respaldo-antes-de-limpiar`, stash, `refs/original`).
3. Falsos positivos por selectores genéricos (`div` con clase `row`) en Tuboleta y
   TaquillaLive. El más delicado: tocarlo solo verificando contra páginas reales.
   Evidencia en vivo: Gorillaz en TaquillaLive (book) lee 22 sectores disponibles.
