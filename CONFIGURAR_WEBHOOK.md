# 🔧 Configurar Webhook de Telegram - Guía Rápida

## ⚠️ Problema Detectado

Tu aplicación está funcionando correctamente en Render, pero **el webhook no está configurado en Telegram**. Por eso el bot no responde.

## ✅ Solución: Configurar el Webhook

### Paso 1: Obtener tu Token

Tu token está en Render Dashboard → Environment → `TELEGRAM_BOT_TOKEN`

### Paso 2: Configurar el Webhook

Elige una de estas opciones:

#### Opción A: Usando curl (Windows PowerShell)

```powershell
# Reemplaza TU_TOKEN con tu token real
$token = "TU_TOKEN"
$webhookUrl = "https://agente-8yf2.onrender.com/webhook"
$secret = "TU_SECRETO"  # El mismo que tienes en TELEGRAM_WEBHOOK_SECRET

$body = @{
    url = $webhookUrl
    secret_token = $secret
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/setWebhook" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

#### Opción B: Usando curl (Linux/Mac)

```bash
curl -X POST "https://api.telegram.org/bot<TU_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://agente-8yf2.onrender.com/webhook",
    "secret_token": "TU_SECRETO"
  }'
```

#### Opción C: Usando el script Python

1. Descarga `setup_webhook.py` a tu máquina
2. Configura variables de entorno:
   ```bash
   export TELEGRAM_BOT_TOKEN="tu_token"
   export TELEGRAM_WEBHOOK_URL="https://agente-8yf2.onrender.com/webhook"
   export TELEGRAM_WEBHOOK_SECRET="tu_secreto"
   ```
3. Ejecuta:
   ```bash
   python setup_webhook.py set
   ```

### Paso 3: Verificar que Funcionó

Ejecuta este comando para verificar:

```bash
curl "https://api.telegram.org/bot<TU_TOKEN>/getWebhookInfo"
```

Deberías ver algo como:

```json
{
  "ok": true,
  "result": {
    "url": "https://agente-8yf2.onrender.com/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

Si `url` está vacío o es diferente, el webhook no se configuró correctamente.

### Paso 4: Probar el Bot

1. Espera 10-30 segundos después de configurar el webhook
2. Abre Telegram y envía un mensaje de texto al bot (ej: "hola" o "/start")
3. El bot debería responder

### Paso 5: Verificar en los Logs

Después de enviar un mensaje, revisa los logs en Render. Deberías ver algo como:

```
127.0.0.1 - - [13/Jan/2026:14:52:00 +0000] "POST /webhook HTTP/1.1" 200 ...
```

Si ves peticiones POST a `/webhook`, significa que está funcionando.

## 🔍 Verificación Rápida

### 1. Verificar que la app esté funcionando

Abre en tu navegador:
```
https://agente-8yf2.onrender.com/health
```

Deberías ver:
```json
{
  "status": "ok",
  "telegram_configured": true,
  "calendar_configured": false,
  "database_path": "/opt/render/project/src/data/app.db"
}
```

### 2. Verificar variables de entorno en Render

Asegúrate de tener:
- ✅ `TELEGRAM_BOT_TOKEN` - Tu token del bot
- ✅ `TELEGRAM_WEBHOOK_URL` - `https://agente-8yf2.onrender.com/webhook`
- ⚠️ `TELEGRAM_WEBHOOK_SECRET` - Opcional pero recomendado

### 3. Verificar webhook en Telegram

```bash
curl "https://api.telegram.org/bot<TU_TOKEN>/getWebhookInfo"
```

## ❌ Problemas Comunes

### "El webhook se configuró pero el bot sigue sin responder"

1. **Espera 30-60 segundos** - Puede tardar un poco
2. **Verifica los logs** - Busca errores en Render Dashboard → Logs
3. **Prueba con un mensaje de texto** - No solo con voz
4. **Verifica que el webhook esté activo**:
   ```bash
   curl "https://api.telegram.org/bot<TU_TOKEN>/getWebhookInfo"
   ```

### "Error 401 Unauthorized en los logs"

El `TELEGRAM_WEBHOOK_SECRET` no coincide. Verifica que:
- El secret en Render sea el mismo que usaste al configurar el webhook
- O elimina el secret token si no lo necesitas (no recomendado)

### "Error 503 en /webhook"

La aplicación no está corriendo. Verifica:
- Que el servicio esté "Live" en Render (no "Sleeping")
- Que no haya errores en los logs de inicio

## 📝 Notas Importantes

- **URL del webhook**: Debe ser exactamente `https://agente-8yf2.onrender.com/webhook` (sin barra final)
- **HTTPS obligatorio**: Telegram solo acepta webhooks con HTTPS
- **Secret token**: Si lo configuras, debe coincidir en ambos lados
- **Primera vez**: El primer mensaje después de configurar puede tardar 30-60 segundos

## 🆘 Si Nada Funciona

1. Revisa los logs completos en Render Dashboard
2. Verifica que el token sea correcto:
   ```bash
   curl "https://api.telegram.org/bot<TU_TOKEN>/getMe"
   ```
3. Prueba eliminar y volver a configurar el webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TU_TOKEN>/deleteWebhook"
   # Luego configúralo de nuevo
   ```




