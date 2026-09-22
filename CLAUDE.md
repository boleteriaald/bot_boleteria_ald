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

Las pruebas están en `tests/` (unittest, sin dependencias nuevas) y se ejecutan con
`python -m unittest discover -s tests -v`. Antes vivían en carpetas temporales y se
perdieron dos veces: **cualquier prueba nueva va a `tests/`**.

- `tests/apoyo.py` carga una copia nueva del monitor por prueba, con `config` doble,
  Telegram simulado, estado y registro en carpeta temporal y **reloj simulado**. Se
  sustituye el `time` del script, nunca el `time` global: parchear `time.sleep`
  global contamina a las demás pruebas del proceso.
- `apoyo` llama a `preparar_consola()`: sin eso, los emojis de los `print` del
  monitor tumban las pruebas en consolas cp1252.
- Las pruebas no deben depender de `URLS_A_MONITOREAR` ni `FILTROS_LOCALIDADES`
  reales: una ya se rompió cuando el usuario cambió un filtro. Cada prueba pone
  los suyos.
- `test_chrome_real.py` está desactivado salvo `MONITOR_PRUEBAS_CHROME=1`; la que
  cierra Chrome, salvo `MONITOR_PRUEBAS_RELANZAR=1`. Exigen el monitor detenido.
- `discover` es obligatorio: ejecutado como archivo suelto, `apoyo` no se encuentra.

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

## TaquillaLive: lo que ya se sabe

Descubierto contra páginas reales (evento Feid, sep-2026); conviene no volver a
aprenderlo a golpes.

- `performance-details` **nunca** tiene disponibilidad real por localidad: es un
  catálogo estático (nombre/aforo/precio) más un botón genérico "Compra Tus
  Tiquetes" que solo dice si la venta del evento está abierta en general. Se trata
  como aviso `[SIN DETALLE]`, igual que la venta abierta de Ticketmaster — no se usa
  el nombre del evento como si fuera una localidad (ese error ya se cometió y se
  corrigió una vez en Ticketmaster, ver `verificar_disponibilidad_ticketmaster`).
- El detalle real por localidad solo está en `book-performance`, y ahí cada sector
  vive **siempre** en el DOM dentro de `.ticket-list-box[data-section_id]` con el
  nombre en `.sector_name` — ese catálogo no cambia. Lo que sí cambia en vivo es la
  **visibilidad** (`style="display:none"`) de cada caja: TaquillaLive retiene el
  cupo en el carrito de otro comprador durante la compra y lo libera segundos o
  minutos después. Es la misma distinción catálogo-vs-disponibilidad-real que en
  Ticketmaster (`sector.available` siempre `true`, lo real en
  `sector.sections[].available`). Por eso se decide con `is_displayed()`, nunca con
  `sector.text`: Selenium devuelve texto vacío para un elemento oculto, así que
  decidir por texto vacío hacía que una caja retenida se descartara en silencio en
  vez de contarse como agotada.
- Cuando **todos** los sectores están retenidos a la vez, la página muestra el aviso
  "Sin disponibilidad por alta demanda del evento, en el momento todos los tickets
  están en proceso de compra por otros usuarios" y oculta las tres cajas. No es un
  agotado real. `detectar_sala_espera()` ya reconoce la frase "alta demanda", así
  que se reutiliza tal cual para avisar `[SIN DETALLE]` en vez de reportar 0
  disponibles.
- Un evento de mucha demanda (p. ej. Stream Fighters/Westcol) puede redirigir
  `book-performance` entero a una sala de espera de terceros en `queue-it.net`, con
  markup que no tiene nada que ver con TaquillaLive. Se detecta por dominio
  (`queue-it.net` en `driver.current_url`) además del texto de la página.
- El barrido genérico `div[contains(@class,'ticket')]` conjeturado antes de verificar
  contra la página real también capturaba los contenedores envolventes de cada
  sector (`ticket-list-boxes`, `ticket-list-trigger`, `ticket-list-content`) como si
  fueran sectores aparte — la causa más probable de los 22 "sectores" que se leyeron
  alguna vez para Gorillaz (ver Pendientes). El selector `.ticket-list-box` es
  específico y se prueba primero; el barrido genérico queda solo de reserva por si
  otro evento usa un theme distinto.

## Pendientes acordados

Hechos: README real, deduplicación, detector de Ticketmaster por sector, detección de
bloqueo y de sala de espera, normalización de nombres en los filtros, límites de
tiempo en scripts y cargas de página, registro en `logs/monitor.log`, sin `except:`
desnudos, cada URL aislada en su propio `try`, emojis seguros en consolas cp1252 y
reintento de los avisos que Telegram no pudo entregar (`deshacer_avisos()`) y
reconexión y relanzamiento automático de Chrome (`sesion_viva()` antes de cada URL,
`recuperar_sesion()`), y pruebas en `tests/`.

Sobre la reconexión y el relanzamiento:

- Los detectores capturan todas las excepciones y devuelven listas vacías, así que
  una sesión muerta nunca llega al bucle como error; hay que preguntar por ella.
- **Contra un Chrome cerrado, un intento de chromedriver tarda 63 s en fallar**
  (medido). Por eso `conectar_chrome()` y `sesion_viva()` consultan antes el puerto
  de depuración (`puerto_depuracion_activo()`, milisegundos). Antes, con 10 intentos,
  el bot pasaba más de 10 minutos ciego.
- `sesion_viva()` captura `Exception` a propósito: si muere chromedriver, el error es
  de la conexión HTTP local, no de Selenium.
- `soltar_sesion()` para chromedriver sin cerrar Chrome; `lanzar_chrome()` usa
  `cmd /c start`, como el `.bat`, para que Chrome quede independiente. Verificado
  contra Chrome real.
- Relanzamiento como mucho cada `INTERVALO_RELANZAMIENTO` (5 min): con un Chrome
  abierto con el perfil del monitor pero sin modo debug, cada relanzamiento solo
  abre otra ventana en esa instancia y el puerto nunca se activa.

Por orden:

1. Limpieza: `es_pagina_de_fechas` y `obtener_primera_fecha_disponible` no se llaman
   nunca (`buscar_disponibilidad_pasala` está dormida, no muerta: se conserva);
   `requirements.txt` sin versión de `python-telegram-bot` y con `requests` sin uso;
   el nombre del script lleva espacio y número de versión; restos de git de la
   reescritura del historial (rama `respaldo-antes-de-limpiar`, stash, `refs/original`).
2. Falsos positivos por selectores genéricos (`div` con clase `row`) en Tuboleta.
   El más delicado: tocarlo solo verificando contra páginas reales. La mitad de
   TaquillaLive (book) ya se resolvió con el selector `.ticket-list-box` — ver
   "TaquillaLive: lo que ya se sabe".
