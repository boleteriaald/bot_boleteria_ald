# ============================================================
# PLANTILLA DE CONFIGURACION
# ============================================================
# 1. Copia este archivo como "config.py"
# 2. Rellena los valores reales
# 3. NUNCA subas config.py a GitHub (ya esta en .gitignore)
# ============================================================

# ------------------------------------------------------------
# TELEGRAM (canal de notificacion actual)
# ------------------------------------------------------------
# Como obtener el token:
#   1. Abre Telegram y busca a @BotFather
#   2. Envia /newbot y sigue los pasos
#   3. Copia el token que te entrega
#
# Como obtener tu chat id:
#   1. Busca a @userinfobot en Telegram y envia /start
#   2. Copia el numero "Id"
TELEGRAM_BOT_TOKEN = "123456789:AA-tu-token-de-botfather-aqui"
TELEGRAM_CHAT_ID = "123456789"

# ------------------------------------------------------------
# WHATSAPP / CALLMEBOT (opcional - actualmente desactivado)
# ------------------------------------------------------------
# Pasos para obtener la API KEY:
#   1. Agrega el numero +34 644 84 49 14 (CallMeBot) a tus contactos
#   2. Envia por WhatsApp: "I allow callmebot to send me messages"
#   3. El bot responde con tu API KEY
WHATSAPP_PHONE = "+57XXXXXXXXXX"
WHATSAPP_APIKEY = "000000"

# ------------------------------------------------------------
# MONITOR
# ------------------------------------------------------------
CANTIDAD_BOLETAS_DESEADAS = 2   # Cuantas boletas se buscan
TIEMPO_ENTRE_INTENTOS = 5       # Segundos entre cada ronda de revision
MAX_INTENTOS = 30               # Maximo de rondas antes de detenerse
