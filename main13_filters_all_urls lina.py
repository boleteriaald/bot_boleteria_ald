import asyncio
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from telegram import Bot
from telegram.error import TelegramError

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

URLS_A_MONITOREAR = [

    # BTS
    "https://www.ticketmaster.co/event/bts-world-tour-venta-general-viernes-2-octubre",
    "https://www.ticketmaster.co/event/bts-world-tour-venta-general-sabado-3-octubre",

    # # TINI TUBOLETA
    # "https://tbpgpal.checkout.tuboleta.com/selection/event/seat?perfId=10230464800095&table=1&productId=10230464799993",
    "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230464800095&table=1&productId=10230464799993",
    #
    # # TINI FANS
    # "https://tuboletapass4.checkout.tuboleta.com/selection/event/seat?perfId=10230464800095&table=1&advantageId=10230464775047&productId=10230464799993",

    # KAROL G DEL 4
    "https://www.ticketmaster.co/event/karol-g-viajando-por-el-mundo-tropitour-venta-general",
    # KAROL G DEL 5
    "https://www.ticketmaster.co/event/karol-g-viajando-por-el-mundo-tropitour-venta-general-segunda-fecha#",
    # KAROL G DEL 6
    "https://www.ticketmaster.co/event/karol-g-viajando-por-el-mundo-tropitour-venta-general-tercera-fech#",

    # ROBBIE WILLIAMS
    # "https://tuboletapass.checkout.tuboleta.com/selection/event/date?productId=10230355790289",
    "https://tuboletapass.checkout.tuboleta.com/selection/event/seat?perfId=10230355790391&table=1&productId=10230355790289",
    "https://pasala.checkout.tuboleta.com/selection/resale/item?performanceId=10230355790391",

    # CAMILO
    # "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230441698792&table=1&productId=10230441698670",

    # WWE
    # "https://tuboletapass4.checkout.tuboleta.com/selection/event/seat?perfId=10230449577695&table=1&productId=10230440869582",
    # "https://tuboletapass4.checkout.tuboleta.com/selection/event/date?productId=10230440869582"

    # KRIS R FUNCIONAL
    # "https://breakfast.checkout.tuboleta.com/selection/event/date?productId=10230387611599",
    "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230398494504&table=1&productId=10230387611599",

    # LOS CALIGARIS
    "https://tuboletapass4.checkout.tuboleta.com/selection/event/seat?perfId=10230442113890&table=1&productId=10230442107826",

    # OMAR COURTZ
    "https://tbpgpal.checkout.tuboleta.com/selection/event/seat?perfId=10230524219204&productId=10230523214255",

    # "https://tbpgpal.checkout.tuboleta.com/selection/event/date?productId=10230387611599", #KRIS R LOCALIDAD FALLA
    # "https://tbpgpal.checkout.tuboleta.com/selection/event/seat?perfId=10230398494504&table=1&productId=10230387611599",
    # "https://www.ticketmaster.co/event/grupo-firme-la-ultima-peda-pereira-venta-general",
    # "https://www.ticketmaster.co/event/la-vela-puerca",
    # "https://www.ticketmaster.co/event/arcangel-venta-general-nueva-fecha",
    "https://www.ticketmaster.co/event/arcangel-venta-general",
    # "https://www.taquillalive.com/performance-details/?artist=julion-alvarez&event=TCL.EVN1086.PRF1",
    # "https://www.taquillalive.com/performance-details/?artist=la-pestilencia&event=TCL.EVN1154.PRF1",
    # "https://www.taquillalive.com/performance-details/?artist=maroon-5&event=TCL.EVN1153.PRF1",
    # "https://www.taquillalive.com/book-performance/?artist=maroon-5&event=TCL.EVN1153.PRF1",
    # "https://www.taquillalive.com/book-performance/?artist=korn&event=TCL.EVN1034.PRF1",

    # LENNY TAVAREZ Y J QUILES
    # "https://breakfast.checkout.tuboleta.com/selection/event/date?productId=10230492501166",
    # "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230492501275&table=1&productId=10230492501166",

    # LENNY PREVENTA
    # "https://movistarpref.checkout.tuboleta.com/selection/event/seat?perfId=10230492501275&advantageId=10230492613983&productId=10230492501166",
    # "https://movistarpref.checkout.tuboleta.com/selection/event/seat?perfId=10230492501275&table=1&advantageId=10230492613983&productId=10230492501166",

    # DEFF LEPARD
    "https://tbpgpal.checkout.tuboleta.com/selection/event/seat?perfId=10230485786391&table=1&productId=10230485782854",

    # GORILLAZ    
    "https://www.taquillalive.com/performance-details/?artist=gorillaz&event=TCL.EVN1152.PRF1",
    "https://www.taquillalive.com/book-performance/?artist=gorillaz&event=TCL.EVN1152.PRF1",

    # ALVARO DIAZ FECHA 1 - 3 SEP
    # "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230492501277&table=1&productId=10230492501167"

    # ALVARO DIAZ PÁSALA
    # "https://pasala.checkout.tuboleta.com/selection/resale/item?performanceId=10230492501277",

    # JORGE DREXLER
    # "https://tuboletapass.checkout.tuboleta.com/selection/event/seat?perfId=10230398494507&table=1&productId=10230387611601",

    # RYAN CALI
    # "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230493240095&table=1&productId=10230493153527",

    # RYAN BOGOTÁ
    # "https://breakfast.checkout.tuboleta.com/selection/event/date?productId=10230451310131&_gl=1*4qwrrk*_gcl_au*MTI4ODU1NzA0Ni4xNzc2NjIyOTk5Ljc2MjAzMjQ3NC4xNzgzNTcwNzY2LjE3ODM1NzA3NjY.*_ga*MTk0NDE0NzkuMTc3NjYyMjk5OQ..*_ga_0TVTJ30NVQ*czE3ODM1NjQ3MDEkbzMkZzEkdDE3ODM1NzE2MjYkajUxJGwwJGgxMTI3OTc4Mzc3",
    # "https://breakfast.checkout.tuboleta.com/selection/event/date?productId=10230451310131",
    "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230451311545&table=1&productId=10230451310131",

]

# ============================================================
# CONFIGURACIÓN DE FILTROS POR URL
# ============================================================
# Define qué localidades quieres monitorear para cada URL
# Si la URL no está en el diccionario, se monitorean TODAS las localidades
# Si está en el diccionario, solo se notificará si coincide con una de las localidades

FILTROS_LOCALIDADES = {

    # OMAR COURTZ
    "https://tbpgpal.checkout.tuboleta.com/selection/event/seat?perfId=10230524219204&productId=10230523214255":
        ["TRIBUNA", "PLATEA", ],

    # ROBBIE WILLIAMS
    # "https://tuboletapass.checkout.tuboleta.com/selection/event/date?productId=10230355790289":
    "https://tuboletapass.checkout.tuboleta.com/selection/event/seat?perfId=10230355790391&table=1&productId=10230355790289":
        ["302", "307",
         # "202", "207",
         "PLATEA", "TRIBUNA"],

    # KRIS R FUNCIONAL
    # "https://breakfast.checkout.tuboleta.com/selection/event/date?productId=10230387611599",
    "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230398494504&table=1&productId=10230387611599":
        ["TRIBUNA", "PLATEA",
         "202", "206", "208", "302", "304", "305", "307"],

    # RYAN BOGOTÁ
    "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230451311545&table=1&productId=10230451310131":
        ["VIP", "OCCIDENTAL ALTA", "ORIENTAL BAJA", "ORIENTAL ALTA", "SUR ALTA", "NORTE ALTA"],

    # RYAN CALI
    # "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230493240095&table=1&productId=10230493153527":
    #     [
    #         "VIP OCCIDENTAL SANKA",
    #         "VIP ORIENTAL SANKA",
    #         "OCCIDENTAL 1ER PISO",
    #         "OCCIDENTAL 2DO PISO",
    #         "OCCIDENTAL 3ER PISO",
    #         "ORIENTAL 1ER PISO",
    #         "ORIENTAL 2DO PISO"],

    # CALVIN HARIS
    "https://www.ticketmaster.co/event/calvin-harris-venta-general":
        ["PLATEA 1", "PLATEA 2", "119"],

    # GORILLAZ
    "https://www.taquillalive.com/performance-details/?artist=gorillaz&event=TCL.EVN1152.PRF1":
        ["PLATEA 2"],

    "https://www.taquillalive.com/book-performance/?artist=gorillaz&event=TCL.EVN1152.PRF1":
        ["PLATEA 2"],

    # JORGE DREXLER
    # "https://tuboletapass.checkout.tuboleta.com/selection/event/seat?perfId=10230398494507&table=1&productId=10230387611601":
    #     ["TRIBUNA"],

    # TINI TUBOLETA
    "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230464800095&table=1&productId=10230464799993":
        ["TRIBUNA"],

    # TINI FANS
    # "https://tuboletapass4.checkout.tuboleta.com/selection/event/seat?perfId=10230464800095&table=1&advantageId=10230464775047&productId=10230464799993":
    #   ["TRIBUNA", "PLATEA"],

    # # MAROON5
    # "https://www.taquillalive.com/book-performance/?artist=maroon-5&event=TCL.EVN1153.PRF1":
    #     ["PAQUETE", "PLATEA"],

    # ROBBIE WILLIAMS
    "https://pasala.checkout.tuboleta.com/selection/resale/item?performanceId=10230355790391":
        ["307",
         # "302",
         # "202",
         "207",
         "PLATEA", "TRIBUNA"],

    # LOS CALIGARIS
    "https://tuboletapass4.checkout.tuboleta.com/selection/event/seat?perfId=10230442113890&table=1&productId=10230442107826":
        ["TRIBUNA", "PLATEA"],

    # DEFF LEPARD
    "https://tbpgpal.checkout.tuboleta.com/selection/event/seat?perfId=10230485786391&table=1&productId=10230485782854":
        ["PISO 3"],

    # CAMILO
    # "https://breakfast.checkout.tuboleta.com/selection/event/seat?perfId=10230441698792&table=1&productId=10230441698670":
    # # ["TRIBUNA", "PRIMERAS"],
    #     ["PRIMERAS"],

}


async def enviar_telegram(mensaje):
    """Envía un mensaje por Telegram (SIN LÍMITES)"""
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)

        print(f"   📤 Enviando a Telegram Chat ID: {TELEGRAM_CHAT_ID}")

        # Limpieza básica del mensaje
        mensaje_limpio = mensaje.replace('[', '(').replace(']', ')')

        # Enviar mensaje
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=mensaje_limpio,
            parse_mode='HTML'  # Permite formato HTML
        )

        print(f"✓ Telegram enviado exitosamente")
        return True

    except TelegramError as e:
        print(f"✗ Error de Telegram: {e}")
        return False
    except Exception as e:
        print(f"✗ Error al enviar Telegram: {e}")
        return False


def enviar_whatsapp(mensaje):
    """Envía mensaje por Telegram (función wrapper para compatibilidad)"""
    try:
        # Ejecutar función async
        asyncio.run(enviar_telegram(mensaje))
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


# def enviar_whatsapp(mensaje):
#     """Envía un mensaje por WhatsApp usando CallMeBot con encoding correcto"""
#     try:
#         # ✅ IMPORTANTE: Eliminar caracteres especiales problemáticos del mensaje
#         # Reemplazar los corchetes por paréntesis que son más seguros
#         mensaje_limpio = mensaje.replace('[', '(').replace(']', ')')
#
#         # ✅ Codificar el mensaje para URL
#         mensaje_codificado = urllib.parse.quote(mensaje_limpio)
#
#         url = f"https://api.callmebot.com/whatsapp.php?phone={WHATSAPP_PHONE}&text={mensaje_codificado}&apikey={WHATSAPP_APIKEY}"
#
#         print(f"   📤 Enviando a: {WHATSAPP_PHONE}")
#         print(f"   📊 Longitud (limpio): {len(mensaje_limpio)} caracteres")
#
#         response = requests.get(url, timeout=10)
#
#         if response.status_code == 200:
#             print(f"✓ WhatsApp enviado exitosamente: {response.status_code}")
#             return True
#         elif response.status_code == 210 or response.status_code == 201:
#             print(f"⚠️ WhatsApp - Error/Cola (código {response.status_code})")
#             print(f"   ℹ️ El mensaje fue enviado pero quedó en cola (hasta 16 mensajes cada 240 minutos)")
#             # Contar como éxito porque está en la cola
#             return True
#         else:
#             print(f"⚠️ WhatsApp - Código inesperado ({response.status_code})")
#             return False
#
#     except requests.exceptions.Timeout:
#         print(f"✗ Error: Timeout al enviar WhatsApp (>10 segundos)")
#         return False
#     except Exception as e:
#         print(f"✗ Error al enviar WhatsApp: {e}")
#         return False


def conectar_chrome():
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        intentos = 0
        max_intentos = 10
        while intentos < max_intentos:
            try:
                driver = webdriver.Chrome(options=chrome_options)
                print("✓ Conectado a Chrome")
                return driver
            except Exception as e:
                intentos += 1
                if intentos < max_intentos:
                    print(f"⏳ Esperando a que Chrome se inicie... (intento {intentos}/{max_intentos})")
                    time.sleep(2)
                else:
                    raise e
    except Exception as e:
        print(f"✗ Error al conectar a Chrome: {e}")
        print("\nAsegúrate de haber ejecutado: iniciar_chrome_debug.bat")
        return None


def es_url_pasala(url):
    return "pasala.checkout.tuboleta.com" in url


def es_url_tbpgpal(url):
    return "tbpgpal.checkout.tuboleta.com" in url


def es_url_ticketmaster(url):
    """Detecta si la URL es de Ticketmaster.co"""
    return "ticketmaster.co" in url


def es_url_taquillalive(url):
    """Detecta si la URL es de TaquillalLive"""
    return "taquillalive.com" in url


def es_url_taquillalive_performance_details(url):
    """Detecta si es la página de detalles del evento"""
    return "taquillalive.com" in url and "performance-details" in url


def es_url_taquillalive_book(url):
    """Detecta si es la página de compra de entradas"""
    return "taquillalive.com" in url and "book-performance" in url


def verificar_disponibilidad_ticketmaster(driver, url):
    """
    Verifica disponibilidad en Ticketmaster
    Busca el botón "Ver entradas" que indica disponibilidad
    """
    try:
        print(f"\n→ Navegando a Ticketmaster: {url}")
        driver.get(url)
        time.sleep(3)

        # Obtener nombre del evento
        nombre_evento = None
        try:
            # Intentar obtener el nombre del evento
            nombre_evento = driver.find_element(By.XPATH, "//h1 | //h2[contains(@class, 'event')]").text.strip()
        except:
            try:
                # Alternativa: obtener del title
                nombre_evento = driver.title.split('|')[0].strip()
            except:
                nombre_evento = "Evento Ticketmaster"

        print(f"   Evento: {nombre_evento}")

        # ✅ Buscar el botón "Ver entradas"
        try:
            boton_ver_entradas = driver.find_element(By.XPATH,
                                                     "//button[contains(text(), 'Ver entradas')] | "
                                                     "//a[contains(text(), 'Ver entradas')] | "
                                                     "//button[contains(text(), 'BUY')] | "
                                                     "//button[contains(text(), 'Buy')] | "
                                                     "//button[contains(@class, 'purchase')] | "
                                                     "//a[contains(@class, 'purchase')]"
                                                     )

            # Si encontró el botón, está disponible
            print(f"   ✅ Botón 'Ver entradas' encontrado - DISPONIBLE")
            return [nombre_evento], [], url

        except:
            # No encontró botón = agotado o sin venta
            print(f"   ❌ Botón 'Ver entradas' NO encontrado - AGOTADO/SIN VENTA")
            return [], [nombre_evento], url

    except Exception as e:
        print(f"✗ Error al verificar disponibilidad en Ticketmaster: {e}")
        return [], [], url


# def es_url_taquillalive(url):
#     """Detecta si la URL es de TaquillalLive"""
#     return "taquillalive.com" in url
#
#
# def es_url_taquillalive_performance_details(url):
#     """Detecta si es la página de detalles del evento"""
#     return "taquillalive.com" in url and "performance-details" in url
#
#
# def es_url_taquillalive_book(url):
#     """Detecta si es la página de compra de entradas"""
#     return "taquillalive.com" in url and "book-performance" in url


def verificar_disponibilidad_taquillalive_details(driver, url):
    """
    Verifica disponibilidad en la página de detalles de TaquillalLive
    Busca el botón "Compra Tus Tiquetes"
    """
    try:
        print(f"\n→ Navegando a TaquillalLive (Details): {url}")
        driver.get(url)
        time.sleep(3)

        # Obtener nombre del evento
        nombre_evento = None
        try:
            nombre_evento = driver.find_element(By.XPATH,
                                                "//h1 | //h2 | //div[@class='event-title'] | //span[@class='artist-name']"
                                                ).text.strip()
        except:
            nombre_evento = "Evento TaquillalLive"

        print(f"   Evento: {nombre_evento}")

        # ✅ Buscar el botón "Compra Tus Tiquetes"
        try:
            boton_compra = driver.find_element(By.XPATH,
                                               "//button[contains(text(), 'Compra Tus Tiquetes')] | "
                                               "//a[contains(text(), 'Compra Tus Tiquetes')] | "
                                               "//button[contains(text(), 'COMPRA')] | "
                                               "//a[contains(@class, 'buy-button')]"
                                               )

            print(f"   ✅ Botón 'Compra Tus Tiquetes' encontrado - DISPONIBLE")
            return [nombre_evento], [], url

        except:
            print(f"   ❌ Botón 'Compra Tus Tiquetes' NO encontrado - AGOTADO")
            return [], [nombre_evento], url

    except Exception as e:
        print(f"✗ Error al verificar disponibilidad en TaquillalLive (Details): {e}")
        return [], [], url


def verificar_disponibilidad_taquillalive_book(driver, url):
    """
    Verifica disponibilidad en la página de compra de TaquillalLive
    Detecta sectores disponibles en el panel derecho
    """
    try:
        print(f"\n→ Navegando a TaquillalLive (Book): {url}")
        driver.get(url)
        time.sleep(4)  # Esperar más tiempo para que cargue el mapa

        # Obtener nombre del evento
        nombre_evento = None
        try:
            nombre_evento = driver.find_element(By.XPATH,
                                                "//h1 | //h2[@class='event-title'] | //div[@class='title']"
                                                ).text.strip()
        except:
            try:
                # Obtener del título de la página
                nombre_evento = driver.title.split('|')[0].strip() if '|' in driver.title else driver.title
            except:
                nombre_evento = "Evento TaquillalLive"

        if nombre_evento:
            print(f"   Evento: {nombre_evento}")

        localidades_disponibles = []
        localidades_agotadas = []

        # ✅ MEJORADO: Buscar los BOTONES/DROPDOWNS de sectores en el panel derecho
        # La estructura parece ser div con clase "ticket-item" o similar
        try:
            # Buscar todos los elementos que contienen información de sectores
            sectores = driver.find_elements(By.XPATH,
                                            "//div[contains(@class, 'ticket')] | "
                                            "//div[contains(@class, 'sector')] | "
                                            "//div[contains(@class, 'section')] | "
                                            "//div[@class='row'] | "
                                            "//li[contains(@class, 'ticket')] | "
                                            "//button[contains(@class, 'sector')]"
                                            )

            print(f"   ✓ Se encontraron {len(sectores)} elementos de sectores")

            # Si no hay sectores, buscar por otro patrón
            if len(sectores) == 0:
                sectores = driver.find_elements(By.XPATH,
                                                "//*[contains(text(), 'Sector') or contains(text(), 'Vista') or contains(text(), 'Paquete')]/.."
                                                )
                print(f"   ℹ️ Reintentado: Se encontraron {len(sectores)} elementos")

            if len(sectores) == 0:
                print("   ❌ No se encontraron sectores disponibles")
                return [], [nombre_evento], url

            # Procesar cada sector
            for idx, sector in enumerate(sectores):
                try:
                    # Obtener texto completo del sector
                    texto_sector = sector.text.strip()

                    if not texto_sector or len(texto_sector) < 3:
                        continue

                    # Extraer nombre del sector (primera línea o línea más larga)
                    lineas = [l.strip() for l in texto_sector.split('\n') if l.strip()]

                    if not lineas:
                        continue

                    # El nombre es generalmente la primera línea significativa
                    nombre_sector = lineas[0]

                    # ✅ IMPORTANTE: Filtrar lineas que son solo precios o números
                    if nombre_sector.startswith('$') or nombre_sector.startswith('Desde') or nombre_sector.isdigit():
                        # Buscar la línea anterior que sea el nombre real
                        if len(lineas) > 1:
                            nombre_sector = lineas[0] if not lineas[0].startswith('$') else (
                                lineas[1] if len(lineas) > 1 else nombre_sector)

                    # Evitar palabras genéricas
                    if nombre_sector in ['Filtrar', 'Siguente', 'Siguiente', '+', '-', '']:
                        continue

                    # Si ya hemos visto este sector, saltar
                    if nombre_sector in localidades_disponibles or nombre_sector in localidades_agotadas:
                        continue

                    # ✅ Verificar si el sector está disponible
                    es_disponible = True

                    # Verificar clases del elemento
                    clases = sector.get_attribute("class") or ""
                    if "disabled" in clases or "sold-out" in clases or "agotado" in clases.lower():
                        es_disponible = False

                    # Verificar si está deshabilitado
                    if sector.get_attribute("disabled"):
                        es_disponible = False

                    # Buscar indicadores de agotado en el texto
                    if "Agotado" in texto_sector or "Sold Out" in texto_sector or "AGOTADO" in texto_sector:
                        es_disponible = False

                    # Verificar si hay un dropdown o botón accesible (indicador de disponibilidad)
                    try:
                        dropdown = sector.find_element(By.XPATH,
                                                       ".//select | .//button | .//a[contains(@class, 'btn')]"
                                                       )
                        # Si hay un elemento interactivo, probablemente esté disponible
                    except:
                        # Si no hay elemento interactivo y no es "Filtrar", podría estar agotado
                        if "Filtrar" not in nombre_sector:
                            pass

                    # Registrar el sector
                    if es_disponible and nombre_sector not in ['Filtrar', 'Siguente', 'Siguiente']:
                        localidades_disponibles.append(nombre_sector)
                        print(f"   ✅ {nombre_sector}")
                    elif nombre_sector not in ['Filtrar', 'Siguente', 'Siguiente']:
                        localidades_agotadas.append(nombre_sector)
                        print(f"   ❌ {nombre_sector}")

                except Exception as e:
                    continue

            print(f"\n📊 RESUMEN:")
            print(f"   ✓ Disponibles: {len(localidades_disponibles)}")
            print(f"   ✗ Agotadas: {len(localidades_agotadas)}")

            if localidades_disponibles:
                print(f"\n✅ Sectores DISPONIBLES en TaquillalLive:")
                for idx, loc in enumerate(localidades_disponibles, 1):
                    print(f"   {idx}. {loc}")

            return localidades_disponibles, localidades_agotadas, url

        except Exception as e:
            print(f"   ⚠️ Error buscando sectores: {e}")
            return [], [nombre_evento], url

    except Exception as e:
        print(f"✗ Error al verificar disponibilidad en TaquillalLive (Book): {e}")
        import traceback
        traceback.print_exc()
        return [], [], url


def es_pagina_de_fechas(driver):
    try:
        fechas = driver.find_elements(By.XPATH,
                                      "//a[contains(text(), 'jul')] | //a[contains(text(), 'ago')] | //a[contains(text(), 'sep')] | //a[contains(text(), 'oct')] | //button[contains(@class, 'date')]")
        return len(fechas) > 0
    except:
        return False


def obtener_primera_fecha_disponible(driver):
    try:
        print("   → Buscando primera fecha disponible...")
        fechas = driver.find_elements(By.XPATH,
                                      "//button[contains(@class, 'event-date')] | //a[contains(text(), 'COMPRAR')]")
        if fechas:
            print(f"   ✓ Fecha encontrada. Navegando...")
            fechas[0].click()
            time.sleep(3)
            nueva_url = driver.current_url
            print(f"   ✓ Nueva URL: {nueva_url}")
            return True, nueva_url
        else:
            print("   ✗ No se encontraron fechas disponibles")
            return False, None
    except Exception as e:
        print(f"   ✗ Error al buscar fechas: {e}")
        return False, None


# def contar_articulos_pasala(driver, url):
#     """
#     Cuenta artículos disponibles en Pásala verificando el atributo 'checked'
#     Extrae el nombre del <span class="name"> dentro del label
#     """
#     try:
#         print(f"\n→ Navegando a Pásala: {url}")
#         driver.get(url)
#
#         try:
#             WebDriverWait(driver, 5).until(
#                 EC.presence_of_all_elements_located(
#                     (By.CSS_SELECTOR, "input[id*='seat-cat-checkbox'][type='checkbox']")
#                 )
#             )
#         except:
#             print("   ⚠️ Timeout esperando checkboxes...")
#             time.sleep(2)
#
#         time.sleep(1)
#
#         checkboxes = driver.find_elements(
#             By.CSS_SELECTOR,
#             "input[id*='seat-cat-checkbox'][type='checkbox']"
#         )
#
#         print(f"✓ Se encontraron {len(checkboxes)} categorías totales")
#
#         articulos_disponibles = []
#         articulos_no_disponibles = []
#
#         if len(checkboxes) == 0:
#             print("   ℹ️ No hay categorías en esta página (completamente agotada)")
#             return articulos_disponibles, articulos_no_disponibles, url
#
#         for checkbox in checkboxes:
#             try:
#                 is_checked = checkbox.get_attribute("checked") is not None
#                 is_selected = checkbox.is_selected()
#
#                 # ✅ Obtener el nombre del <span class="name">
#                 nombre_categoria = None
#
#                 # Intento 1: Buscar span.name en el label asociado
#                 try:
#                     checkbox_id = checkbox.get_attribute("id")
#                     if checkbox_id:
#                         label = driver.find_element(By.XPATH, f"//label[@for='{checkbox_id}']")
#                         try:
#                             # Buscar el <span class="name"> dentro del label
#                             span_name = label.find_element(By.CSS_SELECTOR, "span.name")
#                             nombre_categoria = span_name.text.strip()
#                         except:
#                             # Si no encuentra span.name, obtener todo el texto del label
#                             nombre_categoria = label.text.strip()
#                 except:
#                     pass
#
#                 # Intento 2: Si falló, buscar span.name directamente
#                 if not nombre_categoria or nombre_categoria == "":
#                     try:
#                         parent = checkbox.find_element(By.XPATH, "..")
#                         span_name = parent.find_element(By.CSS_SELECTOR, "span.name")
#                         nombre_categoria = span_name.text.strip()
#                     except:
#                         pass
#
#                 # Intento 3: Buscar el label hermano
#                 if not nombre_categoria or nombre_categoria == "":
#                     try:
#                         label = checkbox.find_element(By.XPATH, "following-sibling::label")
#                         try:
#                             span_name = label.find_element(By.CSS_SELECTOR, "span.name")
#                             nombre_categoria = span_name.text.strip()
#                         except:
#                             nombre_categoria = label.text.strip()
#                     except:
#                         pass
#
#                 # Fallback: Usar el ID si todo falla
#                 if not nombre_categoria or nombre_categoria == "":
#                     checkbox_id = checkbox.get_attribute("id") or "desconocida"
#                     # Extraer la parte numérica del ID
#                     id_limpio = checkbox_id.split('-')[-1] if '-' in checkbox_id else checkbox_id
#                     nombre_categoria = f"Localidad ({id_limpio})"
#
#                 # Registrar según estado
#                 if is_checked or is_selected:
#                     articulos_disponibles.append(nombre_categoria)
#                     print(f"   ✅ {nombre_categoria}")
#                 else:
#                     articulos_no_disponibles.append(nombre_categoria)
#                     print(f"   ❌ {nombre_categoria}")
#
#             except Exception as e:
#                 print(f"   ⚠️ Error procesando checkbox: {e}")
#                 continue
#
#         print(f"\n📊 RESUMEN:")
#         print(f"   ✓ Disponibles: {len(articulos_disponibles)}")
#         print(f"   ✗ No disponibles: {len(articulos_no_disponibles)}")
#
#         if articulos_disponibles:
#             print(f"\n✅ Categorías DISPONIBLES en Pásala:")
#             for idx, art in enumerate(articulos_disponibles, 1):
#                 print(f"   {idx}. {art}")
#
#         return articulos_disponibles, articulos_no_disponibles, url
#
#     except Exception as e:
#         print(f"✗ Error al contar artículos Pásala: {e}")
#         return [], [], url

def contar_articulos_pasala(driver, url):
    """
    Cuenta artículos disponibles en Pásala usando JavaScript para extraer nombres
    """
    try:
        print(f"\n→ Navegando a Pásala: {url}")
        driver.get(url)

        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "input[id*='seat-cat-checkbox'][type='checkbox']")
                )
            )
        except:
            print("   ⚠️ Timeout esperando checkboxes...")
            time.sleep(2)

        time.sleep(2)  # Espera extra para que renderice todo

        checkboxes = driver.find_elements(
            By.CSS_SELECTOR,
            "input[id*='seat-cat-checkbox'][type='checkbox']"
        )

        print(f"✓ Se encontraron {len(checkboxes)} categorías totales")

        articulos_disponibles = []
        articulos_no_disponibles = []

        if len(checkboxes) == 0:
            print("   ℹ️ No hay categorías en esta página (completamente agotada)")
            return articulos_disponibles, articulos_no_disponibles, url

        for idx, checkbox in enumerate(checkboxes):
            try:
                is_checked = checkbox.get_attribute("checked") is not None
                is_selected = checkbox.is_selected()

                # ✅ NUEVO: Usar JavaScript para extraer el nombre
                checkbox_id = checkbox.get_attribute("id")

                # Script que busca el label por ID y extrae el nombre
                js_script = f"""
                var label = document.querySelector('label[for="{checkbox_id}"]');
                if (label) {{
                    var spanName = label.querySelector('span.name');
                    if (spanName) {{
                        return spanName.textContent.trim();
                    }}
                    return label.textContent.trim();
                }}
                return null;
                """

                nombre_categoria = driver.execute_script(js_script)

                # Si JavaScript no funciona, fallback a búsqueda tradicional
                if not nombre_categoria:
                    try:
                        label = driver.find_element(By.XPATH, f"//label[@for='{checkbox_id}']")
                        span_name = label.find_element(By.CSS_SELECTOR, "span.name")
                        nombre_categoria = span_name.text.strip()
                    except:
                        try:
                            label = driver.find_element(By.XPATH, f"//label[@for='{checkbox_id}']")
                            nombre_categoria = label.text.strip()
                        except:
                            nombre_categoria = None

                # Si aún sigue vacío, usar fallback
                if not nombre_categoria or nombre_categoria == "":
                    id_limpio = checkbox_id.split('-')[-1] if checkbox_id and '-' in checkbox_id else "desconocida"
                    nombre_categoria = f"Localidad ({id_limpio})"

                # Registrar según estado
                if is_checked or is_selected:
                    articulos_disponibles.append(nombre_categoria)
                    print(f"   ✅ {nombre_categoria}")
                else:
                    articulos_no_disponibles.append(nombre_categoria)
                    print(f"   ❌ {nombre_categoria}")

            except Exception as e:
                print(f"   ⚠️ Error procesando checkbox {idx}: {e}")
                continue

        print(f"\n📊 RESUMEN:")
        print(f"   ✓ Disponibles: {len(articulos_disponibles)}")
        print(f"   ✗ No disponibles: {len(articulos_no_disponibles)}")

        if articulos_disponibles:
            print(f"\n✅ Categorías DISPONIBLES en Pásala:")
            for idx, art in enumerate(articulos_disponibles, 1):
                print(f"   {idx}. {art}")

        return articulos_disponibles, articulos_no_disponibles, url

    except Exception as e:
        print(f"✗ Error al contar artículos Pásala: {e}")
        return [], [], url


def buscar_disponibilidad_pasala(driver, url):
    """
    Busca disponibilidad en URLs de búsqueda de Pásala
    Mejorado para detectar correctamente los eventos
    """
    try:
        print(f"\n→ Navegando a búsqueda Pásala: {url}")
        driver.get(url)
        time.sleep(3)

        # Buscar todos los eventos en los resultados de búsqueda
        eventos = driver.find_elements(By.XPATH,
                                       "//div[contains(@class, 'event')] | //div[contains(@class, 'product')] | //div[contains(@class, 'item')] | //div[contains(@class, 'card')]")

        print(f"✓ Se encontraron {len(eventos)} eventos totales en búsqueda")

        eventos_disponibles = []
        eventos_agotados = []

        if len(eventos) == 0:
            print("   ℹ️ No hay eventos en los resultados de búsqueda")
            return eventos_disponibles, eventos_agotados, url

        # Iterar sobre cada evento
        for idx, evento in enumerate(eventos):
            try:
                # ✅ MEJORADO: Buscar el nombre en múltiples ubicaciones posibles
                nombre_evento = None

                # Intento 1: h2
                try:
                    nombre_evento = evento.find_element(By.XPATH, ".//h2").text.strip()
                except:
                    pass

                # Intento 2: h3
                if not nombre_evento:
                    try:
                        nombre_evento = evento.find_element(By.XPATH, ".//h3").text.strip()
                    except:
                        pass

                # Intento 3: span con clase event-name o title
                if not nombre_evento:
                    try:
                        nombre_evento = evento.find_element(By.XPATH,
                                                            ".//span[@class='event-name'] | .//span[@class='title'] | .//p[@class='title']").text.strip()
                    except:
                        pass

                # Intento 4: Obtener todo el texto y tomar la primera línea
                if not nombre_evento or nombre_evento == "":
                    texto_completo = evento.text.strip()
                    # Filtrar líneas vacías y tomar la primera línea significativa
                    lineas = [l.strip() for l in texto_completo.split('\n') if l.strip() and len(l.strip()) > 5]
                    if lineas:
                        nombre_evento = lineas[0]
                    else:
                        nombre_evento = f"Evento #{idx + 1}"

                # Si aún no tenemos nombre, usar genérico
                if not nombre_evento or nombre_evento == "":
                    nombre_evento = f"Evento #{idx + 1}"

                # Buscar botón "Comprar" en este evento
                try:
                    boton_compra = evento.find_element(By.XPATH,
                                                       ".//button[contains(text(), 'Comprar')] | .//a[contains(text(), 'Comprar')] | .//button[contains(@class, 'buy')] | .//button[contains(text(), 'COMPRAR')]")
                    eventos_disponibles.append(nombre_evento)
                    print(f"   ✅ {nombre_evento}")
                except:
                    eventos_agotados.append(nombre_evento)
                    print(f"   ❌ {nombre_evento}")

            except Exception as e:
                print(f"   ⚠️ Error procesando evento {idx + 1}: {e}")
                continue

        print(f"\n📊 RESUMEN:")
        print(f"   ✓ Disponibles: {len(eventos_disponibles)}")
        print(f"   ✗ Agotados: {len(eventos_agotados)}")

        if eventos_disponibles:
            print(f"\n✅ Eventos DISPONIBLES en búsqueda Pásala:")
            for idx, evt in enumerate(eventos_disponibles, 1):
                print(f"   {idx}. {evt}")

        return eventos_disponibles, eventos_agotados, url

    except Exception as e:
        print(f"✗ Error al buscar disponibilidad en búsqueda Pásala: {e}")
        return [], [], url


def es_url_busqueda_pasala(url):
    """Detecta si la URL es de búsqueda de Pásala"""
    return "pasala.checkout.tuboleta.com/list/resaleProducts" in url


def contar_localidades_disponibles(driver, url):
    """
    Cuenta las localidades disponibles en una URL
    Filtra correctamente qué es una localidad real vs elementos de UI
    """
    try:
        print(f"\n→ Navegando a: {url}")
        driver.get(url)
        time.sleep(3)

        # Detectar tipo de URL
        es_url_producto = "?productId=" in url and "&perfId=" not in url

        if es_url_producto:
            print("   ℹ️ URL de producto - Contando localidades")
        else:
            print("   ℹ️ URL de seat - Mostrando nombres")

        # Buscar filas/elementos de localidades
        filas = driver.find_elements(By.XPATH,
                                     "//th[contains(@class, 'category')] | "
                                     "//tr[contains(@class, 'row')] | "
                                     "//div[contains(@class, 'row')]"
                                     )

        localidades_disponibles = []
        localidades_agotadas = []

        for fila in filas:
            try:
                texto_fila = fila.text.strip()

                if not texto_fila:
                    continue

                # Obtener primera línea
                primera_linea = texto_fila.split('\n')[0].strip()

                # ✅ FILTRO CRÍTICO: Eliminar elementos que NO son localidades
                palabras_prohibidas = [
                    'localidad', 'preferencia', 'tarifa', 'cantidad de boletas',
                    'seleccione un asiento', 'rangos de precios', 'precio',
                    'compra tus tiquetes', 'inscribirse', 'disponibilidad',
                    'total', 'subtotal', 'valor a pagar', 'cargo por servicio'
                ]

                # Verificar si es una palabra prohibida
                es_prohibido = any(palabra in primera_linea.lower() for palabra in palabras_prohibidas)

                if es_prohibido or not primera_linea or len(primera_linea) < 3:
                    continue

                # Verificar si está agotado
                tiene_agotado = "Agotado" in texto_fila

                clases = fila.get_attribute("class") or ""
                if "disabled" in clases.lower():
                    tiene_agotado = True

                # Registrar
                if tiene_agotado:
                    localidades_agotadas.append(primera_linea)
                else:
                    localidades_disponibles.append(primera_linea)

            except:
                continue

        # Eliminar duplicados
        localidades_disponibles = list(dict.fromkeys(localidades_disponibles))
        localidades_agotadas = list(dict.fromkeys(localidades_agotadas))

        print(f"✓ Se encontraron {len(localidades_disponibles)} localidades disponibles")

        # Mostrar solo si hay disponibles
        if localidades_disponibles and not es_url_producto:
            print(f"✓ Localidades DISPONIBLES:")
            for idx, loc in enumerate(localidades_disponibles[:5], 1):  # Solo mostrar primeras 5
                print(f"   {idx}. {loc}")
            if len(localidades_disponibles) > 5:
                print(f"   ... +{len(localidades_disponibles) - 5} más")

        return localidades_disponibles, localidades_agotadas, url

    except Exception as e:
        print(f"✗ Error: {e}")
        return [], [], url


def monitorear_urls(driver):
    """Monitorea todas las URLs en busca de disponibilidad"""

    print("\n" + "=" * 70)
    print("MONITOR DE DISPONIBILIDAD - TUBOLETA")
    print("=" * 70)
    print(f"Total de URLs a monitorear: {len(URLS_A_MONITOREAR)}")

    intentos = 0
    max_intentos = 10000000

    while intentos < max_intentos:
        try:
            intentos += 1
            print(f"\n{'=' * 70}")
            print(f"[Intento {intentos}/{max_intentos}] - {time.strftime('%H:%M:%S')}")
            print("=" * 70)

            # Revisar cada URL
            for idx, url in enumerate(URLS_A_MONITOREAR, 1):
                print(f"\n[URL {idx}/{len(URLS_A_MONITOREAR)}]")

                disponibles = []
                agotadas = []
                url_final = url
                tipo = ""

                # Detectar tipo de URL y obtener disponibilidad
                if es_url_busqueda_pasala(url):
                    disponibles, agotadas, url_final = buscar_disponibilidad_pasala(driver, url)
                    tipo = 'Pásala Búsqueda'
                elif es_url_pasala(url):
                    disponibles, agotadas, url_final = contar_articulos_pasala(driver, url)
                    tipo = 'Pásala'
                elif es_url_taquillalive_book(url):
                    disponibles, agotadas, url_final = verificar_disponibilidad_taquillalive_book(driver, url)
                    tipo = 'TaquillalLive (Book)'
                elif es_url_taquillalive_performance_details(url):
                    disponibles, agotadas, url_final = verificar_disponibilidad_taquillalive_details(driver, url)
                    tipo = 'TaquillalLive (Details)'
                elif es_url_ticketmaster(url):
                    disponibles, agotadas, url_final = verificar_disponibilidad_ticketmaster(driver, url)
                    tipo = 'Ticketmaster'
                elif es_url_tbpgpal(url):
                    disponibles, agotadas, url_final = contar_localidades_disponibles(driver, url)
                    tipo = 'TbpGpal'
                else:
                    disponibles, agotadas, url_final = contar_localidades_disponibles(driver, url)
                    tipo = 'Tuboleta'

                # ✅ NUEVO: Aplicar filtro de localidades
                disponibles_filtrados = filtrar_localidades(disponibles, url_final)

                # Mostrar info del filtrado
                if url_final in FILTROS_LOCALIDADES and FILTROS_LOCALIDADES[url_final]:
                    filtro_info = ", ".join(FILTROS_LOCALIDADES[url_final])
                    print(f"   📌 Filtro activo: {filtro_info}")
                    print(f"   ✓ Disponibles totales: {len(disponibles)}")
                    print(f"   ✓ Disponibles filtrados: {len(disponibles_filtrados)}")

                # ✅ Solo enviar notificación si hay disponibles DESPUÉS del filtro
                if disponibles_filtrados:
                    print("\n" + "=" * 70)
                    print("🎉 ¡DISPONIBILIDAD DETECTADA (COINCIDE CON FILTRO)!")
                    print("=" * 70)

                    # Obtener nombre del evento y fecha
                    nombre_evento = obtener_nombre_evento(driver)
                    fecha_evento = obtener_fecha_evento(driver)

                    print(f"   Evento: {nombre_evento}")
                    if fecha_evento:
                        print(f"   Fecha: {fecha_evento}")

                    # Construir mensaje
                    mensaje = f"🎉 ¡DISPONIBILIDAD DETECTADA!\n\n"

                    mensaje += f"📌 {nombre_evento}\n"

                    if fecha_evento:
                        mensaje += f"📅 {fecha_evento}\n"

                    mensaje += f"\n"

                    # Determinar si mostrar nombres o solo conteo
                    if tipo == 'Tuboleta' and "?productId=" in url_final and "&perfId=" not in url_final:
                        # URL de producto: solo conteo
                        mensaje += f"📍 TUBOLETA - {len(disponibles_filtrados)} localidades disponibles\n"
                        for loc in disponibles_filtrados[:3]:
                            mensaje += f"  • {loc}\n"
                        if len(disponibles_filtrados) > 3:
                            mensaje += f"  ... +{len(disponibles_filtrados) - 3} más\n"
                        mensaje += f"  🔗 {url_final}\n\n"
                    elif tipo == 'Pásala Búsqueda' or tipo == 'Pásala':
                        # Pásala: mostrar nombres
                        mensaje += f"📍 {tipo.upper()} - {len(disponibles_filtrados)} disponibles\n"
                        for loc in disponibles_filtrados[:3]:
                            mensaje += f"  • {loc}\n"
                        if len(disponibles_filtrados) > 3:
                            mensaje += f"  ... +{len(disponibles_filtrados) - 3} más\n"
                        mensaje += f"  🔗 {url_final}\n\n"
                    else:
                        # Otros tipos: mostrar nombres
                        mensaje += f"📍 {tipo.upper()} - {len(disponibles_filtrados)} disponibles\n"
                        for loc in disponibles_filtrados[:3]:
                            mensaje += f"  • {loc}\n"
                        if len(disponibles_filtrados) > 3:
                            mensaje += f"  ... +{len(disponibles_filtrados) - 3} más\n"
                        mensaje += f"  🔗 {url_final}\n\n"

                    mensaje += f"⏰ {time.strftime('%H:%M:%S')}"

                    print(f"\n📱 Enviando Telegram INMEDIATAMENTE...")
                    print(f"   Longitud: {len(mensaje)} caracteres")
                    enviar_whatsapp(mensaje)

                    print(f"\n✅ Notificación enviada. Continuando monitoreo...")
                    print(f"   Reintentando en 5 segundos...")
                    time.sleep(5)

                elif disponibles and url_final in FILTROS_LOCALIDADES:
                    # Hay disponibles pero no coinciden con el filtro
                    print(f"   ℹ️ Disponibles detectados pero NO coinciden con filtro")

        except Exception as e:
            print(f"✗ Error en monitoreo: {e}")
            time.sleep(5)

    print("\n✗ Máximo de intentos alcanzado (10000000)")
    return False


def obtener_nombre_evento(driver):
    """Extrae el nombre del evento de la página"""
    try:
        # Intentar múltiples selectores
        nombre = None

        selectores = [
            "//h1",
            "//h2[@class='event-title']",
            "//div[@class='title']",
            "//span[@class='event-name']",
            "//div[contains(@class, 'event-header')]//h1",
            "//div[contains(@class, 'event-info')]//h1"
        ]

        for selector in selectores:
            try:
                nombre = driver.find_element(By.XPATH, selector).text.strip()
                if nombre and len(nombre) > 3:
                    return nombre
            except:
                continue

        # Si no encuentra por XPath, intentar del título de la página
        if not nombre:
            titulo = driver.title.split('|')[0].strip() if '|' in driver.title else driver.title
            if titulo and len(titulo) > 3:
                return titulo

        return "Evento"

    except:
        return "Evento"


def obtener_fecha_evento(driver):
    """Extrae la fecha del evento de la página"""
    try:
        fecha = None

        # Intentar encontrar fechas en formato común
        selectores = [
            "//span[contains(text(), '202')]",  # Años 202x
            "//div[contains(@class, 'date')]",
            "//time",
            "//span[@class='date']",
            "//p[contains(text(), 'viernes') or contains(text(), 'sábado') or contains(text(), 'domingo') or contains(text(), 'lunes') or contains(text(), 'martes') or contains(text(), 'miércoles') or contains(text(), 'jueves')]"
        ]

        for selector in selectores:
            try:
                elemento = driver.find_element(By.XPATH, selector)
                texto = elemento.text.strip()
                if texto and len(texto) > 5:
                    # Si contiene día y mes, es probablemente una fecha
                    if any(mes in texto.lower() for mes in
                           ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
                            'octubre', 'noviembre', 'diciembre', 'january', 'february', 'march', 'april', 'may', 'june',
                            'july', 'august', 'september', 'october', 'november', 'december']):
                        fecha = texto
                        break
                    elif '202' in texto:  # Contiene año
                        fecha = texto
                        break
            except:
                continue

        return fecha if fecha else None

    except:
        return None


def filtrar_localidades(disponibles, url):
    """
    Filtra las localidades disponibles según los criterios definidos

    Retorna:
    - localidades filtradas si hay coincidencias
    - lista vacía si no hay coincidencias
    - todas las localidades si la URL no tiene filtro definido
    """
    # Si la URL no tiene filtro, retornar todas
    if url not in FILTROS_LOCALIDADES:
        return disponibles

    filtro = FILTROS_LOCALIDADES[url]

    # Si el filtro está vacío, retornar todas
    if not filtro:
        return disponibles

    # Filtrar: solo localidades que contienen alguna palabra clave (búsqueda parcial)
    localidades_filtradas = []

    for localidad in disponibles:
        for palabra_clave in filtro:
            # Búsqueda parcial (no sensible a mayúsculas)
            if palabra_clave.lower() in localidad.lower():
                localidades_filtradas.append(localidad)
                break  # No agregar duplicados

    return localidades_filtradas


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("MONITOR DE DISPONIBILIDAD - TUBOLETA Y PÁSALA")
    print("=" * 70)

    driver = conectar_chrome()
    if driver:
        try:
            exito = monitorear_urls(driver)
            if exito:
                print("\n✓ ¡Script completado!")
            else:
                print("\n✗ Script finalizado por límite de intentos")
        except KeyboardInterrupt:
            print("\n⚠ Script detenido por el usuario")
        except Exception as e:
            print(f"\n✗ Error: {e}")
        finally:
            print("\nScript finalizado")
    else:
        print("\n✗ Error de conexión")
