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

`config.example.py` es la plantilla pública; si se añade una opción de
configuración nueva, hay que reflejarla ahí (sin valores reales).

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

La configuración actual —17 URLs por ronda, `driver.get()` con espera fija de 3-4 s,
sin pausa entre rondas, más `PAUSA_TRAS_DISPONIBILIDAD`— lleva **más de 6 meses
ejecutándose 24/7 sin un solo bloqueo** por parte de las boleteras. Es una línea base
probada empíricamente y es la referencia a preservar.

Regla dura: **ningún cambio puede aumentar la huella de peticiones** — ni esperas más
cortas, ni reintentos automáticos, ni recargas extra de página, ni más visitas por
ronda. Si un cambio lo implicara, avisar antes y no hacerlo por iniciativa propia.

Lo contrario tampoco se hace a la ligera: frenar el bucle "por precaución" cuesta
capacidad de reacción, y aquí eso cuesta boletas. No añadir pausas entre rondas,
aleatorización de tiempos ni escalonado de URLs sin que el usuario lo pida.

Contexto que evita repetir un error de diagnóstico: el usuario **sí** sufrió un bloqueo
de IP, pero fue con **otro código, en otro repositorio**, modificado por otra IA. Nunca
con este. No atribuir aquel incidente a este código ni usarlo para justificar cambios
de ritmo aquí.

## Pendientes acordados

Por orden, tras la reescritura del README y la deduplicación:

1. Ticketmaster devuelve el nombre del evento en vez de localidades, así que los
   filtros por localidad no funcionan en esas URLs.
2. 27 `except:` desnudos (capturan también `KeyboardInterrupt`) y sin logging a
   archivo: tras una noche corriendo no queda rastro de lo ocurrido.
3. Sin reconexión: si Chrome se cierra, el bucle gira registrando errores.
4. Falsos positivos por selectores genéricos (`div` con clase `row`).
5. Código muerto: `es_pagina_de_fechas`, `obtener_primera_fecha_disponible` y
   `buscar_disponibilidad_pasala` no se invocan nunca.
