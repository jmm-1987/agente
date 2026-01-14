"""Pipeline de procesamiento de audio: Telegram → ffmpeg → faster-whisper"""
import os
import subprocess
from pathlib import Path
from typing import Optional
import threading
import config
from utils import clean_temp_files

# Modelo global de Whisper (cargado una sola vez)
_whisper_model = None
_model_lock = threading.Lock()

def is_model_loaded():
    """Verifica si el modelo ya está cargado"""
    return _whisper_model is not None


def download_telegram_audio(file_path: str, output_path: str) -> bool:
    """Descarga archivo de audio de Telegram usando el bot token"""
    import requests
    
    bot_token = config.TELEGRAM_BOT_TOKEN
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN no configurado")
    
    url = f"https://api.telegram.org/bot{bot_token}/getFile?file_path={file_path}"
    response = requests.get(url)
    
    if not response.ok:
        raise ValueError(f"Error al obtener info del archivo: {response.text}")
    
    file_info = response.json()
    if not file_info.get('ok'):
        raise ValueError(f"Error en respuesta de Telegram: {file_info}")
    
    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    file_response = requests.get(download_url, stream=True)
    
    if not file_response.ok:
        raise ValueError(f"Error al descargar archivo: {file_response.status_code}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        for chunk in file_response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return True


def convert_to_wav(input_path: str, output_path: str) -> bool:
    """Convierte audio a WAV 16kHz mono usando ffmpeg con mejoras de calidad"""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Archivo de entrada no existe: {input_path}")
    
    # Verificar duración del audio
    duration_cmd = [
        'ffprobe', '-v', 'error', '-show_entries',
        'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
        input_path
    ]
    
    try:
        result = subprocess.run(
            duration_cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            if duration > config.AUDIO_MAX_DURATION_SECONDS:
                raise ValueError(
                    f"Audio demasiado largo ({duration:.1f}s). "
                    f"Máximo: {config.AUDIO_MAX_DURATION_SECONDS}s"
                )
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
        if isinstance(e, ValueError):
            raise
        # Si ffprobe no está disponible, continuar pero advertir
    
    # Convertir a WAV 16kHz mono con mejoras de calidad
    # Primero intentar con filtros de audio mejorados
    cmd_with_filters = [
        'ffmpeg', '-i', input_path,
        '-ar', '16000',      # Sample rate 16kHz (óptimo para Whisper)
        '-ac', '1',          # Mono
        '-af', 'highpass=f=80,acompressor=threshold=0.089:ratio=9:attack=200:release=1000',  # Filtros de audio
        '-f', 'wav',         # Formato WAV
        '-y',                # Sobrescribir
        output_path
    ]
    
    # Comando básico sin filtros (fallback)
    cmd_basic = [
        'ffmpeg', '-i', input_path,
        '-ar', '16000',      # Sample rate 16kHz
        '-ac', '1',          # Mono
        '-f', 'wav',         # Formato WAV
        '-y',                # Sobrescribir
        output_path
    ]
    
    try:
        # Intentar primero con filtros
        result = subprocess.run(
            cmd_with_filters,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Si falla con filtros, intentar sin ellos
        if result.returncode != 0:
            result = subprocess.run(
                cmd_basic,
                capture_output=True,
                text=True,
                timeout=30
            )
        
        if result.returncode != 0:
            raise RuntimeError(
                f"Error en ffmpeg: {result.stderr}\n"
                f"Instala ffmpeg: https://ffmpeg.org/download.html"
            )
        
        if not os.path.exists(output_path):
            raise RuntimeError("ffmpeg no generó archivo de salida")
        
        return True
        
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg no está instalado. "
            "Instala desde: https://ffmpeg.org/download.html"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout al convertir audio")


def _get_whisper_model():
    """Obtiene el modelo de Whisper (carga una sola vez, thread-safe)"""
    global _whisper_model
    
    if _whisper_model is not None:
        return _whisper_model
    
    with _model_lock:
        # Doble verificación (double-check locking pattern)
        if _whisper_model is not None:
            return _whisper_model
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[WHISPER] Cargando modelo {config.WHISPER_MODEL} (primera vez, puede tardar unos minutos)...")
        
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper no está instalado. "
                "Instala con: pip install faster-whisper"
            )
        
        # Cargar modelo (se cachea automáticamente)
        # Para Render free tier, usar siempre CPU con int8 para minimizar memoria
        device = "cpu"
        compute_type = "int8"  # int8 usa menos memoria que float16/float32
        
        try:
            logger.info(f"[WHISPER] Intentando cargar modelo con device={device}, compute_type={compute_type}")
            _whisper_model = WhisperModel(config.WHISPER_MODEL, device=device, compute_type=compute_type)
            logger.info(f"[WHISPER] ✅ Modelo cargado correctamente con {device}/{compute_type}")
        except Exception as e:
            logger.warning(f"[WHISPER] Error con {device}/{compute_type}: {e}, intentando alternativas...")
            # Si falla con compute_type, intentar con int8 en CPU
            try:
                logger.info(f"[WHISPER] Intentando cargar con CPU/int8...")
                _whisper_model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
                logger.info(f"[WHISPER] ✅ Modelo cargado con CPU/int8")
            except Exception as e2:
                logger.warning(f"[WHISPER] Error con CPU/int8: {e2}, intentando sin compute_type...")
                # Último intento: solo el modelo sin compute_type
                try:
                    logger.info(f"[WHISPER] Intentando cargar con CPU (sin compute_type)...")
                    _whisper_model = WhisperModel(config.WHISPER_MODEL, device="cpu")
                    logger.info(f"[WHISPER] ✅ Modelo cargado con CPU (sin compute_type)")
                except Exception as e3:
                    logger.warning(f"[WHISPER] Error con CPU sin compute_type: {e3}, intentando configuración por defecto...")
                    _whisper_model = WhisperModel(config.WHISPER_MODEL)
                    logger.info(f"[WHISPER] ✅ Modelo cargado (configuración por defecto)")
        
        return _whisper_model


def transcribe_audio(audio_path: str, language: str = "es") -> str:
    """Transcribe audio usando faster-whisper con configuración optimizada para español"""
    import logging
    logger = logging.getLogger(__name__)
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Archivo de audio no existe: {audio_path}")
    
    logger.info(f"[WHISPER] Iniciando transcripción de {audio_path}")
    
    # Obtener modelo (cargado una sola vez)
    model = _get_whisper_model()
    logger.info(f"[WHISPER] Modelo obtenido, iniciando transcripción...")
    
    # Parámetros optimizados para mejor precisión en español
    # beam_size: número de hipótesis a considerar (mayor = más preciso pero más lento)
    # best_of: número de candidatos a generar (mayor = más preciso)
    # temperature: controla la aleatoriedad (0 = determinista, más preciso)
    # condition_on_previous_text: usa contexto previo para mejor precisión
    transcribe_options = {
        "language": language,
        "beam_size": 5,  # Balance entre precisión y velocidad
        "best_of": 5,
        "temperature": 0.0,  # Más determinista = más preciso
        "condition_on_previous_text": True,
        "initial_prompt": "Esta es una conversación en español sobre tareas y clientes.",
        "vad_filter": True,  # Filtrar silencios
        "vad_parameters": {
            "min_silence_duration_ms": 500
        }
    }
    
    # Transcribir con parámetros optimizados
    try:
        logger.info(f"[WHISPER] Llamando a model.transcribe()...")
        segments, info = model.transcribe(audio_path, **transcribe_options)
        logger.info(f"[WHISPER] model.transcribe() completado, procesando segmentos...")
    except TypeError as e:
        # Si algún parámetro no es válido, intentar con parámetros mínimos
        logger.warning(f"[WHISPER] Error con parámetros avanzados: {e}, intentando alternativas...")
        error_str = str(e).lower()
        if "vad" in error_str or "initial_prompt" in error_str:
            # Intentar sin parámetros avanzados
            try:
                logger.info(f"[WHISPER] Intentando sin parámetros avanzados...")
                segments, info = model.transcribe(
                    audio_path,
                    language=language,
                    beam_size=5,
                    temperature=0.0
                )
                logger.info(f"[WHISPER] Transcripción con parámetros básicos completada")
            except Exception as e2:
                logger.warning(f"[WHISPER] Error con parámetros básicos: {e2}, intentando solo con idioma...")
                # Último recurso: solo idioma
                segments, info = model.transcribe(audio_path, language=language)
                logger.info(f"[WHISPER] Transcripción con solo idioma completada")
        else:
            raise
    
    # Concatenar segmentos con mejor manejo de puntuación
    logger.info(f"[WHISPER] Iterando sobre segmentos...")
    text_parts = []
    segment_count = 0
    for segment in segments:
        segment_count += 1
        text = segment.text.strip()
        if text:
            text_parts.append(text)
            if segment_count % 10 == 0:  # Log cada 10 segmentos
                logger.info(f"[WHISPER] Procesados {segment_count} segmentos...")
    
    logger.info(f"[WHISPER] Total de segmentos procesados: {segment_count}")
    transcript = ' '.join(text_parts).strip()
    
    # Limpiar transcripción común: eliminar espacios múltiples, normalizar puntuación
    import re
    transcript = re.sub(r'\s+', ' ', transcript)  # Múltiples espacios a uno
    transcript = re.sub(r'\s+([.,;:!?])', r'\1', transcript)  # Espacios antes de puntuación
    transcript = transcript.strip()
    
    if not transcript:
        raise ValueError("No se pudo transcribir audio (audio vacío o sin voz)")
    
    return transcript


def process_audio_from_file(input_file: str) -> str:
    """Pipeline completo: conversión → transcripción (archivo ya descargado)"""
    import logging
    logger = logging.getLogger(__name__)
    
    temp_wav = None
    
    try:
        # 1. Convertir a WAV
        logger.info(f"[AUDIO_PIPELINE] Iniciando conversión de {input_file} a WAV...")
        temp_wav = os.path.join(config.TEMP_DIR, f"audio_{os.getpid()}.wav")
        convert_to_wav(input_file, temp_wav)
        logger.info(f"[AUDIO_PIPELINE] Conversión completada: {temp_wav}")
        
        # 2. Transcribir
        logger.info(f"[AUDIO_PIPELINE] Iniciando transcripción...")
        transcript = transcribe_audio(temp_wav)
        logger.info(f"[AUDIO_PIPELINE] Transcripción completada: {len(transcript)} caracteres")
        
        return transcript
        
    finally:
        # Limpiar archivos temporales
        if temp_wav:
            clean_temp_files(temp_wav)
        # El archivo de entrada también se limpia después
        if input_file and os.path.exists(input_file):
            clean_temp_files(input_file)

