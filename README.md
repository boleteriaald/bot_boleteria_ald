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
- Se conecta a una ventana de Chrome **que ya tienes abierta y con sesión iniciada**,
  en lugar de abrir un navegador nuevo. Esto reutiliza tus cookies y reduce mucho la
  probabilidad de que las plataformas detecten la automatización.

## Qué NO hace

- **No compra boletas.** No selecciona asientos, no agrega al carrito y no paga.
  Solo observa y avisa; la compra la haces tú, a mano, en la ventana de Chrome que
  ya está abierta.
- No inicia sesión por ti. Debes estar logueado previamente en el perfil de Chrome
  que usa el monitor.
- No envía WhatsApp. Ese canal existió (vía CallMeBot) y hoy está desactivado; el
  código quedó comentado en el script.

## Plataformas soportadas

| URL | Qué revisa |
|---|---|
| `*.checkout.tuboleta.com` (tuboletapass, breakfast, tbpgpal, ...) | Filas de localidades que no estén marcadas como "Agotado" |
| `pasala.checkout.tuboleta.com` (reventa) | Casillas de categoría (`seat-cat-checkbox`) que aparezcan activas |
| `www.ticketmaster.co` | Presencia del botón "Ver entradas" |
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

El archivo `config.py` **no está en el repositorio** (contiene secretos y está
excluido en `.gitignore`). Créalo a partir de la plantilla:

```bash
cp config.example.py config.py
```

Luego edítalo y rellena:

- `TELEGRAM_BOT_TOKEN` — el token que te entrega @BotFather
- `TELEGRAM_CHAT_ID` — tu ID de usuario, que te da [@userinfobot](https://t.me/userinfobot)

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

- La coincidencia es **parcial y sin distinguir mayúsculas**: `"platea"` encuentra
  `"PLATEA ORIENTAL 2"`.
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

## Limitaciones conocidas

Documentadas a propósito, para que no sorprendan:

- **Notificaciones repetidas.** No hay memoria de estado: mientras una localidad siga
  disponible, se envía un mensaje en cada vuelta del bucle. Con varios eventos activos
  esto satura el chat y puede chocar con los límites de Telegram.
- **Ticketmaster reporta el evento, no la localidad.** Solo comprueba si existe el
  botón "Ver entradas", así que devuelve el nombre del evento. En consecuencia, los
  filtros por localidad **no funcionan** en URLs de Ticketmaster.
- **Falsos positivos.** La lectura de Tuboleta y TaquillaLive se apoya en selectores
  genéricos (`div` con clase `row`) y en la ausencia de la palabra "Agotado". Puede
  contar como localidad algo que no lo es.
- **Sin reconexión.** Si cierras Chrome o se cae la sesión, el bucle sigue girando y
  registrando errores en vez de reconectar.
- **Solo consola.** No hay registro en archivo, así que tras una noche corriendo no
  queda rastro de lo ocurrido.
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
