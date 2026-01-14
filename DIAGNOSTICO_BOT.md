# 🔍 Diagnóstico: Bot de Telegram No Responde

## ✅ Checklist Rápido

Sigue estos pasos en orden para diagnosticar el problema:

### 1. Verificar Variables de Entorno en Render

Asegúrate de tener configuradas estas variables:

- ✅ `TELEGRAM_BOT_TOKEN` - Token del bot (obligatorio)
- ✅ `TELEGRAM_WEBHOOK_URL` - Debe ser: `https://agente-8yf2.onrender.com/webhook` (ajusta con tu URL)
- ⚠️ `TELEGRAM_WEBHOOK_SECRET` - Opcional pero recomendado
- ✅ `ADMIN_PASSWORD` - Para el panel web
- ✅ `SECRET_KEY` - Clave secreta para sesiones
- ✅ `SQLITE_PATH` - `/opt/render/project/src/data/app.db`

### 2. Verificar que el Webhook Esté Configurado

**Este es el problema más común.** El webhook debe estar configurado en Telegram.

#### Opción A: Usando curl (desde tu terminal local)

```bash
# Reemplaza TU_TOKEN con tu token real
curl -X POST "https://api.telegram.org/bot<TU_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://agente-8yf2.onrender.com/webhook",
    "secret_token": "tu_secreto_webhook"
  }'
```

#### Opción B: Usando el script Python

1. Descarga `setup_webhook.py` a tu máquina local
2. Configura las variables de entorno:
   ```bash
   export TELEGRAM_BOT_TOKEN="tu_token"
   export TELEGRAM_WEBHOOK_URL="https://agente-8yf2.onrender.com/webhook"
   export TELEGRAM_WEBHOOK_SECRET="tu_secreto"
   ```
3. Ejecuta:
   ```bash
   python setup_webhook.py check  # Verifica estado
   python setup_webhook.py set    # Configura webhook
   ```

#### Opción C: Verificar estado actual

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

Si `url` está vacío o es diferente, el webhook no está configurado.

### 3. Verificar que la Aplicación Esté Funcionando

1. **Verifica que la app esté activa:**
   - Ve a `https://agente-8yf2.onrender.com/health`
   - Deberías ver un JSON con información del sistema

2. **Verifica los logs en Render:**
   - Ve a Render Dashboard → Tu servicio → "Logs"
   - Busca mensajes como:
     - ✅ `"Bot de Telegram inicializado"` - El bot está configurado
     - ❌ `"TELEGRAM_BOT_TOKEN no configurado"` - Falta el token
     - ❌ Errores al procesar webhook

### 4. Probar el Webhook Manualmente

Puedes probar si el webhook está recibiendo peticiones:

```bash
# Reemplaza con tu URL y token
curl -X POST https://agente-8yf2.onrender.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123456789,
    "message": {
      "message_id": 1,
      "from": {
        "id": 123456789,
        "is_bot": false,
        "first_name": "Test"
      },
      "chat": {
        "id": 123456789,
        "type": "private"
      },
      "date": 1234567890,
      "text": "test"
    }
  }'
```

Si funciona, deberías recibir `{"ok": true}`.

### 5. Verificar Logs de Errores

En Render Dashboard → Logs, busca:

- **Errores de importación**: `ModuleNotFoundError`, `ImportError`
- **Errores de base de datos**: `sqlite3.OperationalError`
- **Errores de webhook**: `Error procesando webhook`
- **Errores de audio**: `Error al procesar audio`

## 🔧 Soluciones Comunes

### Problema: "Bot no responde a ningún mensaje"

**Causa más probable**: Webhook no configurado

**Solución**:
1. Configura el webhook usando uno de los métodos del paso 2
2. Verifica que `TELEGRAM_WEBHOOK_URL` sea exactamente: `https://agente-8yf2.onrender.com/webhook` (sin barra final)
3. Espera 1-2 minutos y prueba enviar un mensaje al bot

### Problema: "Bot responde a veces pero no siempre"

**Causa**: La aplicación está en modo "sleep" (plan gratuito)

**Solución**:
- Render pone a dormir servicios gratuitos después de 15 minutos
- El primer mensaje después de dormir puede tardar 30-60 segundos
- Considera usar un plan de pago o un servicio de "ping" externo

### Problema: "Error 503 en /webhook"

**Causa**: La aplicación no está corriendo o hay un error

**Solución**:
1. Verifica los logs en Render
2. Verifica que la aplicación esté "Live" (no "Sleeping")
3. Revisa que todas las dependencias estén instaladas

### Problema: "Error: Bot no configurado"

**Causa**: `TELEGRAM_BOT_TOKEN` no está configurado o es incorrecto

**Solución**:
1. Verifica que la variable de entorno esté configurada en Render
2. Verifica que el token sea correcto (sin espacios, sin comillas)
3. Reinicia el servicio después de cambiar variables de entorno

### Problema: "Error: Unauthorized" en webhook

**Causa**: `TELEGRAM_WEBHOOK_SECRET` no coincide

**Solución**:
1. Verifica que `TELEGRAM_WEBHOOK_SECRET` en Render coincida con el que usaste al configurar el webhook
2. O elimina el secret token si no lo necesitas (no recomendado para producción)

## 📝 Pasos de Diagnóstico Detallado

### Paso 1: Verificar Token

```bash
curl "https://api.telegram.org/bot<TU_TOKEN>/getMe"
```

Deberías ver información de tu bot. Si no, el token es incorrecto.

### Paso 2: Verificar Webhook

```bash
curl "https://api.telegram.org/bot<TU_TOKEN>/getWebhookInfo"
```

Verifica que `url` sea correcta y `pending_update_count` sea 0 o bajo.

### Paso 3: Verificar Aplicación

```bash
curl "https://agente-8yf2.onrender.com/health"
```

Deberías ver un JSON con información del sistema.

### Paso 4: Probar Webhook Directamente

Envía un mensaje de texto al bot en Telegram y revisa los logs en Render para ver si llega la petición.

## 🆘 Si Nada Funciona

1. **Revisa los logs completos** en Render Dashboard
2. **Verifica que el build haya sido exitoso** (sin errores)
3. **Prueba reiniciar el servicio** en Render
4. **Verifica que el disco persistente esté montado** (si usas SQLite)
5. **Contacta soporte** con los logs de error específicos

## 📞 Información Útil para Soporte

Si necesitas ayuda, proporciona:

- URL de tu aplicación en Render
- Logs de error específicos
- Resultado de `getWebhookInfo`
- Resultado de `/health` endpoint
- Variables de entorno configuradas (sin valores sensibles)



