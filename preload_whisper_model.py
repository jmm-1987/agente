"""Script para pre-descargar el modelo de Whisper durante el build"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def preload_model():
    """Pre-carga el modelo de Whisper para que esté disponible al iniciar"""
    try:
        # Importar config para obtener el modelo
        import config
        
        model_name = config.WHISPER_MODEL
        logger.info(f"Pre-cargando modelo Whisper: {model_name}")
        
        # Importar faster-whisper
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            logger.error("faster-whisper no está instalado")
            sys.exit(1)
        
        # Determinar device y compute_type
        device = "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        logger.info(f"Cargando modelo con device={device}, compute_type={compute_type}")
        
        try:
            # Cargar modelo (esto descargará si no está en caché)
            model = WhisperModel(model_name, device=device, compute_type=compute_type)
            logger.info(f"✅ Modelo {model_name} cargado correctamente")
        except Exception as e:
            logger.warning(f"Error con {device}/{compute_type}: {e}, intentando alternativas...")
            try:
                model = WhisperModel(model_name, device="cpu", compute_type="int8")
                logger.info(f"✅ Modelo {model_name} cargado con CPU/int8")
            except Exception as e2:
                logger.warning(f"Error con CPU/int8: {e2}, intentando sin compute_type...")
                try:
                    model = WhisperModel(model_name, device="cpu")
                    logger.info(f"✅ Modelo {model_name} cargado con CPU (sin compute_type)")
                except Exception as e3:
                    logger.error(f"Error cargando modelo: {e3}")
                    sys.exit(1)
        
        # Hacer una transcripción de prueba para asegurar que funciona
        logger.info("Realizando transcripción de prueba...")
        # Crear un archivo de audio silencioso temporal para prueba
        import tempfile
        import subprocess
        
        # Crear un archivo WAV silencioso de 1 segundo
        test_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        test_wav.close()
        
        try:
            # Generar 1 segundo de silencio a 16kHz mono
            subprocess.run([
                'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=16000:cl=mono',
                '-t', '1', '-y', test_wav.name
            ], capture_output=True, timeout=10, check=False)
            
            # Intentar transcribir (aunque sea silencio)
            segments, info = model.transcribe(test_wav.name, language="es")
            # Consumir al menos un segmento para asegurar que funciona
            list(segments)
            logger.info("✅ Transcripción de prueba completada")
        except Exception as e:
            logger.warning(f"Transcripción de prueba falló (puede ser normal): {e}")
        finally:
            # Limpiar archivo temporal
            if os.path.exists(test_wav.name):
                os.unlink(test_wav.name)
        
        logger.info("✅ Pre-carga del modelo completada exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"Error en pre-carga del modelo: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    preload_model()

