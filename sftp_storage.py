"""Módulo para manejar almacenamiento de imágenes en SFTP"""
import os
import logging
import config
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    logger.warning("paramiko no está instalado. Instala con: pip install paramiko")


class SFTPStorage:
    """Gestor de almacenamiento SFTP para imágenes"""
    
    def __init__(self):
        self.host = os.getenv('SFTP_HOST', '')
        self.port = int(os.getenv('SFTP_PORT', '22'))
        self.username = os.getenv('SFTP_USERNAME', '')
        self.password = os.getenv('SFTP_PASSWORD', '')
        self.remote_path = os.getenv('SFTP_REMOTE_PATH', '/images/tasks')
        self.enabled = bool(self.host and self.username and self.password and PARAMIKO_AVAILABLE)
        
        if not PARAMIKO_AVAILABLE:
            logger.warning("SFTP deshabilitado: paramiko no está instalado")
        elif not self.enabled:
            logger.warning(
                f"SFTP deshabilitado: faltan variables de entorno. "
                f"Host: {'✓' if self.host else '✗'}, "
                f"Username: {'✓' if self.username else '✗'}, "
                f"Password: {'✓' if self.password else '✗'}"
            )
        else:
            logger.info(f"✅ SFTP configurado para {self.host}:{self.port}, ruta remota: {self.remote_path}")
    
    def _get_connection(self):
        """Crea y retorna una conexión SFTP"""
        if not self.enabled:
            raise RuntimeError("SFTP no está habilitado")
        
        transport = paramiko.Transport((self.host, self.port))
        transport.connect(username=self.username, password=self.password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp, transport
    
    def upload_image(self, local_file_path: str, remote_filename: str) -> str:
        """
        Sube una imagen al servidor SFTP
        
        Args:
            local_file_path: Ruta local del archivo
            remote_filename: Nombre del archivo en el servidor remoto
            
        Returns:
            Ruta remota del archivo subido
        """
        if not self.enabled:
            raise RuntimeError("SFTP no está habilitado")
        
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Archivo local no encontrado: {local_file_path}")
        
        try:
            logger.info(f"Conectando a SFTP {self.host}:{self.port}...")
            sftp, transport = self._get_connection()
            logger.info("Conexión SFTP establecida")
            
            # Asegurar que el directorio remoto existe
            try:
                logger.info(f"Verificando directorio remoto: {self.remote_path}")
                sftp.chdir(self.remote_path)
                logger.info(f"Directorio remoto existe: {self.remote_path}")
            except IOError as e:
                logger.info(f"Directorio remoto no existe, creándolo: {self.remote_path} (error: {e})")
                # Crear directorio si no existe
                self._create_remote_directory(sftp, self.remote_path)
                sftp.chdir(self.remote_path)
                logger.info(f"Directorio remoto creado exitosamente: {self.remote_path}")
            
            # Subir archivo
            remote_file_path = f"{self.remote_path}/{remote_filename}"
            logger.info(f"Subiendo archivo {local_file_path} a {remote_file_path}...")
            file_size = os.path.getsize(local_file_path)
            logger.info(f"Tamaño del archivo local: {file_size} bytes")
            sftp.put(local_file_path, remote_file_path)
            logger.info(f"Archivo subido exitosamente a {remote_file_path}")
            
            # Verificar que el archivo existe
            try:
                stat = sftp.stat(remote_file_path)
                logger.info(f"Archivo verificado en SFTP: {remote_file_path}, tamaño: {stat.st_size} bytes")
            except Exception as e:
                logger.warning(f"No se pudo verificar el archivo subido: {e}")
            
            sftp.close()
            transport.close()
            
            logger.info(f"✅ Imagen subida a SFTP: {remote_file_path}")
            return remote_file_path
            
        except Exception as e:
            logger.error(f"Error subiendo imagen a SFTP: {e}", exc_info=True)
            raise
    
    def delete_image(self, remote_file_path: str) -> bool:
        """
        Borra una imagen del servidor SFTP
        
        Args:
            remote_file_path: Ruta remota del archivo a borrar
            
        Returns:
            True si se borró correctamente, False en caso contrario
        """
        if not self.enabled:
            logger.warning("SFTP no está habilitado, no se puede borrar")
            return False
        
        try:
            sftp, transport = self._get_connection()
            
            # Extraer solo el nombre del archivo si viene con ruta completa
            filename = os.path.basename(remote_file_path)
            remote_path = f"{self.remote_path}/{filename}"
            
            try:
                sftp.remove(remote_path)
                logger.info(f"Imagen borrada de SFTP: {remote_path}")
                deleted = True
            except IOError as e:
                logger.warning(f"Imagen no encontrada en SFTP para borrar: {remote_path} - {e}")
                deleted = False
            
            sftp.close()
            transport.close()
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error borrando imagen de SFTP: {e}", exc_info=True)
            return False
    
    def _create_remote_directory(self, sftp, remote_path: str):
        """Crea un directorio remoto recursivamente"""
        try:
            logger.info(f"Creando directorio: {remote_path}")
            sftp.mkdir(remote_path)
            logger.info(f"Directorio creado: {remote_path}")
        except IOError as e:
            logger.info(f"No se pudo crear directorio {remote_path}, intentando crear padre: {e}")
            # Si falla, intentar crear el directorio padre primero
            parent = os.path.dirname(remote_path)
            if parent and parent != '/':
                self._create_remote_directory(sftp, parent)
            try:
                sftp.mkdir(remote_path)
                logger.info(f"Directorio creado después de crear padre: {remote_path}")
            except IOError as e2:
                logger.error(f"Error creando directorio {remote_path}: {e2}")
                raise
    
    def get_public_url(self, remote_file_path: str) -> str:
        """
        Genera la URL pública de una imagen
        
        Args:
            remote_file_path: Ruta remota del archivo
            
        Returns:
            URL pública para acceder a la imagen
        """
        # Si tienes un dominio web configurado para servir las imágenes
        web_domain = os.getenv('SFTP_WEB_DOMAIN', '')
        if web_domain:
            filename = os.path.basename(remote_file_path)
            return f"{web_domain}/images/tasks/{filename}"
        
        # Si no hay dominio configurado, retornar la ruta remota
        return remote_file_path


# Instancia global
sftp_storage = SFTPStorage()

