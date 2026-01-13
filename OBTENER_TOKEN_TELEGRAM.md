# Cómo Obtener el Token y Username de tu Bot de Telegram

## Paso 1: Abrir BotFather en Telegram

1. Abre la aplicación **Telegram** (móvil o escritorio)
2. En la barra de búsqueda, escribe: **@BotFather**
3. Abre la conversación con **BotFather** (tiene un ícono de robot azul ✅)

## Paso 2: Crear un Nuevo Bot

1. En la conversación con BotFather, escribe: `/newbot`
2. BotFather te preguntará: **"Alright, a new bot. How are we going to call it? Please choose a name for your bot."**
   - Responde con el **nombre** que quieras (ej: "Mi Agenda Bot" o "Agenda Personal")
   - Este es el nombre que verán los usuarios, puede tener espacios y emojis

3. BotFather te preguntará: **"Good. Now let's choose a username for your bot. It must end in `bot`. Like this, for example: TetrisBot or tetris_bot."**
   - Responde con un **username único** que termine en `bot`
   - Ejemplos válidos: `mi_agenda_bot`, `agenda_personal_bot`, `miagendabot`
   - **NO puede tener espacios ni mayúsculas** (solo minúsculas, números y guiones bajos)
   - Si el username ya existe, BotFather te pedirá otro

## Paso 3: Obtener el Token

Después de crear el bot, BotFather te mostrará un mensaje como este:

```
Done! Congratulations on your new bot. You will find it at t.me/mi_agenda_bot. You can now add a description, about section and profile picture for your bot, see /help for a list of commands. Use this token to access the HTTP API:

1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890

Keep your token secure and store it safely, it can be used by anyone to control your bot.
```

### 📋 Información que necesitas:

1. **TOKEN**: Es la línea larga que empieza con números (ej: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890`)
   - **Cópialo completo** (incluye los dos puntos `:`)
   - Este es el que vas a poner en tu archivo `.env` como `TELEGRAM_BOT_TOKEN`

2. **USERNAME**: Es la parte después de `t.me/` (ej: `mi_agenda_bot`)
   - Este es el nombre que usarás para buscar tu bot en Telegram
   - No es necesario ponerlo en el `.env`, solo lo necesitas para encontrar el bot

## Paso 4: Verificar que Funcionó

1. Copia el **TOKEN** completo
2. Abre tu archivo `.env` y pega el token:
   ```env
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
   ```

3. Para encontrar tu bot en Telegram:
   - Busca en Telegram: `@tu_username_bot` (el que elegiste)
   - O abre el enlace que BotFather te dio: `t.me/tu_username_bot`

## Comandos Útiles de BotFather

- `/token` - Ver el token de tu bot actual
- `/revoke` - Revocar el token actual y generar uno nuevo (si lo compartiste por error)
- `/mybots` - Ver lista de tus bots
- `/setdescription` - Cambiar la descripción del bot
- `/setabouttext` - Cambiar el texto "About" del bot

## ⚠️ IMPORTANTE - Seguridad

- **NUNCA** compartas tu token públicamente
- **NUNCA** lo subas a GitHub (ya está protegido con `.gitignore`)
- Si accidentalmente lo compartes, usa `/revoke` en BotFather inmediatamente
- El token es como una contraseña: quien lo tenga puede controlar tu bot

## Ejemplo Completo

**Mensaje de BotFather:**
```
Done! Congratulations on your new bot. You will find it at t.me/mi_agenda_bot. 
Use this token to access the HTTP API:

1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
```

**En tu archivo .env:**
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
ADMIN_PASSWORD=mi_contraseña_segura
SECRET_KEY=clave-secreta-aleatoria
```

**Para buscar el bot:**
- Busca en Telegram: `@mi_agenda_bot`




