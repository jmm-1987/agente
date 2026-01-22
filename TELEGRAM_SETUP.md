# Guía de Configuración de Telegram Bot

## Paso 1: Crear el Bot en Telegram

1. Abre Telegram y busca **@BotFather**
2. Envía el comando `/newbot`
3. Sigue las instrucciones:
   - Elige un **nombre** para tu bot (ej: "Mi Agenda Bot")
   - Elige un **username** único que termine en `bot` (ej: "mi_agenda_bot")
4. BotFather te dará un **TOKEN**. **¡GUÁRDALO BIEN!** Se verá algo así:
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

## Paso 2: Configurar Variables de Entorno

### Opción A: Usar archivo .env (Recomendado)

1. Crea un archivo `.env` en la raíz del proyecto (junto a `app.py`)
2. Copia el contenido de `.env.example` y completa con tus valores:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_PASSWORD=tu_contraseña_segura_aqui
SECRET_KEY=clave-secreta-aleatoria-muy-larga-y-segura
```

3. **IMPORTANTE**: El archivo `.env` ya está en `.gitignore`, así que NO se subirá a GitHub

### Opción B: Variables de entorno del sistema

**Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN="tu_token_aqui"
$env:ADMIN_PASSWORD="tu_contraseña"
$env:SECRET_KEY="tu_clave_secreta"
```

**Linux/Mac:**
```bash
export TELEGRAM_BOT_TOKEN="tu_token_aqui"
export ADMIN_PASSWORD="tu_contraseña"
export SECRET_KEY="tu_clave_secreta"
```

## Paso 3: Instalar python-dotenv (para leer .env)

Si usas archivo `.env`, instala `python-dotenv`:

```bash
py -m pip install python-dotenv
```

Luego actualiza `config.py` para cargar el archivo `.env` automáticamente.

## Paso 4: Ejecutar la Aplicación

```bash
python app.py
```

Deberías ver en la consola:
```
Bot de Telegram iniciado en modo polling
```

## Paso 5: Probar el Bot

1. Abre Telegram
2. Busca tu bot por su username (ej: `@mi_agenda_bot`)
3. Envía un mensaje de voz al bot
4. El bot debería responder procesando el audio

## Modo Local vs Producción

- **Local**: El bot usa **polling** (consulta Telegram cada cierto tiempo)
- **Producción**: El bot usa **webhook** (Telegram envía actualizaciones a tu servidor)

Para producción, necesitarás:
- Configurar `TELEGRAM_WEBHOOK_URL` con la URL de tu servidor
- Configurar `TELEGRAM_WEBHOOK_SECRET` (opcional pero recomendado)

## Solución de Problemas

### Error: "TELEGRAM_BOT_TOKEN no configurado"
- Verifica que la variable de entorno esté configurada correctamente
- Si usas `.env`, asegúrate de que `python-dotenv` esté instalado

### Error: "Bot no responde"
- Verifica que el token sea correcto
- Asegúrate de que el bot esté iniciado (deberías ver el mensaje en consola)
- Revisa los logs para ver errores

### El bot no procesa audio
- Verifica que `faster-whisper` esté instalado (requiere Rust)
- Verifica que `ffmpeg` esté instalado y en PATH

## Seguridad

✅ **NUNCA** subas el archivo `.env` a GitHub
✅ **NUNCA** compartas tu token públicamente
✅ El archivo `.env` ya está en `.gitignore` por seguridad

Si accidentalmente subes el token a GitHub:
1. Ve a BotFather y usa `/revoke` para revocar el token
2. Crea un nuevo bot con `/newbot`
3. Actualiza el token en tu `.env`











