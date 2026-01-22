"""Módulo para almacenamiento SFTP de imágenes"""
import os
import logging

logger = logging.getLogger(__name__)

# Verificar si paramiko está disponible
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    logger.warning("paramiko no está instalado. SFTP no estará disponible.")


class SFTPStorage:
    """Clase para manejar almacenamiento SFTP de imágenes"""
    
    def __init__(self):
        self.host = os.getenv('SFTP_HOST', '')
        self.port = int(os.getenv('SFTP_PORT', '22'))
        self.username = os.getenv('SFTP_USERNAME', '')
        self.password = os.getenv('SFTP_PASSWORD', '')
        self.remote_path = os.getenv('SFTP_REMOTE_PATH', '/images/tasks')
        self.web_domain = os.getenv('SFTP_WEB_DOMAIN', '')
        
        # Verificar si SFTP está habilitado
        self.enabled = (
            PARAMIKO_AVAILABLE and
            self.host and
            self.username and
            self.password
        )
        
        if self.enabled:
            logger.info(f"SFTP configurado para {self.host}:{self.port}")
        else:
            logger.warning(
                f"SFTP no está habilitado. "
                f"Host: {self.host or 'NO CONFIGURADO'}, "
                f"Username: {self.username or 'NO CONFIGURADO'}, "
                f"Password: {'✓' if self.password else '✗'}, "
                f"Paramiko disponible: {PARAMIKO_AVAILABLE}"
            )
    
    def _get_connection(self):
        """Obtiene una conexión SFTP"""
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
            local_file_path: Ruta local del archivo a subir
            remote_filename: Nombre del archivo en el servidor remoto
            
        Returns:
            Ruta remota completa del archivo subido
        """
        if not self.enabled:
            raise RuntimeError("SFTP no está habilitado")
        
        sftp, transport = self._get_connection()
        
        try:
            # Asegurar que el directorio remoto existe
            try:
                sftp.mkdir(self.remote_path)
            except IOError:
                # El directorio ya existe, está bien
                pass
            
            # Construir ruta remota completa
            remote_file_path = f"{self.remote_path}/{remote_filename}"
            
            # Subir archivo
            sftp.put(local_file_path, remote_file_path)
            logger.info(f"Imagen subida a SFTP: {remote_file_path}")
            
            return remote_file_path
        finally:
            sftp.close()
            transport.close()
    
    def delete_image(self, remote_file_path: str):
        """
        Elimina una imagen del servidor SFTP
        
        Args:
            remote_file_path: Ruta remota del archivo a eliminar
        """
        if not self.enabled:
            raise RuntimeError("SFTP no está habilitado")
        
        sftp, transport = self._get_connection()
        
        try:
            sftp.remove(remote_file_path)
            logger.info(f"Imagen eliminada de SFTP: {remote_file_path}")
        except FileNotFoundError:
            logger.warning(f"Archivo no encontrado en SFTP: {remote_file_path}")
        finally:
            sftp.close()
            transport.close()


# Crear instancia global
sftp_storage = SFTPStorage()
