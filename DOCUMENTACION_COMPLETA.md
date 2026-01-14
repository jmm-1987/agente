# Documentación Completa del Sistema de Gestión de Tareas por Telegram

## 📋 Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Flujo de Funcionamiento](#flujo-de-funcionamiento)
5. [Base de Datos](#base-de-datos)
6. [Funcionalidades del Bot](#funcionalidades-del-bot)
7. [Panel Web de Administración](#panel-web-de-administración)
8. [Procesamiento de Audio](#procesamiento-de-audio)
9. [Parser de Intenciones](#parser-de-intenciones)
10. [Configuración](#configuración)
11. [Despliegue](#despliegue)
12. [Troubleshooting](#troubleshooting)

---

## 📖 Descripción General

Este sistema es una **aplicación completa de gestión de tareas** que funciona principalmente a través de **mensajes de voz en Telegram**. Permite crear, listar, cerrar y gestionar tareas usando comandos de voz naturales en español.

### Características Principales

- 🎤 **Interacción por voz**: Todo se gestiona mediante mensajes de voz en Telegram
- 🧠 **Transcripción local**: Usa `faster-whisper` para transcribir audio sin APIs externas
- 📝 **Parser inteligente**: Detecta intenciones y extrae información usando reglas, regex y fuzzy matching
- 👥 **Gestión de clientes**: Identificación automática de clientes con coincidencia difusa
- 📅 **Google Calendar**: Integración opcional para sincronizar tareas
- 🌐 **Panel web**: Interfaz web para administración avanzada
- 💾 **SQLite**: Base de datos ligera y portable

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Componentes

```
┌─────────────────┐
│   Telegram Bot  │
│   (Usuario)     │
└────────┬────────┘
         │ Mensaje de voz
         ▼
┌─────────────────────────────────┐
│         Flask App (app.py)       │
│  ┌───────────────────────────┐  │
│  │   Webhook Handler         │  │
│  │   /webhook                │  │
│  └───────────┬───────────────┘  │
│              │                   │
│  ┌───────────▼───────────────┐  │
│  │  TelegramBotHandler       │  │
│  │  (telegram_bot.py)        │  │
│  └───────────┬───────────────┘  │
└──────────────┼──────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
┌────────┐ ┌──────────┐ ┌──────────┐
│ Audio  │ │  Parser  │ │ Database │
│Pipeline│ │ (parser) │ │ (SQLite) │
└────────┘ └──────────┘ └──────────┘
```

### Flujo de Datos

1. **Usuario envía audio** → Telegram envía webhook a Flask
2. **Flask recibe webhook** → Procesa en thread separado
3. **TelegramBotHandler** → Descarga audio y lo procesa
4. **AudioPipeline** → Convierte y transcribe audio
5. **Parser** → Detecta intención y extrae entidades
6. **Database** → Guarda/consulta datos
7. **Respuesta** → Bot responde al usuario

---

## 🔧 Componentes Principales

### 1. `app.py` - Aplicación Flask Principal

**Responsabilidades:**
- Inicializar la aplicación Flask
- Manejar webhooks de Telegram
- Servir el panel web de administración
- Gestionar autenticación web
- Coordinar inicialización del bot de Telegram

**Puntos Clave:**
- Usa **Gunicorn** en producción
- Inicialización **lazy** del bot (solo cuando llega el primer webhook)
- Event loop separado para procesamiento asíncrono de Telegram
- ThreadPoolExecutor para procesar actualizaciones sin bloquear

**Rutas Principales:**
- `/webhook` - Recibe actualizaciones de Telegram
- `/admin/login` - Login del panel web
- `/admin/tasks` - Lista de tareas
- `/admin/clients` - Gestión de clientes
- `/admin/tasks/<id>/solution` - Editar solución de tarea

### 2. `telegram_bot.py` - Lógica del Bot

**Clase Principal:** `TelegramBotHandler`

**Métodos Principales:**

- `handle_voice_message()` - Procesa mensajes de voz
- `handle_text_message()` - Procesa mensajes de texto (botones)
- `handle_callback_query()` - Maneja callbacks de botones inline
- `_handle_intent()` - Procesa intenciones detectadas
- `_show_pending_tasks_text()` - Muestra tareas pendientes
- `_show_close_tasks_menu_text()` - Menú para cerrar tareas
- `_show_ampliar_tasks_menu_text()` - Menú para ampliar tareas

**Botones Persistentes:**
- 📋 Mostrar tareas pendientes
- ✅ Cerrar tareas
- 📝 Ampliar tareas

**Estados de Usuario:**
- `user_states` - Diccionario que guarda estados temporales (ej: usuario en modo "ampliar tarea")

### 3. `audio_pipeline.py` - Procesamiento de Audio

**Funciones Principales:**

- `convert_to_wav()` - Convierte audio a WAV 16kHz mono usando ffmpeg
- `transcribe_audio()` - Transcribe audio usando faster-whisper
- `process_audio_from_file()` - Pipeline completo: conversión + transcripción
- `_get_whisper_model()` - Carga modelo Whisper (carga única, thread-safe)

**Características:**
- Modelo global cargado una sola vez (optimización de memoria)
- Thread-safe con locks
- Filtros de audio para mejorar calidad (highpass, compressor)
- Manejo de errores con fallbacks
- Logging detallado para debugging

**Modelo Whisper:**
- Por defecto: `base` (balance memoria/precisión)
- Device: `cpu`
- Compute type: `int8` (optimizado para memoria)
- Idioma: Español (`es`)

### 4. `parser.py` - Parser de Intenciones

**Clase Principal:** `IntentParser`

**Intenciones Soportadas:**
- `CREAR` - Crear nueva tarea
- `LISTAR` - Listar tareas
- `CERRAR` - Marcar tarea como completada
- `REPROGRAMAR` - Cambiar fecha de tarea
- `CAMBIAR_PRIORIDAD` - Modificar prioridad

**Extracción de Entidades:**
- **Cliente**: Fuzzy matching con base de datos (rapidfuzz)
- **Fecha**: Parsing con `dateparser` (español)
- **Prioridad**: Detección de palabras clave (urgente, importante, etc.)
- **Título**: Texto restante después de extraer entidades

**Fuzzy Matching de Clientes:**
- ≥85% similitud: Selección automática
- 70-84% similitud: Pide confirmación
- <70% similitud: Ofrece crear nuevo cliente

### 5. `database.py` - Base de Datos SQLite

**Clase Principal:** `Database`

**Tablas:**

**`clients`**
- `id` (INTEGER PRIMARY KEY)
- `name` (TEXT UNIQUE)
- `created_at` (TIMESTAMP)

**`tasks`**
- `id` (INTEGER PRIMARY KEY)
- `title` (TEXT)
- `client_id` (INTEGER, FK a clients)
- `due_date` (DATE)
- `priority` (TEXT: 'low', 'normal', 'high', 'urgent')
- `status` (TEXT: 'pending', 'completed')
- `created_at` (TIMESTAMP)
- `completed_at` (TIMESTAMP, nullable)
- `solution` (TEXT, nullable) - Solución/resolución manual
- `ampliacion` (TEXT, nullable) - Ampliación por voz

**Métodos Principales:**
- `init_db()` - Crea tablas si no existen
- `add_client()` - Añade cliente
- `get_client_by_name()` - Busca cliente por nombre
- `search_clients()` - Búsqueda con fuzzy matching
- `add_task()` - Crea tarea
- `get_tasks()` - Obtiene tareas con filtros
- `update_task()` - Actualiza tarea
- `complete_task()` - Marca tarea como completada

**Migraciones Automáticas:**
- El sistema detecta columnas faltantes y las añade automáticamente
- Compatible con versiones anteriores de la base de datos

### 6. `config.py` - Configuración

**Variables de Entorno Principales:**

**Telegram:**
- `TELEGRAM_BOT_TOKEN` - Token del bot (requerido)
- `TELEGRAM_WEBHOOK_URL` - URL del webhook
- `TELEGRAM_WEBHOOK_SECRET` - Secreto del webhook

**Aplicación:**
- `ADMIN_PASSWORD` - Contraseña del panel web
- `SECRET_KEY` - Clave secreta para sesiones Flask
- `SQLITE_PATH` - Ruta de la base de datos

**Audio:**
- `AUDIO_MAX_DURATION_SECONDS` - Duración máxima (default: 60s)
- `WHISPER_MODEL` - Modelo Whisper (default: 'base')

**Google Calendar (Opcional):**
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- `GOOGLE_CALENDAR_ID`

---

## 🔄 Flujo de Funcionamiento

### Flujo Completo: Crear Tarea por Voz

```
1. Usuario envía audio en Telegram
   ↓
2. Telegram envía webhook POST /webhook
   ↓
3. Flask recibe webhook
   ↓
4. app.py: Procesa en thread separado
   ↓
5. telegram_bot.py: handle_voice_message()
   ├─ Descarga archivo de audio
   ├─ Envía "Procesando audio..."
   └─ Llama a audio_pipeline.process_audio_from_file()
      ↓
6. audio_pipeline.py
   ├─ convert_to_wav() → ffmpeg convierte a WAV
   └─ transcribe_audio() → Whisper transcribe a texto
      ↓
7. parser.py: IntentParser.parse()
   ├─ Detecta intención: CREAR
   ├─ Extrae cliente (fuzzy matching)
   ├─ Extrae fecha (dateparser)
   ├─ Extrae prioridad
   └─ Extrae título
      ↓
8. telegram_bot.py: _handle_intent()
   ├─ Si cliente necesita confirmación → Pide confirmación
   ├─ Si fecha necesita confirmación → Pide confirmación
   └─ Si todo OK → database.add_task()
      ↓
9. Bot responde con confirmación y botones
```

### Flujo: Listar Tareas

```
1. Usuario presiona botón "📋 Mostrar tareas pendientes"
   ↓
2. telegram_bot.py: _show_pending_tasks_text()
   ├─ database.get_tasks(status='pending')
   └─ Formatea y envía lista
```

### Flujo: Cerrar Tarea

```
1. Usuario presiona botón "✅ Cerrar tareas"
   ↓
2. telegram_bot.py: _show_close_tasks_menu_text()
   ├─ database.get_tasks(status='pending')
   └─ Muestra lista con botones inline
      ↓
3. Usuario selecciona tarea
   ↓
4. telegram_bot.py: handle_callback_query()
   ├─ Pide confirmación
   └─ Si confirma → database.complete_task()
```

---

## 💾 Base de Datos

### Esquema Completo

```sql
-- Tabla de clientes
CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de tareas
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    client_id INTEGER,
    due_date DATE,
    priority TEXT DEFAULT 'normal',
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    solution TEXT,
    ampliacion TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);
```

### Índices Recomendados

- `clients.name` - Búsqueda rápida de clientes
- `tasks.status` - Filtrado de tareas
- `tasks.due_date` - Ordenamiento por fecha
- `tasks.client_id` - Joins eficientes

---

## 🤖 Funcionalidades del Bot

### Comandos por Voz

**Crear Tarea:**
- "Crear tarea llamar al cliente Alditraex mañana"
- "Tarea urgente para el cliente Test el lunes"
- "Recordar reunión con cliente X el viernes"

**Listar Tareas:**
- "Listar tareas pendientes"
- "Mostrar tareas de hoy"
- "Tareas de mañana"
- "Tareas de la semana"

**Cerrar Tarea:**
- "Da por hecha la tarea del cliente X"
- "Completar tarea llamar cliente Y"
- "Marcar como hecha la tarea Z"

**Reprogramar:**
- "Cambiar fecha de la tarea X al lunes"
- "Mover tarea Y para mañana"

**Cambiar Prioridad:**
- "Tarea urgente llamar cliente X"
- "Prioridad alta para tarea Y"

### Botones Persistentes

Siempre visibles en el teclado:

1. **📋 Mostrar tareas pendientes**
   - Muestra todas las tareas con estado "pending"
   - Formato: ID, título, cliente, fecha, prioridad

2. **✅ Cerrar tareas**
   - Muestra lista de tareas pendientes
   - Permite seleccionar y confirmar cierre

3. **📝 Ampliar tareas**
   - Muestra tareas no completadas
   - Permite añadir ampliación por voz
   - Guarda en campo `ampliacion`

### Funcionalidad de Ampliación

1. Usuario presiona "📝 Ampliar tareas"
2. Bot muestra lista de tareas
3. Usuario selecciona tarea
4. Bot pide que envíe audio con ampliación
5. Bot transcribe y guarda en `ampliacion`

---

## 🌐 Panel Web de Administración

### Acceso

- URL: `https://tu-dominio.com/admin/login`
- Credenciales: `ADMIN_PASSWORD`

### Funcionalidades

**Gestión de Tareas:**
- Ver todas las tareas (pendientes y completadas)
- Filtrar por fecha
- Ver detalles completos
- Editar solución/resolución manualmente
- Botón para añadir a Google Calendar

**Gestión de Clientes:**
- Ver lista de clientes
- Crear nuevos clientes
- Editar clientes existentes

**Características del Panel:**
- Diseño moderno con cards
- Filtros por fecha
- Badges de estado y prioridad
- Modales para editar soluciones
- Responsive design

### Estructura de Templates

- `base.html` - Template base con navbar
- `tasks.html` - Lista de tareas con filtros
- `clients.html` - Gestión de clientes
- `login.html` - Página de login

---

## 🎤 Procesamiento de Audio

### Pipeline Completo

```
Audio OGG (Telegram)
    ↓
[ffmpeg] Conversión
    ├─ Sample rate: 16kHz
    ├─ Canales: Mono
    ├─ Filtros: highpass + compressor
    └─ Formato: WAV
    ↓
[faster-whisper] Transcripción
    ├─ Modelo: base (CPU/int8)
    ├─ Idioma: Español
    ├─ Parámetros optimizados
    └─ VAD (Voice Activity Detection)
    ↓
Texto transcrito
```

### Optimizaciones de Memoria

**Para Render Free Tier (512MB):**
- Modelo: `base` (más ligero que `small`)
- Device: `cpu` (no GPU)
- Compute type: `int8` (menos memoria que float16)
- Carga única del modelo (reutilización)
- Pre-carga durante build

### Filtros de Audio

**highpass=f=80**
- Elimina frecuencias bajas (ruido)

**acompressor**
- Normaliza volumen
- Reduce picos de audio
- Mejora calidad de transcripción

---

## 🧠 Parser de Intenciones

### Detección de Intenciones

**Patrones por Intención:**

**CREAR:**
- "crear", "nueva", "añadir", "agregar"
- "tarea", "recordar", "recordatorio"

**LISTAR:**
- "listar", "mostrar", "ver"
- "pendientes", "hoy", "mañana", "semana"

**CERRAR:**
- "cerrar", "completar", "hecha", "terminada"
- "da por hecha", "marcar como"

**REPROGRAMAR:**
- "cambiar fecha", "mover", "reprogramar"
- "posponer", "adelantar"

**CAMBIAR_PRIORIDAD:**
- "urgente", "importante", "prioridad"
- "alta", "baja"

### Extracción de Entidades

**Cliente:**
```python
# Patrones detectados:
- "cliente X"
- "del cliente X"
- "para el cliente X"
- "con el cliente X"

# Fuzzy matching con base de datos
similarity = rapidfuzz.fuzz.ratio(nombre_detectado, cliente_db)
```

**Fecha:**
```python
# dateparser con idioma español
date = dateparser.parse(texto_fecha, languages=['es'])
```

**Prioridad:**
```python
# Palabras clave:
urgent_keywords = ['urgente', 'urgent', 'inmediato']
high_keywords = ['importante', 'alta', 'high']
low_keywords = ['baja', 'low', 'poco importante']
```

---

## ⚙️ Configuración

### Variables de Entorno Requeridas

```bash
# Telegram (Requerido)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Aplicación (Requerido)
ADMIN_PASSWORD=tu_contraseña_segura
SECRET_KEY=clave-secreta-aleatoria-muy-larga

# Base de datos (Opcional)
SQLITE_PATH=/ruta/a/app.db
```

### Variables Opcionales

```bash
# Telegram Webhook
TELEGRAM_WEBHOOK_URL=https://tu-dominio.com/webhook
TELEGRAM_WEBHOOK_SECRET=secreto-webhook

# Audio
AUDIO_MAX_DURATION_SECONDS=60
WHISPER_MODEL=base  # tiny, base, small, medium

# Google Calendar
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
GOOGLE_CALENDAR_ID=...
```

### Configuración Local

1. Crear archivo `.env`:
```env
TELEGRAM_BOT_TOKEN=tu_token
ADMIN_PASSWORD=tu_password
SECRET_KEY=tu_secret_key
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Ejecutar:
```bash
python app.py
```

---

## 🚀 Despliegue

### Despliegue en Render

**Configuración Básica:**

1. **Crear servicio Web en Render**
2. **Conectar repositorio Git**
3. **Configurar variables de entorno**
4. **Activar Persistent Disk** (IMPORTANTE)
   - Montar en `/opt/render/project/src/data`
   - Mínimo 1GB recomendado

**Build Command (automático desde render.yaml):**
```bash
apt-get update -qq && apt-get install -y -qq ffmpeg &&
pip install --upgrade pip &&
pip install -r requirements.txt &&
pip install ffmpeg-python &&
python preload_whisper_model.py
```

**Start Command:**
```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

**Configuración de Webhook:**

Después del despliegue, configurar webhook:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://tu-app.onrender.com/webhook",
    "secret_token": "tu_secreto"
  }'
```

### Optimizaciones para Render Free Tier

**Memoria (512MB límite):**
- Modelo Whisper: `base` (no `small`)
- Compute type: `int8` (no `float16`)
- Pre-carga del modelo durante build
- Carga única del modelo (reutilización)

**Rendimiento:**
- ThreadPoolExecutor para procesamiento paralelo
- Event loop separado para Telegram
- Timeout de 5 minutos para procesamiento de audio

---

## 🔍 Troubleshooting

### Problema: Bot no responde

**Síntomas:**
- Webhook recibido pero bot no responde
- Logs muestran "Application no inicializado"

**Solución:**
1. Verificar que `TELEGRAM_BOT_TOKEN` esté configurado
2. Verificar logs de inicialización
3. Esperar unos segundos (inicialización lazy)
4. Verificar que webhook esté configurado correctamente

### Problema: Error "Out of Memory"

**Síntomas:**
- Servicio se reinicia en Render
- Logs muestran "Ran out of memory"

**Solución:**
1. Cambiar `WHISPER_MODEL` a `base` o `tiny`
2. Verificar que se use `int8` (no `float16`)
3. Verificar que modelo se pre-carga durante build
4. Considerar upgrade a plan de pago

### Problema: Audio no se transcribe

**Síntomas:**
- Bot responde "Procesando audio..." pero nunca termina
- Logs muestran descarga de modelo pero no transcripción

**Solución:**
1. Verificar logs de `audio_pipeline`
2. Verificar que modelo se haya cargado correctamente
3. Verificar que ffmpeg esté instalado
4. Verificar timeout (5 minutos máximo)

### Problema: Cliente no se detecta

**Síntomas:**
- Bot pide confirmación aunque cliente existe
- Bot ofrece crear cliente nuevo aunque existe

**Solución:**
1. Verificar nombre del cliente en base de datos
2. Verificar umbrales de fuzzy matching en `config.py`
3. Probar con nombre exacto
4. Verificar logs de `parser.py`

### Problema: Fecha no se detecta

**Síntomas:**
- Tarea se crea sin fecha
- Fecha incorrecta

**Solución:**
1. Usar expresiones claras: "mañana", "el lunes", "15 de enero"
2. Verificar logs de `dateparser`
3. Verificar idioma configurado (`languages=['es']`)

### Problema: Base de datos no persiste

**Síntomas:**
- Datos se pierden tras reinicio
- Tareas desaparecen

**Solución:**
1. **ACTIVAR Persistent Disk en Render**
2. Montar en `/opt/render/project/src/data`
3. Configurar `SQLITE_PATH=/opt/render/project/src/data/app.db`

---

## 📊 Métricas y Monitoreo

### Logs Importantes

**Inicialización:**
```
[INIT] Inicializando Application...
[INIT] Application.initialize() completado
[INIT] ✅ Application inicializado correctamente
```

**Procesamiento de Audio:**
```
[HANDLER] Iniciando procesamiento de audio para usuario X
[AUDIO_PIPELINE] Iniciando conversión...
[AUDIO_PIPELINE] Conversión completada
[WHISPER] Iniciando transcripción...
[WHISPER] Modelo obtenido, iniciando transcripción...
[WHISPER] Transcripción completada: X caracteres
```

**Webhook:**
```
[WEBHOOK] Recibida actualización X, tipo: message
[WEBHOOK] Actualización X enviada para procesamiento
```

### Puntos de Monitoreo

1. **Tiempo de respuesta del bot**
2. **Tasa de éxito de transcripciones**
3. **Uso de memoria** (especialmente en Render free tier)
4. **Errores de webhook**
5. **Tiempo de carga del modelo Whisper**

---

## 🔐 Seguridad

### Buenas Prácticas

1. **Nunca commitear tokens o secretos**
   - Usar `.env` y `.gitignore`
   - Variables de entorno en producción

2. **Webhook Secret**
   - Configurar `TELEGRAM_WEBHOOK_SECRET`
   - Validar en endpoint `/webhook`

3. **Contraseña Admin**
   - Usar contraseña fuerte
   - Cambiar contraseña por defecto

4. **Base de Datos**
   - Backup regular si es crítico
   - Persistent Disk en producción

---

## 📚 Referencias y Recursos

### Documentación Externa

- [python-telegram-bot](https://python-telegram-bot.org/)
- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [Flask](https://flask.palletsprojects.com/)
- [Render Documentation](https://render.com/docs)

### Archivos de Documentación del Proyecto

- `README.md` - Guía rápida de inicio
- `DEPLOY_RENDER.md` - Guía detallada de despliegue
- `CONFIGURAR_WEBHOOK.md` - Configuración de webhook
- `DIAGNOSTICO_BOT.md` - Diagnóstico de problemas
- `TELEGRAM_SETUP.md` - Configuración inicial de Telegram

---

## 📝 Notas Adicionales

### Limitaciones Conocidas

1. **Duración máxima de audio**: 60 segundos
2. **Memoria en Render free tier**: 512MB (limita modelo Whisper)
3. **Idioma**: Optimizado para español (otros idiomas pueden funcionar pero con menor precisión)
4. **Base de datos**: SQLite (no recomendado para alta concurrencia)

### Mejoras Futuras Posibles

1. Soporte para múltiples idiomas
2. Integración con más servicios de calendario
3. Notificaciones programadas
4. Exportación de datos (CSV, JSON)
5. API REST para integraciones externas
6. Dashboard con estadísticas

---

## 📞 Soporte

Para problemas o preguntas:

1. Revisar esta documentación completa
2. Consultar `DIAGNOSTICO_BOT.md` para problemas comunes
3. Revisar logs de la aplicación
4. Verificar configuración de variables de entorno

---

**Última actualización:** Enero 2026
**Versión del sistema:** 1.0

