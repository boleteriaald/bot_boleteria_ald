# Monitor de boletas — convenciones del proyecto

Complementa las reglas globales de `~/.claude/CLAUDE.md`, que siguen aplicando.

## Qué es esto

Monitor con Selenium que revisa URLs de Tuboleta/checkout, Pásala (reventa),
Ticketmaster.co y TaquillaLive, y avisa por Telegram cuando aparecen localidades
disponibles. **No paga nunca**: observa y notifica; solo en Ticketmaster y solo para
las URLs de `RESERVAR_TICKETMASTER` (vacío por defecto) reserva boletas hasta la
pantalla de pago y deja el pago al usuario (`reserva_ticketmaster.py`). Ver `README.md`.

Repositorio: `boleteriaald/bot_boleteria_ald` — **es público**.

## Archivos que nunca se suben

- `config.py` — token de Telegram y credenciales. Está en `.gitignore` y **debe
  seguir estándolo**. El repo es público: una credencial subida por error queda
  indexada y la recogen bots en minutos.
- `estado_notificaciones.json` — estado local de avisos ya enviados.
- `.venv/`, `.idea/`, `__pycache__/`.

Antes de cada `git add`, revisar `git status` y confirmar que ninguno aparece.

## Ejecución y pruebas

El script necesita Comet en modo debug (`iniciar_comet_monitor.bat`, puerto 9224; si no
está abierto, el monitor lo abre solo) y sesión ya iniciada en las plataformas que la
exijan. Se lanza así:

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
- Una página de evento sin venta puede decir "AGOTADO" o "EVENTO FINALIZADO" (BTS,
  sep-2026); solo la primera la reconoce el bot como agotado. La segunda cae a la
  detección de sala de espera, y los términos y condiciones de BTS contienen "Cuando
  sea tu turno para comprar…": sin el límite de longitud de `detectar_sala_espera()`
  (`LONGITUD_MAXIMA_PAGINA_ESPERA`) eso avisaba en falso "SALA DE ESPERA, la venta
  abrió". Una sala de espera real es una página corta.
- `bts-world-tour-2026` es el índice con 4 botones (Preventa Army Membership y Venta
  General × 2 y 3 de octubre). El monitor solo vigila las dos Venta General; las URLs
  de Army Membership son `bts-world-tour-army-membership-{viernes-2,sabado-3}-octubre`.

## Reserva en Ticketmaster: lo que ya se sabe

Flujo real (Carlos Vives Bucaramanga, sep-2026, hecho a mano por Claude in Chrome):
Ver entradas → sector → tarifa con "+" → Continuar (boletas listadas) → Continuar →
garantía → Continuar → entrega → Confirmar reserva → pago ("La reserva expira en
~05:00"). Decisiones fijas del usuario: **nunca** Garantía Extendida (viene marcada de
fábrica y suma su línea al resumen; hay que pulsar "no gracias"), **siempre** "Boleto
Digital en la App" aunque haya otras entregas, y **parar antes de pagar**: el bot no
toca ningún medio de pago ni escribe datos de tarjeta.

- **Interfaz nueva del seguro** (Maná, 28-oct-2026; la reserva real de Platea C se quedó
  ahí con 1 boleta retenida, "pantalla desconocida"): tras las boletas listadas sale una
  sola pantalla con la entrega ya puesta ("Recibirás tus tickets en la app"; en el resumen,
  "Boleto Digital en la App (más seguro)") y el bloque "Seguro de devolución de entradas"
  con "Continuar sin seguro" y "Sumar seguro por $ …". El botón de abajo dice "Elige si
  quieres sumar el seguro" hasta elegir y luego "Continuar al pago" → medios de pago.
  `_hasta_pago()` pulsa siempre "Continuar sin seguro" antes de "Continuar al pago", y no
  sigue si el resumen no muestra la entrega de la app. Los pasos viejos (garantía con "no
  gracias", entrega, "Confirmar reserva") **se conservan**: no se sabe si todos los eventos
  cambiaron. Probado solo con página simulada.
  - Otra variante (Bunbury, misma tarde): "Si no puedes ir no podrás recuperar el valor de
    tus entradas" con "Sin protección" / "Proteger mis entradas", y "Continuar al pago" ya
    activo. No se pulsa nada del seguro: directo a "Continuar al pago".
  - La comprobación de entrega acepta "Boleto Digital en la App" o "Recibirás tus tickets en
    la app" (`ENTREGAS_APP`), sin distinguir espacios duros ni saltos de línea (`_contiene`),
    y espera unos segundos al resumen. La reserva real de Bunbury se paró ahí con 4 boletas
    retenidas ("el resumen no muestra…") aunque la captura lo mostraba; la causa exacta no se
    vio (sospecha: `\xa0`, que el pie de página sí traía). `fallo()` ahora corta el pie de
    página para que el Telegram muestre la pantalla.
- **"Continuar sin seguro" que no hace efecto** (Maná, Platea C, 16:05, 28-oct-2026, leído
  en vivo en la pestaña que quedó retenida): el texto del seguro **sí** estaba; el bot pulsó
  "Continuar sin seguro", la pantalla cambió sola (contador) y lo dio por hecho, pero el botón
  de abajo seguía en "Elige si quieres sumar el seguro" (`button#ck-confirm.ck-cta--disabled`,
  `aria-disabled="true"`). Ahora "sin seguro" solo cuenta cuando aparece "Continuar al pago";
  si no, se repite el clic. Los dos botones se pulsan primero por selector
  (`BOTONES_POR_SELECTOR`: `button.ck-panel__exit--skip`, `button#ck-confirm`) y si no, por
  texto. Al vencer, la pantalla muestra el diálogo "Se acabó el tiempo de reserva"
  (`.modal.ck-expired`), que es consecuencia, no causa. La sospecha de los espacios duros
  no era la causa aquí (falló igual con el arreglo puesto), pero el arreglo se queda.
- **El seguro que tarda en cargar** (Maná, Platea C, 16:27, 28-oct-2026): falló en 6 s,
  mientras Preferencial y Bunbury Platino (variante "Sin protección", con "Continuar al pago"
  ya a la vista) pasaban. En Platea C (platea numerada, asiento asignado, variante "Seguro de
  devolución" con el precio del seguro calculado) el resumen sale antes que el bloque del
  seguro; el bot veía una pantalla sin nada que reconocer, esperaba "a que cambiara algo", el
  contador lo cambiaba al instante y en ~2 s lo daba por atascado. Ahora, ante una pantalla
  desconocida, espera hasta `ESPERA_PASO` a una pantalla **conocida** (`_reconocida()`).
  Hipótesis por tiempos del registro, sin ver la pantalla en ese instante.
- **Espacios dobles en el nombre del sector** (Maná, "101 - 103 - 105 - 107  (Menores +12)",
  16:37, 28-oct-2026): el catálogo (`App`) trae el doble espacio y la lista en pantalla lo
  muestra con uno; `JS_ELEGIR_SECTOR` comparaba tal cual y falló con "el sector no aparece o
  no se pudo abrir". Ahora iguala los espacios. Verificado en vivo: abrió el sector y eligió
  la sección "101 (+12)" por la palabra "101".
- **Platea E de Maná** (16:3x, 28-oct-2026, `probar_reserva.py`): el "+" se frenó en 1 y
  "Buscar mejores asientos" dijo "No hay asientos libres para esta sección" ni para 1. El
  catálogo la daba disponible. No retuvo nada.
- **Espacios duros (`\xa0`)**: Ticketmaster los mete al azar en sus frases. Maná, misma
  pantalla del seguro: a las 15:40 fue bien y a las 15:52 "pantalla desconocida" con 1 boleta
  retenida. `PaginaSelenium.texto()` los cambia por espacios y `JS_CLIC_TEXTO` iguala los
  espacios antes de comparar; el seguro se reconoce por el título **o** por "Continuar sin
  seguro". Cualquier frase nueva que se busque debe pasar por `texto()`, no por
  `innerText` crudo.
- **Portada nueva con "Comprar entradas"** (Bunbury, 28-oct-2026, verificado en vivo):
  `button.pk-buy` despliega la tarjeta de la fecha con su "Ver entradas". `abrir_mapa()` lo
  pulsa solo si no hay ya "Ver entradas" ni "Seleccionar sector". Antes fallaba a los 15 s
  con "la pagina no mostro 'Ver entradas'".
- **Varias tarifas en un sector** (Maná, Preferencial, 28-oct-2026): "Entrada ET1 |
  Descuento Compensar" y "Entrada | Etapa 1". Cada una es una fila `.pk-rate.rateOption`
  con `aria-valuenow`, `.pk-rate-name` y su propio `button.plus`. El `JS_SUMAR` viejo (un
  solo "+", buscado subiendo desde el título) no encontraba nada y la reserva falló con "el
  selector no pasa de 0". Ahora `fijar_cantidad()` elige fila con `elegir_tarifa()` (la
  primera que no sea de descuento/convenio, `RE_TARIFA_RESTRINGIDA`) y usa su "+" y su
  contador; sin filas, sigue el formato viejo. Verificado en vivo hasta el "+" (marcó 2 en
  Etapa 1); el Continuar con dos tarifas aún no.
- **Cambiar los sectores de `RESERVAR_TICKETMASTER` no reprueba lo ya visto**: la clave
  `url@reserva||sector` se apunta para todos los disponibles en cuanto la URL está activada,
  casen o no. Con Maná se cambió "preferencial" por "platea c" y Platea C nunca se intentó.
  Hay que quitar su clave (monitor parado).
- El catálogo **no dice cuántas boletas quedan**: solo `lowAvailability` y `max: 4` en
  la tarifa (ningún sector de Vives tenía cupo bajo para probarlo).
- **Cuando no hay las pedidas** (verificado en vivo, Iron Maiden, sector 107, 1-oct-2026):
  el "+" **se frena en el máximo disponible** y la página muestra "Límite de cantidad —
  Has seleccionado el máximo disponible para esta tarifa". No hay rechazo al Continuar:
  al pedir 4 quedó en 2. `fijar_cantidad()` deja de pulsar al ver ese aviso (sin él
  esperaba 8 s por cada clic de más) y la reserva sigue con las que haya. La bajada
  4 → 3 → 2 → 1 con limpiar selección queda como respaldo por si Continuar rechazara
  (carrera con otro comprador); ese rechazo aún no se ha visto. Los intentos y el
  aviso quedan en `Reserva.intentos`, en el log y en el Telegram.
- **Localidades numeradas** (verificado en vivo con Iron Maiden, 1-oct-2026; el recorrido
  completo con el bot aún no se ha ejecutado):
  - El evento puede no tener "Ver entradas": la lista de sectores ya está a la vista.
  - Hay un paso **"Seleccionar sección"** (111, 113…): las filas libres son
    `div.sectionOption` (no `sectorOption`, que son las de sectores) y las agotadas
    `item-inactive`. Si una palabra de `RESERVAR_TICKETMASTER["sectores"]` nombra una
    sección ("107" dentro de "101 - 103 - 105 - 107"), solo se reserva esa; si está
    agotada no se reserva otra. Si ninguna palabra la nombra, vale la primera libre.
  - En este paso no hay "Continuar": el botón es **"Buscar mejores asientos"**, que
    asigna asientos juntos y deja las boletas listadas ("Cambiar tarifa"). Ahí **ya corre**
    "La reserva expira en": no sirve de señal de pago (por eso `RE_PAGO` no la usa).
  - Sin asientos: "Lo sentimos! No hay asientos libres para esta sección. elige otra
    sección." y "Limpiar selección" no hace nada; solo el enlace "elige otra sección"
    devuelve a los sectores.
  - El aviso "Límite de cantidad" es un **diálogo modal** (`.modal.in`) con su propio
    "Continuar" que solo lo cierra; hay que cerrarlo antes de seguir.
  - `RESERVAR_TICKETMASTER` (qué reservar) es independiente de `FILTROS_LOCALIDADES`
    (de qué avisar): la reserva mira **todos** los disponibles y lleva su propia
    deduplicación en `estado_notificaciones.json` (claves `url@reserva||sector`). Antes
    colgaba de los sectores ya filtrados para avisar y, con filtros distintos, nunca
    reservaba. Una sola URL puede llevar varias palabras, y **su orden es la prioridad**
    (la primera manda; a igual prioridad, el orden del catálogo).
  - Para reprobar con un sector ya visto hay que quitar de ese archivo su clave
    `url@reserva||sector` (no la de avisos).
- **Varias reservas a la vez** (verificado a mano por Aldemar, 1-oct-2026): Ticketmaster
  deja tener **varias reservas vivas en la misma cuenta**, una por pestaña, cada una con su
  contador, hasta la pantalla de pago (probó 3 localidades distintas). Por eso
  `"max_reservas": N` reserva una localidad por pestaña hasta N (BTS e Iron Maiden: 8);
  las fallidas no cuentan, con menos sectores que N se reservan los que haya, y el
  usuario decide cuál pagar (las demás vencen solas). **Cada sección libre de un sector
  numerado es una reserva distinta** (Calvin Harris: el sector "117-118-119-120" son 4
  secciones = 4 pestañas, no una): la pestaña toma la primera sección libre que no esté
  en `excluir_secciones`, y el bucle sigue con otra pestaña hasta que la página no tenga
  más (`Reserva.sin_mas_secciones`, que no es un fallo) o se llegue al tope
  (`MAX_INTENTOS_POR_SECTOR` = 12 como cota). Va en `_reservar_varias()`;
  sin `max_reservas` (=1) es una sola reserva. Cada localidad ya reservada tiene su propio
  enfriamiento de 10 min (`_RESERVADOS`) y todo el intento tiene un tope de
  `TIEMPO_MAXIMO_RESERVAS` (300 s): el monitor no revisa nada más mientras reserva.
- **Por qué a veces da 3 y no 4 (SIN RESOLVER)** (Calvin Harris, 2-oct-2026). Hechos:
  - Calvin **no valida la cantidad** (el "+" deja pedir 4 aunque haya menos; Iron Maiden sí
    se frena) y "Buscar mejores asientos" solo busca asientos **juntos**: si no hay N
    seguidos dice "No hay asientos libres", aunque haya sueltos. Con 1 sí hay mapa.
  - Dos veces seguidas el bot dio **4 + 3 + 3** y dejó la 118 como no disponible (`118:no`),
    aunque Aldemar ve 4 juntos en la 119 y la 120. A mano, con casi un minuto entre
    reservas, cada sección dio 4, también reservando antes la 117 y con otras reservas
    vivas en la misma sesión.
  - **Hipótesis descartadas** (todas contra la página real): pasarse del tope (el 5º clic;
    con `maximo 4` siguió igual), el orden (117 primero), que las reservas simultáneas se
    estorben, el ritmo (con `PAUSA_ENTRE_RESERVAS` = 5 s, ~10 s entre reservas, salió igual
    4+3+3) y que una reserva *confirmada* hasta el pago afecte a las siguientes (a mano:
    117 confirmada y luego 119 con 4 → dio 4, y la 118 seguía libre).
  - **Lo único que cambia es el navegador**: a mano, en el Comet de uso diario (con la
    extensión), todo da 4 y la 118 sale libre; en el Comet de reserva (perfil
    `C:\selenium\CometProfile`, controlado por Selenium) sale 4+3+3 y `118:no`, siempre igual
    (3 ejecuciones). Candidatos sin probar: detección de automatización (`navigator.webdriver`,
    depuración remota) con degradación de la disponibilidad, o una cuenta/perfil distintos.
    Prueba decisiva: hacer a mano, SIN el bot, las mismas reservas en la ventana del Comet de
    reserva. Si da 4+4+4 es la automatización; si da 4+3+3 es el perfil/cuenta.
  - El reintento "sin pasarse del tope" de `_reservar_sector()` nació de la hipótesis
    descartada; es inofensivo pero su motivo no se confirmó.
- **El mapa de asientos es un `<canvas>`** (los asientos no son elementos de la página;
  `window.seat` está vacío): completar a mano pulsando asientos exigiría calcular píxeles.
  Está descartado por ahora. Desde el mapa, pulsar una sección salta directo a la cantidad
  (se ahorran los dos pasos de la lista); no se ha automatizado.
- Hay **dos botones "Continuar"** en la pantalla de selección y uno no hace nada:
  de ahí el "primer clic perdido". Hay un único reintento de clic por pantalla, nunca
  una recarga. Además hay un "Continuar" de un diálogo oculto (cuenta creada).
- Garantía (verificado en vivo con la reserva real, 30-sep-2026): `ul.insurance-options
  > li`, la elegida lleva la clase `active` y su línea "GARANTIA EXTENDIDA" aparece en
  el resumen. "no gracias" **no es un elemento propio**, es un nodo de texto suelto
  junto a un `<strong>`: buscarlo por texto fallaba y la reserva se quedaba con 4
  boletas retenidas. Se hace clic en `.insurance-header` del `<li>` que lo contiene.
- Entrega: `<h2>` dentro de `li.delivery-select`; un clic en él avanza a la
  confirmación. "Confirmar reserva" es un único `<a class="btn btn-primary">`.
- Cancelar una prueba: "Cancelar compra" abre un diálogo y hay que pulsar "Aceptar".
  Hasta "Confirmar reserva" la página dice que las entradas "todavía no están
  reservadas".
- Con una pestaña en segundo plano (o ventana oculta) las capturas de pantalla de la
  extensión se cuelgan; `get_page_text` sigue funcionando.
- **Dónde se reserva**: en el equipo de Aldemar el Chrome del monitor (perfil
  `C:\selenium\ChromeProfile`) no carga el mapa ni deja iniciar sesión (Bitdefender);
  la primera prueba real falló ahí con "no se pudo abrir el mapa". Por eso
  `RESERVA_PUERTO_DEPURACION = 9223` apunta a un Comet aparte (`iniciar_comet_debug.bat`,
  perfil `C:\selenium\CometProfile`, sesión de Ticketmaster iniciada una vez a mano).
  El monitor sigue leyendo con su Chrome; solo la reserva usa Comet. `None` = reservar
  en una pestaña del Chrome del monitor.
- Comet trae su propio Chromium (153) y Selenium elige el chromedriver por el Chrome
  instalado (154): `_chromedriver_para()` busca en la caché de Selenium Manager el
  driver de la misma versión mayor. Si no hay, el aviso lo dice.
- El estado de avisos cuenta: la reserva solo se dispara con un sector **nuevo**. Para
  reprobar con un sector ya avisado hay que parar el monitor y quitar esa clave de
  `estado_notificaciones.json` (solo esa, no el archivo entero).
- **Verificado de punta a punta** (1-oct-2026, 4 VIP de Carlos Vives, disparado por el
  monitor en 5 s hasta el pago): mapa, sector, "+", garantía, entrega, confirmación y
  pago. Lo aprendido a golpes:
  - Los clics deben ser **nativos** (Selenium `element.click()`), no `.click()` de
    JavaScript: este no activa la opción de garantía. Si un elemento caduca
    (`StaleElementReferenceException`, la página se repinta sola) se vuelve a buscar.
  - La garantía puesta es la **línea suelta** `GARANTIA EXTENDIDA` del resumen; el
    enlace de términos también nombra "Garantía Extendida" y no cuenta.
  - Si el perfil ya trae un medio de pago elegido, la página salta directo a
    "Ingresa los datos de tu tarjeta" (sin lista de medios). El contador
    "La reserva expira en" solo aparece ya en la etapa de pago.
  - `probar_reserva.py` prueba la reserva sola, sin monitor ni estado de avisos.
- **Sin verificar en vivo**: el caso de menos de 4 boletas (la bajada 4→3→2→1 solo
  está probada con una página simulada) y el texto exacto del aviso de "no hay
  boletas".

## Navegadores: solo Comet, en dos instancias

Desde el 30-oct-2026 el bot no usa Google Chrome: Bitdefender lo detecta en el equipo de la
empresa de Aldemar. Donde este archivo habla del "Chrome del monitor" en hechos anteriores a esa
fecha, se refiere a aquel navegador.

- **Monitor**: puerto 9224, perfil `C:\selenium\CometMonitorProfile`
  (`PUERTO_DEPURACION`, `PERFIL_NAVEGADOR`). **Reserva**: puerto 9223, perfil
  `C:\selenium\CometProfile`. Son dos a propósito: relanzar el del monitor no se lleva por
  delante una reserva retenida, y el monitor no comparte ventana con las pestañas de reserva.
- No se reutiliza el 9222 del Chrome viejo: con uno de esos abierto, el monitor se engancharía
  a él sin que nadie lo notara.
- `_driver_en_puerto()` conecta los dos con el chromedriver de la versión de Comet. Comet se
  actualiza solo: si no hay driver de su versión mayor en caché, `_descargar_chromedriver()` lo
  baja con Selenium Manager (solo verificado con la 155, ya en caché).
- Lectura de prueba en el perfil nuevo, sin sesión (30-oct-2026): Tuboleta se lee bien sin
  iniciar sesión (Ryan Castro dio 3 disponibles y 5 agotadas, y en el Chrome viejo salía
  `LECTURA VACIA` en cada ronda). Cloudflare en Eleventickets pasó solo, pero la página cae en la
  portada "VENTA DE ENTRADAS EN BREVE" con "Iniciar Sesión" y no se ve el mapa (0 bloques), cuando
  el Chrome con sesión veía 2 + 88. Sospecha, sin comprobar: hace falta iniciar sesión también en
  este perfil. Hay que iniciarla a mano y comprobarlo antes de darlo por bueno.

## Eleventickets (Final Sudamericana): lo que ya se sabe

`reserva_eleventickets.py` añade al carrito hasta 4 entradas en el Comet de reserva y
**para ahí**: nunca entra al carrito ni al pago. Leído el 28-oct-2026 contra la página real.

- En el monitor: `verificar_disponibilidad_eleventickets()` lee los bloques del mapa (una
  carga por ronda, como siempre); disponibles = bloques **habilitados**, no bloques con cupo.
  `RESERVAR_ELEVENTICKETS` (URL → `maximo`, `sectores`) dispara
  `intentar_reserva_eleventickets()` cuando un bloque que casa aparece habilitado por primera
  vez (clave `url@reserva||bloque`); entonces prueba **todos** los habilitados que casan. Un
  bloque que sigue habilitado no se reintenta en cada ronda: vuelve a contar tras 3 lecturas
  sin verlo. `reservar_eleventickets.py` hace lo mismo a mano, una vez.
- El evento en `FILTROS_LOCALIDADES` lleva `["CAT2 - Oriental"]`: sin filtro avisaría de
  los 90 bloques.

- Cloudflare muestra "Un momento… Verificación de seguridad" a navegadores nuevos (el
  navegador integrado de Claude se quedó ahí). En el Comet de reserva pasó sola a las 13:05
  del 28-oct-2026, pero a las 14:36 (primer disparo real desde el monitor) se quedó parada
  30 s y la reserva falló con "el mapa no cargo": el permiso de Cloudflare caduca. Ahora
  `abrir()` la reconoce, espera `ESPERA_VERIFICACION` (45 s) por si pasa sola y, si no,
  deja la pestaña abierta (`conservar_pestana`, apuntada en `_PESTANA_VERIFICACION`) y lo
  dice en el Telegram: hay que pasarla a mano en el Comet. No se intenta saltarla. Luego,
  una vez por ronda, `reintentar_tras_verificacion()` **mira** esa pestaña (solo JS, sin
  recargar ni pedir nada): mientras siga la verificación no hace nada ni abre otra; en
  cuanto se ve el mapa, reserva ahí mismo (`PaginaSelenium(ya_cargada=True)`). Así el
  reintento no añade cargas y nunca llega antes de que el usuario haya pasado la verificación. El Chrome del monitor también la tuvo (dos
  lecturas vacías) y pasó sola. La extensión Claude in Chrome tiene **bloqueado por política** ejecutar JS y
  capturar en este sitio: se inspecciona con Selenium sobre el Comet de reserva.
- AngularJS + Leaflet. Cada sector es una capa SVG con `capa.dados` (`dscbloco` = nombre,
  `disabled` 1 = no pulsable, `m`). CAT2 - Oriental = 41 bloques (Tribuna Alta/Media/Baja,
  Sector 1-15). Al abrir la venta solo estaban habilitados Alta 5-9.
- `m >= 2`: productos (`.ingressos`, plantilla `Siwprodutoslistagem`), "+" =
  `button.botao-soma` (se deshabilita en `limite_prod`), "Agotado" =
  `span.ingresso-esgotado`, "Añadir al Carrito de Compras" = `button.botao-avancar`. El
  producto de CAT2 Oriental se llama "Público Colombiano". `m == 1` = asientos numerados
  (uno por clic); antes de abrir, los 90 bloques decían `m = "1"`, pero al abrir mostraron
  productos con "+".
- Reservar es `POST tickets/booking`, sin reCAPTCHA. Éxito: `$rootScope.qtdReserva` sube.
  Errores y diálogos son **ngDialog** (`.ngdialog-content`), no `md-dialog`: el primer
  intento real solo miraba `md-dialog` y dio "sin respuesta en 15s". El código 1111 hace que
  la página resuelva sola una prueba de trabajo (`$rootScope.powProcessing`) y repita la
  petición: se espera `ESPERA_COMPRA` (60 s). Una respuesta de fila recarga la página.
- **El "+" no dice cuántas quedan**: deja subir a 4 aunque haya menos, y al añadir el
  servidor contesta "¡El producto está agotado!" (diálogo "Atención", visto por Aldemar,
  28-oct-2026, pidiendo 2). Por eso, ante un rechazo de cupo (`RE_SIN_CUPO`) se repite en el
  mismo bloque con una menos (4 → 3 → 2 → 1) y luego se pasa al siguiente; sin respuesta o
  con la página recargada no se insiste. La cantidad rechazada sigue marcada: se baja con
  `button.botao-subtracao`. El bot no reintenta ni espera a que se libere cupo: una pasada.
- Comprobar el carrito del servidor (solo lectura):
  `Common.ajaxmg('SuperIngressoWeb', 'getCarrinhoQtdReservados', [])`.
- **Entre ventas el evento se cierra** (30-oct-2026, 11:20, antes de la venta de las 12): el
  enlace de la venta anterior responde "Presentación bloqueada" (ngDialog, sin mapa) y la home
  dice "VENTA DE ENTRADAS EN BREVE", sin enlaces. La sesión también había caducado. Con el
  evento bloqueado, el lector mira la home (`_buscar_evento_en_home`) y, si publica otro
  enlace, lo lee con la misma configuración (`_config_eleventickets`); si deja de decir "en
  breve" sin enlace reconocible, avisa con `[SIN DETALLE]`. El enlace de la home con la venta
  abierta aún no se ha visto: su lectura (`JS_EVENTOS_HOME`) sale del código de la página.
- **Excepción pedida por Aldemar para esa venta**: `"reintentar_siempre": True` intenta añadir
  en **cada ronda** mientras haya un bloque habilitado que case. Tras un éxito sigue el freno de
  10 min (`_ULTIMA_RESERVA`), salvo con `"completar": True`; los Telegram de fallo salen como
  mucho cada 10 min. Además, las demás URLs quedaron comentadas con `#TEMP `. Ambas cosas
  **suben la huella de peticiones** a Eleventickets y deben revertirse al acabar la venta.
- **`"completar": True`** (misma venta, "4 sí o sí"): sin freno tras un éxito ni
  `PAUSA_TRAS_DISPONIBILIDAD`; cada intento pregunta al servidor cuánto hay en el carrito
  (`en_carrito()`) y sigue por los demás bloques hasta llegar a `maximo`, aunque queden en
  sectores distintos. La cuenta en memoria (`_ENTRADAS_CONSEGUIDAS`) lo detiene al llegar y no
  baja si una reserva vence: una entrada pagada sale del carrito y, mirando solo el carrito,
  compraría otras 4. Reiniciar el monitor la pone a cero. Un segundo "Añadir" en la misma
  cuenta aún no se ha visto en vivo.
- **El tope de 4 cuenta lo pagado** (30-oct-2026): con 4 CAT2 pagadas en la cuenta, el carrito
  da 0 y cada asiento responde "Se ha excedido el número límite de entradas por persona (4)".
  `RE_LIMITE_CUENTA` detiene el intento (`completo`). Occidental son asientos numerados (`m=1`,
  sectores 313-315) y Oriental, productos con cantidad; los bloques cambian entre ventas.
- **Varios bloques numerados en una página** (30-oct-2026): al acercarse a uno, el mapa quita a
  los vecinos de las capas visibles y carga sus asientos, así que buscar el bloque con
  `eachLayer` daba "no se abrio" en 0,0 s (el 315 y el 314 no se revisaban). `JS_PULSAR_BLOQUE`
  mira también `g_mapa_groupBlocos`, con los 90, y usa `setView` sin animación en vez de
  `fitBounds`. Verificado en vivo: 313, 315 y 314 abren seguidos. Estados de asiento: `L` libre,
  `R` reservado, `O` ocupado, `B` bloqueado; no traen hora de vencimiento. Un asiento recién
  liberado se va en segundos: G-015 ya contestó "Assento reservado" (ngDialog) al pulsarlo.
- **Sin verificar**: un "Añadir" que funcione (los dos intentos del 28-oct-2026 no dejaron
  nada en el carrito y no se vio por qué) y el flujo de asientos numerados.
- Comet se actualizó a 155: hizo falta bajar chromedriver 155 con Selenium Manager
  (`selenium-manager.exe --driver chromedriver --browser-version 155`). Sin él falla también
  la reserva de Ticketmaster.

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
- El selector específico tiene que usar `By.CLASS_NAME` (coincidencia por token
  exacto), nunca un XPath `contains(@class, 'ticket-list-box')` (substring): el
  contenedor que envuelve los tres sectores se llama `ticket-list-boxes`, PLURAL, y
  ese `contains()` también lo capta. Como el contenedor va primero en el DOM, se le
  asignaba el nombre del primer sector (siempre GREEN PRINT en Feid, por ser el
  primer `.sector_name` en su subárbol) pero `is_displayed()` se evaluaba sobre el
  contenedor — visible mientras exista *cualquier* sector visible, no sobre la caja
  real de ese sector. Resultado: el primer sector salía "disponible" de forma
  persistente (no era un parpadeo, pasaba en cada lectura) aunque su caja real
  estuviera oculta, y para cuando el barrido llegaba a su caja real el nombre ya
  estaba deduplicado. Reportado por el usuario tras más de un día de falsos avisos
  de GREEN PRINT en dos máquinas distintas; reproducido y corregido sep-2026.

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
