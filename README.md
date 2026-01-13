# Agenda por Telegram

Sistema completo de gestión de tareas mediante Telegram usando solo mensajes de voz. El bot responde con texto y botones interactivos.

## Características

- ✅ **Solo audio**: Interacción completa mediante mensajes de voz en Telegram
- 🎤 **Transcripción local**: Usa faster-whisper (sin APIs de pago)
- 🧠 **Parser inteligente**: Detección de intenciones y extracción de entidades usando reglas + regex + rapidfuzz
- 👥 **Gestión de clientes**: Identificación automática de clientes con fuzzy matching
- 📅 **Google Calendar**: Integración opcional con Google Calendar
- 🌐 **Web App**: Interfaz web para administración de tareas y clientes
- 💾 **SQLite**: Base de datos SQLite (funciona en producción con disco persistente)

## Intenciones Soportadas

- **CREAR**: Crear nueva tarea
- **LISTAR**: Listar tareas (hoy/mañana/semana/pendientes)
- **CERRAR**: Marcar tarea como completada
- **REPROGRAMAR**: Cambiar fecha de tarea
- **CAMBIAR_PRIORIDAD**: Modificar prioridad de tarea

## Requisitos

- Python 3.11+
- ffmpeg (para conversión de audio)
- Token de bot de Telegram

### Instalación de ffmpeg

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Descargar desde https://ffmpeg.org/download.html y añadir al PATH.

## Instalación Local

1. **Clonar repositorio:**
```bash
git clone <repo-url>
cd agente
```

2. **Crear entorno virtual:**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno:**
Crear archivo `.env` o exportar variables:
```bash
export TELEGRAM_BOT_TOKEN="tu_token_aqui"
export ADMIN_PASSWORD="tu_contraseña_admin"
export SECRET_KEY="clave_secreta_aleatoria"
```

5. **Inicializar base de datos:**
La base de datos se crea automáticamente al ejecutar la aplicación.

6. **Ejecutar aplicación:**
```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Configuración de Telegram Webhook

Una vez desplegado, configura el webhook de Telegram:

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://tu-dominio.com/webhook",
    "secret_token": "tu_secreto_webhook"
  }'
```

O usar el endpoint de la aplicación:
```bash
curl -X POST https://tu-dominio.com/webhook/set \
  -H "Content-Type: application/json" \
  -d '{"url": "https://tu-dominio.com/webhook"}'
```

## Despliegue en Render

### Configuración Básica

1. **Crear nuevo servicio Web en Render**
2. **Conectar repositorio Git**
3. **Configurar variables de entorno:**

   - `TELEGRAM_BOT_TOKEN`: Token del bot de Telegram
   - `TELEGRAM_WEBHOOK_URL`: URL completa del webhook (ej: `https://tu-app.onrender.com/webhook`)
   - `TELEGRAM_WEBHOOK_SECRET`: Secreto para webhook (opcional pero recomendado)
   - `ADMIN_PASSWORD`: Contraseña para acceso web
   - `SECRET_KEY`: Clave secreta para sesiones (se puede generar automáticamente)
   - `SQLITE_PATH`: Ruta de la base de datos (por defecto: `/opt/render/project/src/data/app.db`)

### ⚠️ IMPORTANTE: Disco Persistente en Render

**SQLite requiere disco persistente para conservar datos tras reinicios.**

En Render:
1. Ir a la configuración del servicio
2. Activar **"Persistent Disk"**
3. Configurar tamaño (mínimo 1GB recomendado)
4. Montar en `/opt/render/project/src/data`

**Sin disco persistente, los datos se perderán en cada despliegue/reinicio.**

### Variables Opcionales (Google Calendar)

Si quieres habilitar Google Calendar:

- `GOOGLE_CLIENT_ID`: ID de cliente OAuth2
- `GOOGLE_CLIENT_SECRET`: Secreto de cliente OAuth2
- `GOOGLE_REFRESH_TOKEN`: Token de refresco
- `GOOGLE_CALENDAR_ID`: ID del calendario

### Build Command

Render usará automáticamente el `render.yaml` que incluye:
- Instalación de ffmpeg (sistema)
- Instalación de dependencias Python
- Instalación de ffmpeg-python (wrapper de Python)

El build command instala automáticamente ffmpeg usando apt-get.

### Start Command

```
gunicorn app:app --bind 0.0.0.0:$PORT
```

## Configuración de Google Calendar (Opcional)

1. **Crear proyecto en Google Cloud Console**
2. **Habilitar Google Calendar API**
3. **Crear credenciales OAuth2**
4. **Obtener refresh token:**

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar']

flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

print(f"Refresh Token: {creds.refresh_token}")
```

5. **Configurar variables de entorno** con los valores obtenidos.

## Estructura del Proyecto

```
agente/
├── app.py                 # Flask app principal
├── telegram_bot.py        # Lógica del bot
├── audio_pipeline.py      # Procesamiento de audio
├── parser.py              # Parser de intenciones
├── database.py            # Modelos SQLite
├── calendar_sync.py       # Google Calendar
├── config.py              # Configuración
├── utils.py               # Utilidades
├── requirements.txt       # Dependencias
├── Procfile              # Para Render
├── render.yaml           # Configuración Render
├── tests/                # Tests pytest
├── templates/            # Templates Jinja2
├── static/               # CSS/JS
└── data/                 # Base de datos SQLite
```

## Uso

### Por Telegram

1. Envía un mensaje de voz al bot
2. El bot transcribe y procesa la intención
3. Responde con texto y botones interactivos
4. Confirma o modifica según necesites

**Ejemplos de comandos por voz:**

- "Crear tarea llamar al cliente Alditraex mañana"
- "Listar tareas pendientes"
- "Da por hecha la tarea del cliente Alditraex"
- "Tarea urgente para el cliente Test el lunes"

### Por Web App

1. Accede a `http://localhost:5000` (o tu dominio en producción)
2. Inicia sesión con `ADMIN_PASSWORD`
3. Gestiona tareas y clientes desde la interfaz web

## Gestión de Clientes

El sistema detecta automáticamente menciones de clientes en los audios:

- "cliente X"
- "del cliente X"
- "para el cliente X"

**Fuzzy Matching:**
- **≥85% confianza**: Selección automática
- **70-84% confianza**: Pide confirmación con botones
- **<70% confianza**: Ofrece crear cliente nuevo

## Tests

Ejecutar tests con pytest:

```bash
pytest tests/
```

Tests incluidos:
- `test_parser.py`: Tests de detección de intenciones
- `test_client_matching.py`: Tests de fuzzy matching de clientes
- `test_date_extraction.py`: Tests de extracción de fechas

## Límites

- **Duración máxima de audio**: 60 segundos
- **Archivos temporales**: Se eliminan automáticamente después de procesar

## Troubleshooting

### Error: "ffmpeg no está instalado"
Instala ffmpeg según tu sistema operativo (ver Requisitos).

### Error: "faster-whisper no está instalado"
```bash
pip install faster-whisper
```

### Error: "Bot no configurado"
Verifica que `TELEGRAM_BOT_TOKEN` esté configurado correctamente.

### Error: "Google Calendar no está configurado"
Es normal si no has configurado las variables de Google Calendar. La funcionalidad se deshabilita automáticamente.

### Base de datos no persiste en Render
Activa **Persistent Disk** en la configuración de Render y monta en `/opt/render/project/src/data`.

## Licencia

MIT

## Autor

Desarrollado como sistema completo de gestión de tareas por voz.
