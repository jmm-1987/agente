"""Pipeline de procesamiento de audio: Telegram → ffmpeg → faster-whisper"""
import os
import subprocess
from pathlib import Path
from typing import Optional
import config
from utils import clean_temp_files


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


def transcribe_audio(audio_path: str, language: str = "es") -> str:
    """Transcribe audio usando faster-whisper con configuración optimizada para español"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper no está instalado. "
            "Instala con: pip install faster-whisper"
        )
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Archivo de audio no existe: {audio_path}")
    
    # Cargar modelo (se cachea automáticamente)
    # Intentar usar GPU si está disponible, sino CPU
    device = "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    
    try:
        model = WhisperModel(config.WHISPER_MODEL, device=device, compute_type=compute_type)
    except Exception as e:
        # Si falla con compute_type, intentar con int8 en CPU
        try:
            model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
        except Exception:
            # Último intento: solo el modelo sin compute_type
            try:
                model = WhisperModel(config.WHISPER_MODEL, device="cpu")
            except Exception:
                model = WhisperModel(config.WHISPER_MODEL)
    
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
        segments, info = model.transcribe(audio_path, **transcribe_options)
    except TypeError as e:
        # Si algún parámetro no es válido, intentar con parámetros mínimos
        error_str = str(e).lower()
        if "vad" in error_str or "initial_prompt" in error_str:
            # Intentar sin parámetros avanzados
            try:
                segments, info = model.transcribe(
                    audio_path,
                    language=language,
                    beam_size=5,
                    temperature=0.0
                )
            except Exception:
                # Último recurso: solo idioma
                segments, info = model.transcribe(audio_path, language=language)
        else:
            raise
    
    # Concatenar segmentos con mejor manejo de puntuación
    text_parts = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            text_parts.append(text)
    
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
    temp_wav = None
    
    try:
        # 1. Convertir a WAV
        temp_wav = os.path.join(config.TEMP_DIR, f"audio_{os.getpid()}.wav")
        convert_to_wav(input_file, temp_wav)
        
        # 2. Transcribir
        transcript = transcribe_audio(temp_wav)
        
        return transcript
        
    finally:
        # Limpiar archivos temporales
        if temp_wav:
            clean_temp_files(temp_wav)
        # El archivo de entrada también se limpia después
        if input_file and os.path.exists(input_file):
            clean_temp_files(input_file)

