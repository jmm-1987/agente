#!/bin/bash
# Script para verificar y configurar el webhook de Telegram

echo "=========================================="
echo "🔍 Verificación de Webhook de Telegram"
echo "=========================================="
echo ""

# Pedir token
read -p "Introduce tu TELEGRAM_BOT_TOKEN: " TOKEN
if [ -z "$TOKEN" ]; then
    echo "❌ Error: Token no puede estar vacío"
    exit 1
fi

# Pedir URL del webhook
read -p "Introduce la URL de tu webhook (ej: https://agente-8yf2.onrender.com/webhook): " WEBHOOK_URL
if [ -z "$WEBHOOK_URL" ]; then
    echo "❌ Error: URL no puede estar vacía"
    exit 1
fi

# Pedir secret (opcional)
read -p "Introduce TELEGRAM_WEBHOOK_SECRET (opcional, presiona Enter para omitir): " SECRET

echo ""
echo "📊 Verificando estado actual del webhook..."
echo ""

# Verificar estado actual
curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo" | python3 -m json.tool

echo ""
echo ""
read -p "¿Deseas configurar el webhook ahora? (s/n): " CONFIRM

if [ "$CONFIRM" != "s" ] && [ "$CONFIRM" != "S" ]; then
    echo "Operación cancelada"
    exit 0
fi

echo ""
echo "🔧 Configurando webhook..."

# Construir payload
PAYLOAD="{\"url\": \"${WEBHOOK_URL}\"}"
if [ ! -z "$SECRET" ]; then
    PAYLOAD="{\"url\": \"${WEBHOOK_URL}\", \"secret_token\": \"${SECRET}\"}"
fi

# Configurar webhook
RESULT=$(curl -s -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

echo "$RESULT" | python3 -m json.tool

echo ""
echo "✅ Webhook configurado!"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Espera 10-30 segundos"
echo "   2. Envía un mensaje de texto al bot en Telegram"
echo "   3. Revisa los logs en Render para ver si llega la petición"
echo ""






