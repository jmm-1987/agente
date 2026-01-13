# Guía de Despliegue en Render

Esta guía te ayudará a desplegar la aplicación Agenda por Telegram en Render paso a paso.

## ✅ Checklist Pre-Despliegue

Antes de comenzar, asegúrate de tener:

- [ ] Repositorio Git con el código (GitHub, GitLab, etc.)
- [ ] Token de bot de Telegram (obtener desde @BotFather)
- [ ] Contraseña para el panel web (ADMIN_PASSWORD)
- [ ] (Opcional) Credenciales de Google Calendar

## 📋 Paso 1: Crear Servicio en Render

1. Ve a [Render Dashboard](https://dashboard.render.com/)
2. Haz clic en **"New +"** → **"Web Service"**
3. Conecta tu repositorio Git
4. Selecciona el repositorio y la rama (normalmente `main` o `master`)

## ⚙️ Paso 2: Configuración del Servicio

### Configuración Básica

- **Name**: `agenda-telegram` (o el nombre que prefieras)
- **Environment**: `Python 3`
- **Region**: Elige la región más cercana a tus usuarios
- **Branch**: `main` (o tu rama principal)
- **Root Directory**: Dejar vacío (raíz del proyecto)

### Build & Start Commands

Render detectará automáticamente el `render.yaml`, pero puedes verificar:

- **Build Command**: Se ejecuta automáticamente desde `render.yaml`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`

## 🔐 Paso 3: Variables de Entorno

Ve a la sección **"Environment"** y añade las siguientes variables:

### Variables Obligatorias

```
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_WEBHOOK_URL=https://tu-app.onrender.com/webhook
TELEGRAM_WEBHOOK_SECRET=secreto_aleatorio_seguro
ADMIN_PASSWORD=tu_contraseña_segura
SECRET_KEY=clave_secreta_aleatoria_larga
SQLITE_PATH=/opt/render/project/src/data/app.db
```

**Nota**: `SECRET_KEY` puede generarse automáticamente si usas `render.yaml`, pero es mejor configurarla manualmente.

### Variables Opcionales (Google Calendar)

Si quieres habilitar Google Calendar:

```
GOOGLE_CLIENT_ID=tu_client_id
GOOGLE_CLIENT_SECRET=tu_client_secret
GOOGLE_REFRESH_TOKEN=tu_refresh_token
GOOGLE_CALENDAR_ID=tu_calendar_id
```

### Generar SECRET_KEY

Puedes generar una clave secreta segura con Python:

```python
import secrets
print(secrets.token_urlsafe(32))
```

O con OpenSSL:

```bash
openssl rand -hex 32
```

## 💾 Paso 4: Configurar Disco Persistente

**⚠️ CRÍTICO**: Sin disco persistente, la base de datos SQLite se perderá en cada reinicio.

1. En la configuración del servicio, ve a **"Disks"**
2. Haz clic en **"Add Disk"**
3. Configura:
   - **Name**: `data-disk`
   - **Mount Path**: `/opt/render/project/src/data`
   - **Size**: Mínimo 1GB (recomendado 2GB)
4. Guarda los cambios

## 🚀 Paso 5: Desplegar

1. Haz clic en **"Create Web Service"**
2. Render comenzará a construir la aplicación
3. El proceso puede tardar 5-10 minutos (instala ffmpeg, Python packages, etc.)
4. Una vez completado, verás la URL de tu aplicación (ej: `https://agenda-telegram.onrender.com`)

## 🔗 Paso 6: Configurar Webhook de Telegram

Una vez que la aplicación esté desplegada y funcionando:

### Opción 1: Usando curl

```bash
curl -X POST "https://api.telegram.org/bot<TU_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://tu-app.onrender.com/webhook",
    "secret_token": "tu_secreto_webhook"
  }'
```

Reemplaza:
- `<TU_TOKEN>`: Tu token de bot de Telegram
- `https://tu-app.onrender.com/webhook`: La URL de tu aplicación + `/webhook`
- `tu_secreto_webhook`: El mismo valor que configuraste en `TELEGRAM_WEBHOOK_SECRET`

### Opción 2: Usando el endpoint de la aplicación

```bash
curl -X POST https://tu-app.onrender.com/webhook/set \
  -H "Content-Type: application/json" \
  -d '{"url": "https://tu-app.onrender.com/webhook"}'
```

### Verificar Webhook

Para verificar que el webhook está configurado correctamente:

```bash
curl "https://api.telegram.org/bot<TU_TOKEN>/getWebhookInfo"
```

Deberías ver algo como:

```json
{
  "ok": true,
  "result": {
    "url": "https://tu-app.onrender.com/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

## ✅ Paso 7: Verificar Funcionamiento

1. **Probar el bot en Telegram**:
   - Envía un mensaje de voz al bot
   - Debería responder transcribiendo y procesando la intención

2. **Probar el panel web**:
   - Ve a `https://tu-app.onrender.com/admin/login`
   - Inicia sesión con `ADMIN_PASSWORD`
   - Deberías ver la lista de tareas

3. **Revisar logs**:
   - En Render Dashboard, ve a la sección **"Logs"**
   - Verifica que no haya errores

## 🔧 Solución de Problemas

### Error: "ffmpeg no está instalado"

El `render.yaml` debería instalar ffmpeg automáticamente. Si ves este error:

1. Verifica que el build command incluya `apt-get install -y ffmpeg`
2. Revisa los logs de build en Render
3. Asegúrate de que el servicio esté usando el `render.yaml`

### Error: "Bot no responde"

1. Verifica que `TELEGRAM_BOT_TOKEN` esté configurado correctamente
2. Verifica que el webhook esté configurado (ver Paso 6)
3. Revisa los logs de la aplicación en Render
4. Prueba enviar un mensaje de texto primero (no solo voz)

### Error: "Base de datos no persiste"

1. Verifica que el disco persistente esté montado en `/opt/render/project/src/data`
2. Verifica que `SQLITE_PATH` apunte a `/opt/render/project/src/data/app.db`
3. Revisa los logs para ver si hay errores de permisos

### Error: "faster-whisper no funciona"

1. Verifica que el modelo se descargue correctamente (puede tardar en el primer uso)
2. Revisa los logs para ver errores específicos
3. Considera usar un modelo más pequeño (`base` en lugar de `small`) si hay problemas de memoria

### La aplicación se duerme después de inactividad

Render pone a dormir los servicios gratuitos después de 15 minutos de inactividad. Para evitar esto:

1. Usa un plan de pago (Starter o superior)
2. O configura un cron job externo que haga ping a tu aplicación cada 10 minutos

## 📊 Monitoreo

### Logs en Render

- Ve a **"Logs"** en el dashboard de Render
- Los logs muestran:
  - Errores de la aplicación
  - Mensajes de Telegram procesados
  - Errores de transcripción de audio

### Métricas

Render proporciona métricas básicas:
- CPU usage
- Memory usage
- Request count
- Response times

## 🔄 Actualizaciones

Para actualizar la aplicación:

1. Haz push de tus cambios a Git
2. Render detectará automáticamente los cambios
3. Iniciará un nuevo build y despliegue
4. La aplicación se reiniciará con los nuevos cambios

**Nota**: Durante el despliegue, la aplicación puede estar temporalmente no disponible (1-2 minutos).

## 🔒 Seguridad

- ✅ **NUNCA** subas el archivo `.env` a Git (ya está en `.gitignore`)
- ✅ Usa contraseñas seguras para `ADMIN_PASSWORD` y `SECRET_KEY`
- ✅ Usa un `TELEGRAM_WEBHOOK_SECRET` aleatorio y seguro
- ✅ Mantén tu token de Telegram privado
- ✅ Si expones el token accidentalmente, revócalo inmediatamente en @BotFather

## 📝 Notas Adicionales

- El primer despliegue puede tardar más tiempo (descarga modelos de Whisper)
- Los modelos de Whisper se cachean automáticamente
- La aplicación usa `gunicorn` con múltiples workers para mejor rendimiento
- Render asigna automáticamente el puerto mediante la variable `$PORT`

## 🆘 Soporte

Si tienes problemas:

1. Revisa los logs en Render Dashboard
2. Verifica que todas las variables de entorno estén configuradas
3. Prueba la aplicación localmente primero
4. Consulta la documentación de Render: https://render.com/docs

