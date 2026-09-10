# Monitor de disponibilidad de boletas

Monitor automatizado que revisa en bucle una lista de URLs de venta y reventa de
boletas, detecta cuándo aparecen localidades disponibles y avisa por **Telegram**.

> **Estado:** prototipo funcional en refactorización. Ver
> [Limitaciones conocidas](#limitaciones-conocidas) antes de confiar en él a ciegas.

---

## Qué hace

- Revisa en bucle infinito las URLs definidas en `URLS_A_MONITOREAR`.
- Detecta la plataforma de cada URL y aplica el método de lectura que le corresponde.
- Filtra las localidades encontradas por palabras clave, definidas por URL en
  `FILTROS_LOCALIDADES` (por ejemplo, avisar solo de `TRIBUNA` y `PLATEA`).
- Envía un mensaje de Telegram cuando hay disponibilidad que coincide con el filtro.
- Te avisa también si una boletera responde con una verificación anti-bot (el
  monitor no puede leer ese sitio mientras dure) o con una sala de espera (la venta
  abrió y hay fila).
- Se conecta a una ventana de Chrome **que ya tienes abierta y con sesión iniciada**,
  en lugar de abrir un navegador nuevo. Esto reutiliza tus cookies y reduce mucho la
  probabilidad de que las plataformas detecten la automatización.

## Qué NO hace

- **No compra boletas.** No selecciona asientos, no agrega al carrito y no paga.
  Solo observa y avisa; la compra la haces tú, a mano, en **otra pestaña** de la
  ventana de Chrome del monitor. La pestaña que usa el bot cambia de página en cada
  consulta, así que si compras en ella te la quitará de las manos.
- No inicia sesión por ti. Debes estar logueado previamente en el perfil de Chrome
  que usa el monitor.
- No envía WhatsApp. Ese canal existió (vía CallMeBot) y se retiró; el único canal
  de notificación es Telegram.

## Plataformas soportadas

| URL | Qué revisa |
|---|---|
| `*.checkout.tuboleta.com` (tuboletapass, breakfast, tbpgpal, ...) | Filas de localidades que no estén marcadas como "Agotado" |
| `pasala.checkout.tuboleta.com` (reventa) | Casillas de categoría (`seat-cat-checkbox`) que aparezcan activas |
| `www.ticketmaster.co` | Catálogo de sectores que publica la propia página, con los disponibles y los agotados. No necesita pulsar "Ver entradas" |
| `www.taquillalive.com/performance-details` | Presencia del botón "Compra Tus Tiquetes" |
| `www.taquillalive.com/book-performance` | Sectores listados en el panel de compra |

## Requisitos

- Python 3.10 o superior (probado con 3.12)
- Google Chrome instalado
- Un bot de Telegram propio (lo creas con [@BotFather](https://t.me/BotFather))
- Cuenta ya registrada en las plataformas que vayas a monitorear

## Instalación

```bash
git clone https://github.com/boleteriaald/bot_boleteria_ald.git
cd bot_boleteria_ald
python -m venv .venv
source .venv/Scripts/activate    # Git Bash en Windows
pip install -r requirements.txt
```

## Configuración

### 1. Credenciales

Crea un archivo `config.py` en la raíz del proyecto con dos valores:

```python
TELEGRAM_BOT_TOKEN = "el token que te entrega @BotFather"
TELEGRAM_CHAT_ID = "tu ID de usuario, que te da @userinfobot"
```

Escríbele al menos una vez a tu bot desde Telegram antes de usarlo; si no, no puede
enviarte mensajes.

### 2. URLs a monitorear

Se editan directamente en el script, en la lista `URLS_A_MONITOREAR`:

```python
URLS_A_MONITOREAR = [
    "https://www.ticketmaster.co/event/nombre-del-evento",
    "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=...",
]
```

### 3. Filtros por localidad

En el diccionario `FILTROS_LOCALIDADES`, la clave es la URL y el valor es la lista de
palabras clave que te interesan:

```python
FILTROS_LOCALIDADES = {
    "https://...la-misma-url-exacta...": ["TRIBUNA", "PLATEA", "307"],
}
```

Reglas del filtro:

- La coincidencia es **parcial**: `"platea"` encuentra `"PLATEA ORIENTAL 2"`.
- Se ignoran mayúsculas, tildes, espacios repetidos y separadores (`-`, `,`, `/`):
  `"PLATEA E PARES"` encuentra `"Platea E  Pares"`, y `"110, 112"` encuentra
  `"110 - 112 - 114"`. Los nombres los escribe a mano cada boletera y no son
  consistentes, así que esto evita fallos silenciosos.
- Usa la palabra más corta que identifique la localidad (`PLATEA A`, `PREFERENCIAL`,
  `119`). No copies el nombre completo de la página informativa del evento: en la
  de venta suele cambiar (los rangos se parten, se añaden sufijos de edad).
- Ojo con los nombres contenidos en otros: `NORTE BAJA` también encuentra
  `ORIENTAL NORTE BAJA`. Y con los números cortos: `11` encuentra `110`, `111`…
- La URL debe ser **idéntica** a la de `URLS_A_MONITOREAR`, carácter por carácter.
  Si no coincide, el filtro se ignora en silencio.
- Una URL **sin** filtro definido notifica **cualquier** disponibilidad.

## Uso

**Paso 1** — Abre Chrome en modo debugging (esto abre una ventana aparte, con un
perfil propio en `C:\selenium\ChromeProfile`):

```bash
./iniciar_chrome_debug.bat
```

**Paso 2** — En esa ventana, inicia sesión en las plataformas que vayas a monitorear.
Solo hace falta la primera vez; el perfil conserva la sesión.

**Paso 3** — Con esa ventana abierta, lanza el monitor:

```bash
python "main13_filters_all_urls lina.py"
```

El script imprime el progreso en consola y no se detiene solo: córtalo con `Ctrl+C`.
No cierres la ventana de Chrome mientras corre.

## Cómo funciona por dentro

```
iniciar_chrome_debug.bat
        │  abre Chrome con --remote-debugging-port=9222
        ▼
conectar_chrome()  ──► Selenium se ancla a esa ventana (no abre una nueva)
        │
        ▼
monitorear_urls()  ──► bucle infinito
        │
        ├─ para cada URL: detecta la plataforma y la lee
        │        (contar_localidades_disponibles / contar_articulos_pasala /
        │         verificar_disponibilidad_ticketmaster / ..._taquillalive_*)
        │
        ├─ filtrar_localidades()  ──► aplica las palabras clave de esa URL
        │
        └─ si queda algo: enviar_telegram()
```

## Notificaciones: cuándo avisa y cuándo calla

El monitor recuerda de qué ya te avisó, así que **no repite el mismo mensaje en cada
vuelta del bucle**. Una localidad genera aviso cuando:

1. **Aparece por primera vez** — la transición de agotado a disponible, que es lo que
   de verdad importa.
2. **Sigue disponible y han pasado 10 minutos** desde el último aviso. Es un
   recordatorio, marcado como tal en el mensaje, por si no viste el primero.

El registro es **por localidad individual**, no por URL: si ya te avisó de `PLATEA 307`
y luego aparece `TRIBUNA 202`, la segunda también genera aviso.

**Tolerancia a lecturas fallidas.** Si una página carga lenta, la lectura puede salir
vacía aunque las boletas sigan ahí. Para que ese parpadeo no dispare un aviso nuevo al
ciclo siguiente, una localidad no se da por agotada hasta **tres lecturas consecutivas**
sin verla.

**Si Telegram falla**, el aviso no se da por enviado: se reintenta en la ronda
siguiente en lugar de esperar al recordatorio de 10 minutos. Lo mismo con los avisos
de bloqueo. En el registro queda como `AVISO NO ENVIADO, se reintentara`.

El estado vive en `estado_notificaciones.json` (excluido de git) y sobrevive a los
reinicios: si cortas el script y lo relanzas, no te bombardea con lo que ya sabías.

Para ajustar el comportamiento, en la cabecera del script:

```python
INTERVALO_RECORDATORIO = 600        # Segundos entre recordatorios
LECTURAS_VACIAS_PARA_OLVIDAR = 3    # Lecturas en vacío antes de dar algo por agotado
```

Si quieres empezar de cero (por ejemplo, para forzar que te vuelva a avisar de todo),
basta con borrar el archivo de estado:

```bash
rm estado_notificaciones.json
```

## Registro de lo que hace

Además de la consola, el monitor escribe en `logs/monitor.log` (excluido de git):

- una línea por ronda y otra por URL, con cuántas localidades leyó disponibles,
  agotadas y filtradas;
- cada aviso enviado y, sobre todo, **los que no se pudieron enviar**;
- bloqueos anti-bot, salas de espera y cargas de página que se agotaron;
- cada error, con su traza completa.

El archivo rota al llegar a 5 MB y conserva los 5 anteriores (unos 25 MB en total,
alrededor de una semana de funcionamiento continuo).

La marca que conviene vigilar es `LECTURA VACIA`: la URL no devolvió ni disponibles
ni agotadas. Puede ser un evento sin nada que mostrar, pero si una URL la repite
ronda tras ronda, lo normal es que su lectura se haya roto.

Para verlo en vivo desde PowerShell:

```powershell
Get-Content logs\monitor.log -Tail 40 -Wait
```

Y para quedarte solo con lo importante:

```powershell
Select-String -Path logs\monitor.log -Pattern "ERROR|WARNING|AVISO|LECTURA VACIA"
```

## Limitaciones conocidas

Documentadas a propósito, para que no sorprendan:

- **Ticketmaster con sala de espera.** Si un evento abre con cola virtual, el bot te
  avisa de que la venta abrió, pero no puede decirte qué localidades hay hasta que
  pase la cola.
- **Ticketmaster puede cambiar su estructura interna.** El detalle por localidad
  depende de cómo organiza los datos de su página. Si lo cambia, el bot pasa a un
  modo sin detalle: avisa "venta abierta [SIN DETALLE]" saltándose los filtros, en
  vez de quedarse callado.
- **Falsos positivos.** La lectura de Tuboleta y TaquillaLive se apoya en selectores
  genéricos (`div` con clase `row`) y en la ausencia de la palabra "Agotado". Puede
  contar como localidad algo que no lo es.
- **Sin reconexión.** Si cierras Chrome o se cae la sesión, el bucle sigue girando y
  registrando errores en vez de reconectar.
- **Configuración a mano.** `URLS_A_MONITOREAR` y `FILTROS_LOCALIDADES` son dos listas
  separadas dentro del código; es fácil que se desincronicen.

## Seguridad

- `config.py` **nunca** debe subirse al repositorio. Ya está en `.gitignore`; revisa
  con `git status` antes de cada commit.
- Este es un repositorio **público**: una credencial subida por error queda indexada
  y es recogida por bots en minutos. Si pasa, rota el token de inmediato.
- El monitor no necesita —ni usa— las contraseñas de las plataformas: la sesión vive
  en el perfil de Chrome.

## Aviso

Herramienta de uso personal. Automatizar la consulta de estos sitios puede ir en
contra de sus términos de servicio; úsala con moderación y bajo tu responsabilidad.
