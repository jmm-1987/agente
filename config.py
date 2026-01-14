"""Configuración de la aplicación desde variables de entorno"""
import os
from pathlib import Path

# Cargar variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv no está instalado, usar variables de entorno del sistema
    pass

# Base directory
BASE_DIR = Path(__file__).parent

# SQLite Database
SQLITE_PATH = os.getenv('SQLITE_PATH', str(BASE_DIR / 'data' / 'app.db'))
DB_DIR = Path(SQLITE_PATH).parent
DB_DIR.mkdir(parents=True, exist_ok=True)

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')
TELEGRAM_WEBHOOK_SECRET = os.getenv('TELEGRAM_WEBHOOK_SECRET', '')

# Admin Web App
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-secret-key-in-production')

# Google Calendar (opcional)
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REFRESH_TOKEN = os.getenv('GOOGLE_REFRESH_TOKEN', '')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', '')
GOOGLE_CALENDAR_ENABLED = all([
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REFRESH_TOKEN,
    GOOGLE_CALENDAR_ID
])

# Audio Processing
AUDIO_MAX_DURATION_SECONDS = 60
TEMP_DIR = Path('/tmp') if Path('/tmp').exists() else Path(BASE_DIR / 'tmp')
TEMP_DIR.mkdir(exist_ok=True)

# Faster Whisper
# Modelos disponibles: tiny, base, small, medium, large-v2, large-v3
# Para Render free tier (512MB): usar 'base' o 'tiny'
# 'base' ofrece buen balance entre precisión y memoria (~150MB)
# 'tiny' es más ligero pero menos preciso (~75MB)
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')  # Cambiado a 'base' para mejor uso de memoria

# Parser thresholds
CLIENT_MATCH_THRESHOLD_AUTO = 85
CLIENT_MATCH_THRESHOLD_CONFIRM = 70
CLIENT_MATCH_MAX_CANDIDATES = 3

# Flask
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
