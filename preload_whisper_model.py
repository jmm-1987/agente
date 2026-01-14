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
        
        # Para Render free tier, usar siempre CPU con int8 para minimizar memoria
        device = "cpu"
        compute_type = "int8"
        
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
        
        # El modelo ya está cargado y cacheado, no necesitamos hacer prueba de transcripción
        # El simple hecho de cargar el modelo asegura que esté descargado y disponible
        
        logger.info("✅ Pre-carga del modelo completada exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"Error en pre-carga del modelo: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    preload_model()

