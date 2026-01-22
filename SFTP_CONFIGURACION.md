# Configuración SFTP para Almacenamiento de Imágenes

Este documento explica cómo configurar el almacenamiento SFTP para las imágenes adjuntas a las tareas.

## Variables de Entorno en Render

Debes configurar las siguientes variables de entorno en tu proyecto de Render:

### Variables Requeridas

1. **`SFTP_HOST`**
   - Descripción: Dirección del servidor SFTP
   - Ejemplo: `access-5017125124.webspace-host.com`
   - **Valor de tu cuenta**: `access-5017125124.webspace-host.com`

2. **`SFTP_PORT`**
   - Descripción: Puerto del servidor SFTP
   - Valor por defecto: `22`
   - **Valor de tu cuenta**: `22`

3. **`SFTP_USERNAME`**
   - Descripción: Nombre de usuario para autenticación SFTP
   - Ejemplo: `a584814`
   - **Valor de tu cuenta**: `a584814`

4. **`SFTP_PASSWORD`**
   - Descripción: Contraseña para autenticación SFTP
   - **Valor de tu cuenta**: (La contraseña que estableciste para este acceso)

5. **`SFTP_REMOTE_PATH`**
   - Descripción: Ruta remota donde se guardarán las imágenes
   - Valor por defecto: `/images/tasks`
   - Ejemplo: `/images/tasks` o `/htdocs/images/tasks` (dependiendo de tu configuración)

### Variable Opcional

6. **`SFTP_WEB_DOMAIN`** (Opcional)
   - Descripción: Dominio web público para acceder a las imágenes
   - Ejemplo: `https://tudominio.com`
   - Nota: Solo necesaria si quieres generar URLs públicas para las imágenes

## Cómo Configurar en Render

1. Ve a tu proyecto en Render Dashboard
2. Navega a **Environment** (Entorno)
3. Haz clic en **Add Environment Variable** (Añadir Variable de Entorno)
4. Añade cada una de las variables anteriores con sus valores correspondientes
5. Guarda los cambios
6. Render reiniciará automáticamente tu aplicación

## Comportamiento

- **Si SFTP está configurado**: Las imágenes se suben al servidor SFTP y se borran del sistema local después de subirlas.
- **Si SFTP NO está configurado**: Las imágenes se guardan localmente en el directorio temporal (se perderán en cada despliegue).
- **Al completar una tarea**: Las imágenes asociadas se borran automáticamente del servidor SFTP.

## Instalación de Dependencias

El módulo `paramiko` ya está incluido en `requirements.txt` y se instalará automáticamente en el despliegue.

## Verificación

Para verificar que SFTP está funcionando correctamente:

1. Sube una imagen a través de Telegram
2. Revisa los logs de Render para ver mensajes como:
   - `SFTP configurado para access-5017125124.webspace-host.com:22`
   - `Imagen subida a SFTP: /images/tasks/[nombre_archivo].jpg`
3. Verifica que la imagen aparece en tu servidor SFTP en la ruta configurada

## Solución de Problemas

### Error: "SFTP no está habilitado"
- Verifica que todas las variables de entorno requeridas están configuradas
- Revisa que los valores son correctos (sin espacios adicionales)

### Error: "Error subiendo imagen a SFTP"
- Verifica las credenciales (usuario y contraseña)
- Verifica que el servidor SFTP es accesible desde Render
- Revisa que la ruta remota existe o tiene permisos para crearse
- Revisa los logs para más detalles del error

### Las imágenes se siguen guardando localmente
- Verifica que `paramiko` está instalado (debería instalarse automáticamente)
- Revisa los logs para ver si hay mensajes de advertencia sobre SFTP


