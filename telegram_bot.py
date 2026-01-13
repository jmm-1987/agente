"""Lógica del bot de Telegram"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import os
import database
import parser
import audio_pipeline
import config
from utils import normalize_text


class TelegramBotHandler:
    """Manejador de comandos y mensajes del bot"""
    
    def __init__(self):
        self.db = database.db
        self.parser = parser.IntentParser()
        # Estado de usuarios: {user_id: {'action': 'ampliar_task', 'task_id': int}}
        self.user_states = {}
    
    def _get_action_buttons(self) -> InlineKeyboardMarkup:
        """Retorna botones de acción siempre disponibles (inline)"""
        keyboard = [
            [
                InlineKeyboardButton("📋 Mostrar tareas pendientes", callback_data="show_pending_tasks"),
                InlineKeyboardButton("✅ Cerrar tareas", callback_data="close_tasks_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_reply_keyboard(self) -> ReplyKeyboardMarkup:
        """Retorna teclado de respuesta que siempre está visible"""
        keyboard = [
            [
                KeyboardButton("📋 Mostrar tareas pendientes"),
                KeyboardButton("✅ Cerrar tareas")
            ],
            [
                KeyboardButton("📝 Ampliar tareas")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Procesa mensajes de texto"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[HANDLER] handle_text_message llamado para update {update.update_id}")
        
        text = update.message.text
        
        if not text:
            logger.warning(f"[HANDLER] Mensaje sin texto en update {update.update_id}")
            return
        
        text_lower = text.lower().strip()
        reply_markup = self._get_reply_keyboard()
        logger.info(f"[HANDLER] Procesando texto: {text_lower[:50]}")
        
        # Manejar botones del teclado
        if text == "📋 Mostrar tareas pendientes":
            user = update.effective_user
            await self._show_pending_tasks_text(update, user)
            return
        
        if text == "✅ Cerrar tareas":
            user = update.effective_user
            await self._show_close_tasks_menu_text(update, user)
            return
        
        if text == "📝 Ampliar tareas":
            user = update.effective_user
            await self._show_ampliar_tasks_menu_text(update, user)
            return
        
        # Comandos de ayuda
        if text_lower in ['/start', '/help', 'ayuda', 'help']:
            await update.message.reply_text(
                "👋 ¡Hola! Soy tu bot de agenda.\n\n"
                "📝 **Cómo usarme:**\n"
                "• Envía un **mensaje de voz** para crear tareas\n"
                "• Ejemplos de comandos por voz:\n"
                "  - 'Crear tarea llamar al cliente Alditraex mañana'\n"
                "  - 'Listar tareas pendientes'\n"
                "  - 'Da por hecha la tarea del cliente Alditraex'\n\n"
                "🎤 **Importante:** Solo respondo a mensajes de voz.\n"
                "Envía un audio con tu comando para empezar.",
                reply_markup=reply_markup
            )
            return
        
        # Si es texto normal, explicar que necesita ser voz
        await update.message.reply_text(
            "👋 Hola! Este bot funciona con **mensajes de voz**.\n\n"
            "🎤 Por favor, envía un mensaje de voz con tu comando.\n\n"
            "Ejemplos:\n"
            "• 'Crear tarea llamar al cliente mañana'\n"
            "• 'Listar tareas pendientes'\n"
            "• 'Da por hecha la tarea del cliente X'\n\n"
            "Escribe /help para más información.",
            reply_markup=reply_markup
        )
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Procesa mensaje de voz"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[HANDLER] handle_voice_message llamado para update {update.update_id}")
        
        user = update.effective_user
        voice = update.message.voice
        
        reply_markup = self._get_reply_keyboard()
        
        if not voice:
            await update.message.reply_text("❌ No se detectó audio en el mensaje.", reply_markup=reply_markup)
            return
        
        # Verificar duración
        if voice.duration > config.AUDIO_MAX_DURATION_SECONDS:
            await update.message.reply_text(
                f"❌ Audio demasiado largo ({voice.duration}s). "
                f"Máximo: {config.AUDIO_MAX_DURATION_SECONDS}s",
                reply_markup=reply_markup
            )
            return
        
        # Procesar audio
        try:
            await update.message.reply_text("🎤 Procesando audio...", reply_markup=reply_markup)
            
            # Obtener archivo de audio
            file = await context.bot.get_file(voice.file_id)
            
            # Descargar archivo temporalmente
            import tempfile
            temp_ogg = os.path.join(config.TEMP_DIR, f"audio_{user.id}_{voice.file_id}.ogg")
            await file.download_to_drive(temp_ogg)
            
            # Pipeline completo: convertir y transcribir
            transcript = audio_pipeline.process_audio_from_file(temp_ogg)
            
            if not transcript:
                await update.message.reply_text("❌ No se pudo transcribir el audio.", reply_markup=reply_markup)
                return
            
            # Verificar si el usuario está en modo "ampliar tarea"
            user_state = self.user_states.get(user.id)
            if user_state and user_state.get('action') == 'ampliar_task':
                # Procesar como ampliación de tarea
                task_id = user_state.get('task_id')
                await self._add_ampliacion_to_task(update, task_id, transcript, user)
                # Limpiar estado
                del self.user_states[user.id]
                return
            
            # Parsear intención y entidades
            parsed = self.parser.parse(transcript)
            
            # Procesar según intención
            await self._handle_intent(update, context, parsed, user)
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"Error en handle_voice_message: {error_msg}")
            print(f"Traceback: {error_trace}")
            
            reply_markup = self._get_reply_keyboard()
            
            if "ffmpeg" in error_msg.lower():
                await update.message.reply_text(
                    "❌ Error: ffmpeg no está instalado o no está en PATH.\n"
                    "Instala ffmpeg: https://ffmpeg.org/download.html",
                    reply_markup=reply_markup
                )
            elif "faster-whisper" in error_msg.lower():
                await update.message.reply_text(
                    "❌ Error: faster-whisper no está instalado.\n"
                    "Instala con: pip install faster-whisper",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    f"❌ Error al procesar audio: {error_msg}",
                    reply_markup=reply_markup
                )
    
    async def _handle_intent(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                            parsed: dict, user):
        """Procesa intención parseada"""
        intent = parsed['intent']
        entities = parsed['entities']
        
        try:
            if intent == 'CREAR':
                await self._handle_create_task(update, context, parsed, user)
            elif intent == 'LISTAR':
                await self._handle_list_tasks(update, context, parsed, user)
            elif intent == 'CERRAR':
                await self._handle_close_task(update, context, parsed, user)
            elif intent == 'REPROGRAMAR':
                await self._handle_reschedule_task(update, context, parsed, user)
            elif intent == 'CAMBIAR_PRIORIDAD':
                await self._handle_change_priority(update, context, parsed, user)
            else:
                reply_markup = self._get_reply_keyboard()
                await update.message.reply_text(
                    "❓ No entendí la intención. Intenta de nuevo.",
                    reply_markup=reply_markup
                )
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"Error en _handle_intent ({intent}): {error_msg}")
            print(f"Traceback: {error_trace}")
            await update.message.reply_text(
                f"❌ Error al procesar la intención '{intent}': {error_msg}"
            )
    
    async def _handle_create_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 parsed: dict, user):
        """Maneja creación de tarea"""
        entities = parsed['entities']
        title = entities.get('title', parsed['original_text'])
        priority = entities.get('priority', 'normal')
        task_date = entities.get('date')
        client_info = entities.get('client')
        
        # Manejar cliente si existe
        client_id = None
        client_name_raw = None
        
        if client_info:
            client_match = client_info.get('match', {})
            client_name_raw = client_info.get('raw')
            
            if client_match.get('action') == 'auto':
                # Cliente encontrado automáticamente
                client_id = client_match.get('client_id')
            elif client_match.get('action') == 'confirm':
                # Pedir confirmación con botones
                await self._ask_client_confirmation(update, context, client_match, parsed, user)
                return
            elif client_match.get('action') == 'create':
                # Ofrecer crear cliente nuevo
                await self._offer_create_client(update, context, client_name_raw, parsed, user)
                return
        
        # Crear tarea
        task_id = self.db.create_task(
            user_id=user.id,
            user_name=user.full_name or user.username,
            title=title,
            description=parsed['original_text'],
            priority=priority,
            task_date=task_date,
            client_id=client_id,
            client_name_raw=client_name_raw
        )
        
        # Responder con confirmación y botones
        await self._send_task_confirmation(update, context, task_id, user)
    
    async def _ask_client_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                      client_match: dict, parsed: dict, user):
        """Pide confirmación de cliente con botones"""
        candidates = client_match.get('candidates', [])
        
        keyboard = []
        for candidate in candidates:
            keyboard.append([InlineKeyboardButton(
                f"✅ {candidate['name']} ({candidate['confidence']:.0f}%)",
                callback_data=f"confirm_client:{candidate['id']}:{parsed['original_text']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            "➕ Crear cliente nuevo",
            callback_data=f"create_client:{client_match.get('raw', '')}:{parsed['original_text']}"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤔 ¿A qué cliente te refieres?\n\n"
            f"Cliente mencionado: {client_match.get('raw', 'N/A')}",
            reply_markup=reply_markup
        )
    
    async def _offer_create_client(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  client_name: str, parsed: dict, user):
        """Ofrece crear cliente nuevo"""
        keyboard = [[
            InlineKeyboardButton(
                "➕ Crear cliente",
                callback_data=f"create_client:{client_name}:{parsed['original_text']}"
            ),
            InlineKeyboardButton(
                "❌ Continuar sin cliente",
                callback_data=f"skip_client:{parsed['original_text']}"
            )
        ]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"❓ No encontré el cliente '{client_name}'.\n"
            f"¿Quieres crearlo?",
            reply_markup=reply_markup
        )
    
    async def _send_task_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     task_id: int, user):
        """Envía confirmación de tarea creada con botones"""
        task = self.db.get_task_by_id(task_id)
        if not task:
            await update.message.reply_text("❌ Error: Tarea no encontrada.")
            return
        
        # Formatear mensaje
        client_info = ""
        if task['client_id']:
            client = self.db.get_client_by_id(task['client_id'])
            if client:
                client_info = f"\n👤 Cliente: {client['name']}"
        elif task['client_name_raw']:
            client_info = f"\n👤 Cliente: {task['client_name_raw']} (sin asociar)"
        
        date_info = ""
        if task['task_date']:
            task_dt = datetime.fromisoformat(task['task_date'])
            date_info = f"\n📅 Fecha: {task_dt.strftime('%d/%m/%Y %H:%M')}"
        
        priority_emoji = {
            'urgent': '🔴',
            'high': '🟠',
            'normal': '🟡',
            'low': '🟢'
        }.get(task['priority'], '🟡')
        
        message = (
            f"✅ Tarea creada:\n\n"
            f"📝 {task['title']}"
            f"{client_info}"
            f"{date_info}"
            f"\n{priority_emoji} Prioridad: {task['priority']}"
        )
        
        # Botones
        keyboard = []
        
        # Botones principales
        keyboard.append([
            InlineKeyboardButton("✅ Confirmar", callback_data=f"confirm_task:{task_id}"),
            InlineKeyboardButton("✏️ Cambiar", callback_data=f"edit_task:{task_id}")
        ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Cancelar", callback_data=f"cancel_task:{task_id}")
        ])
        
        # Botón Google Calendar (solo si está configurado)
        if config.GOOGLE_CALENDAR_ENABLED:
            keyboard.append([
                InlineKeyboardButton(
                    "📅 Crear en Google Calendar",
                    callback_data=f"create_calendar:{task_id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Añadir teclado de respuesta siempre visible
        reply_keyboard = self._get_reply_keyboard()
        
        # Si es callback query, editar mensaje; si no, responder
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(message, reply_markup=reply_keyboard)
        elif context and hasattr(context, 'message'):
            await context.message.reply_text(message, reply_markup=reply_keyboard)
        else:
            # Fallback: usar el update directamente
            if hasattr(update, 'effective_message'):
                await update.effective_message.reply_text(message, reply_markup=reply_keyboard)
    
    async def _handle_list_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                parsed: dict, user):
        """Maneja listado de tareas"""
        try:
            entities = parsed['entities']
            text_lower = parsed['original_text'].lower()
            
            # Determinar filtro de fecha
            status = 'open'
            task_date_filter = None
            
            if 'hoy' in text_lower:
                task_date_filter = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            elif 'mañana' in text_lower:
                task_date_filter = (datetime.now() + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            elif 'semana' in text_lower:
                # Tareas de esta semana
                task_date_filter = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Obtener tareas
            tasks = self.db.get_tasks(user_id=user.id, status=status)
            
            # Filtrar por fecha si es necesario
            if task_date_filter:
                filtered_tasks = []
                for task in tasks:
                    if task.get('task_date'):
                        try:
                            task_dt = datetime.fromisoformat(task['task_date'])
                            if task_dt.date() == task_date_filter.date():
                                filtered_tasks.append(task)
                        except (ValueError, TypeError):
                            # Si hay error parseando fecha, incluir la tarea de todas formas
                            pass
                tasks = filtered_tasks
            
            if not tasks:
                await update.message.reply_text(
                    "📋 No hay tareas pendientes.",
                    reply_markup=self._get_reply_keyboard()
                )
                return
            
            # Formatear lista
            message_parts = ["📋 Tareas pendientes:\n"]
            for i, task in enumerate(tasks[:10], 1):  # Máximo 10
                client_info = ""
                if task.get('client_id'):
                    try:
                        client = self.db.get_client_by_id(task['client_id'])
                        if client:
                            client_info = f" 👤 {client['name']}"
                    except Exception:
                        pass
                
                date_info = ""
                if task.get('task_date'):
                    try:
                        task_dt = datetime.fromisoformat(task['task_date'])
                        date_info = f" 📅 {task_dt.strftime('%d/%m/%Y')}"
                    except (ValueError, TypeError):
                        pass
                
                message_parts.append(
                    f"{i}. {task.get('title', 'Sin título')}{client_info}{date_info}"
                )
            
            if len(tasks) > 10:
                message_parts.append(f"\n... y {len(tasks) - 10} más")
            
            await update.message.reply_text(
                '\n'.join(message_parts),
                reply_markup=self._get_reply_keyboard()
            )
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error en _handle_list_tasks: {e}")
            print(f"Traceback: {error_trace}")
            await update.message.reply_text(
                f"❌ Error al listar tareas: {str(e)}",
                reply_markup=self._get_reply_keyboard()
            )
    
    async def _handle_close_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                parsed: dict, user):
        """Maneja cierre de tarea"""
        entities = parsed['entities']
        client_info = entities.get('client')
        
        # Si no hay cliente especificado, listar todas las tareas abiertas para que elija
        if not client_info:
            tasks = self.db.get_tasks(user_id=user.id, status='open', limit=10)
            
            if not tasks:
                await update.message.reply_text(
                    "📋 No tienes tareas pendientes para cerrar.",
                    reply_markup=self._get_reply_keyboard()
                )
                return
            
            # Si hay solo una tarea, cerrarla directamente
            if len(tasks) == 1:
                task = tasks[0]
                self.db.complete_task(task['id'])
                await update.message.reply_text(
                    f"✅ Tarea cerrada:\n📝 {task['title']}",
                    reply_markup=self._get_reply_keyboard()
                )
                return
            
            # Si hay varias, mostrar opciones con botones
            keyboard = []
            for task in tasks[:5]:  # Máximo 5 opciones
                keyboard.append([InlineKeyboardButton(
                    f"📝 {task['title'][:40]}",
                    callback_data=f"close_task:{task['id']}"
                )])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # El teclado de respuesta siempre está visible, solo añadir botones inline
            await update.message.reply_text(
                f"Tienes {len(tasks)} tareas pendientes. ¿Cuál quieres cerrar?",
                reply_markup=reply_markup
            )
            return
        
        if client_info:
            # Cerrar por cliente
            client_match = client_info.get('match', {})
            if client_match.get('action') == 'auto':
                client_id = client_match.get('client_id')
                tasks = self.db.get_open_tasks_by_client(user.id, client_id, limit=5)
                
                if not tasks:
                    await update.message.reply_text(
                        f"❌ No hay tareas abiertas para el cliente {client_match.get('client_name')}.",
                        reply_markup=self._get_reply_keyboard()
                    )
                    return
                
                if len(tasks) == 1:
                    # Una sola tarea, pedir confirmación
                    task = tasks[0]
                    keyboard = [[
                        InlineKeyboardButton(
                            "✅ Sí, cerrar",
                            callback_data=f"close_task:{task['id']}"
                        ),
                        InlineKeyboardButton("❌ No", callback_data="cancel_close")
                    ]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"¿Cerrar esta tarea?\n\n📝 {task['title']}",
                        reply_markup=reply_markup
                    )
                else:
                    # Varias tareas, listar con botones
                    keyboard = []
                    for task in tasks:
                        keyboard.append([InlineKeyboardButton(
                            f"📝 {task['title'][:30]}...",
                            callback_data=f"close_task:{task['id']}"
                        )])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"Hay {len(tasks)} tareas abiertas para este cliente. ¿Cuál quieres cerrar?",
                        reply_markup=reply_markup
                    )
                return
        
        # Cerrar por título (fuzzy match)
        title = entities.get('title', parsed['original_text'])
        tasks = self.db.get_tasks(user_id=user.id, status='open')
        
        # Fuzzy match del título
        from rapidfuzz import fuzz, process
        task_titles = [(t['id'], t['title']) for t in tasks]
        matches = process.extract(
            title,
            [t[1] for t in task_titles],
            scorer=fuzz.ratio,
            limit=5
        )
        
        if not matches or matches[0][1] < 70:
            await update.message.reply_text(
                f"❌ No encontré tareas que coincidan con '{title}'.",
                reply_markup=self._get_reply_keyboard()
            )
            return
        
        # Mostrar opciones
        keyboard = []
        for match in matches[:5]:
            matched_title = match[0]
            task_id = next(t[0] for t in task_titles if t[1] == matched_title)
            keyboard.append([InlineKeyboardButton(
                f"📝 {matched_title[:40]} ({match[1]:.0f}%)",
                callback_data=f"close_task:{task_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "¿Qué tarea quieres cerrar?",
            reply_markup=reply_markup
        )
    
    async def _handle_reschedule_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     parsed: dict, user):
        """Maneja reprogramación de tarea"""
        await update.message.reply_text(
            "🔄 Funcionalidad de reprogramación en desarrollo.\n"
            "Por ahora, puedes crear una nueva tarea con la nueva fecha."
        )
    
    async def _handle_change_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     parsed: dict, user):
        """Maneja cambio de prioridad"""
        await update.message.reply_text(
            "⚡ Funcionalidad de cambio de prioridad en desarrollo.\n"
            "Por ahora, puedes crear una nueva tarea con la prioridad deseada."
        )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja callbacks de botones"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        parts = data.split(':')
        action = parts[0]
        
        if action == 'confirm_client':
            client_id = int(parts[1])
            original_text = ':'.join(parts[2:])
            await self._create_task_with_client(query, update, client_id, original_text)
        
        elif action == 'create_client':
            client_name = parts[1]
            original_text = ':'.join(parts[2:])
            await self._create_new_client_and_task(query, update, client_name, original_text)
        
        elif action == 'skip_client':
            original_text = ':'.join(parts[1:])
            await self._create_task_without_client(query, update, original_text)
        
        elif action == 'confirm_task':
            task_id = int(parts[1])
            await query.edit_message_text("✅ Tarea confirmada.")
        
        elif action == 'edit_task':
            task_id = int(parts[1])
            await query.edit_message_text(
                "✏️ Para editar, envía un nuevo mensaje de voz con los cambios."
            )
        
        elif action == 'cancel_task':
            task_id = int(parts[1])
            self.db.delete_task(task_id)
            await query.edit_message_text("❌ Tarea cancelada y eliminada.")
        
        elif action == 'create_calendar':
            task_id = int(parts[1])
            await self._create_calendar_event(query, update, task_id)
        
        elif action == 'close_task':
            task_id = int(parts[1])
            task = self.db.get_task_by_id(task_id)
            if task:
                # Mostrar confirmación
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Sí, completar", callback_data=f"confirm_close_task:{task_id}"),
                        InlineKeyboardButton("❌ No", callback_data="cancel_close")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"¿Quieres completar esta tarea?\n\n📝 {task['title']}",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text("❌ Tarea no encontrada.", reply_markup=self._get_action_buttons())
        
        elif action == 'cancel_close':
            await query.edit_message_text("❌ Operación cancelada.", reply_markup=self._get_action_buttons())
        
        elif action == 'show_pending_tasks':
            await self._show_pending_tasks(query, update)
        
        elif action == 'close_tasks_menu':
            await self._show_close_tasks_menu(query, update)
        
        elif action == 'confirm_close_task':
            task_id = int(parts[1])
            self.db.complete_task(task_id)
            task = self.db.get_task_by_id(task_id)
            task_title = task['title'] if task else "Tarea"
            await query.edit_message_text(
                f"✅ Tarea completada:\n📝 {task_title}",
                reply_markup=self._get_action_buttons()
            )
        
        elif action == 'select_task_for_ampliar':
            task_id = int(parts[1])
            task = self.db.get_task_by_id(task_id)
            if task:
                # Guardar estado del usuario
                user = update.effective_user
                self.user_states[user.id] = {
                    'action': 'ampliar_task',
                    'task_id': task_id
                }
                await query.edit_message_text(
                    f"📝 Tarea seleccionada:\n\n"
                    f"📋 {task['title']}\n\n"
                    f"🎤 Ahora envía un mensaje de voz con la ampliación para esta tarea."
                )
            else:
                await query.edit_message_text("❌ Tarea no encontrada.", reply_markup=self._get_action_buttons())
    
    async def _create_task_with_client(self, query, update, client_id: int, original_text: str):
        """Crea tarea con cliente confirmado"""
        parsed = self.parser.parse(original_text)
        entities = parsed['entities']
        
        task_id = self.db.create_task(
            user_id=update.effective_user.id,
            user_name=update.effective_user.full_name or update.effective_user.username,
            title=entities.get('title', original_text),
            description=original_text,
            priority=entities.get('priority', 'normal'),
            task_date=entities.get('date'),
            client_id=client_id,
            client_name_raw=None
        )
        
        await self._send_task_confirmation_new_message(query.message, task_id, update.effective_user)
        await query.edit_message_text("✅ Cliente confirmado. Tarea creada.")
    
    async def _create_new_client_and_task(self, query, update, client_name: str, original_text: str):
        """Crea cliente nuevo y luego la tarea"""
        try:
            client_id = self.db.create_client(client_name)
            await query.edit_message_text(f"✅ Cliente '{client_name}' creado.")
            
            # Crear tarea
            parsed = self.parser.parse(original_text)
            entities = parsed['entities']
            
            task_id = self.db.create_task(
                user_id=update.effective_user.id,
                user_name=update.effective_user.full_name or update.effective_user.username,
                title=entities.get('title', original_text),
                description=original_text,
                priority=entities.get('priority', 'normal'),
                task_date=entities.get('date'),
                client_id=client_id,
                client_name_raw=client_name
            )
            
            await self._send_task_confirmation_new_message(query.message, task_id, update.effective_user)
            
        except ValueError as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def _create_task_without_client(self, query, update, original_text: str):
        """Crea tarea sin cliente"""
        parsed = self.parser.parse(original_text)
        entities = parsed['entities']
        
        task_id = self.db.create_task(
            user_id=update.effective_user.id,
            user_name=update.effective_user.full_name or update.effective_user.username,
            title=entities.get('title', original_text),
            description=original_text,
            priority=entities.get('priority', 'normal'),
            task_date=entities.get('date'),
            client_id=None,
            client_name_raw=None
        )
        
        await self._send_task_confirmation_new_message(query.message, task_id, update.effective_user)
        await query.edit_message_text("✅ Tarea creada sin cliente.")
    
    async def _create_calendar_event(self, query, update, task_id: int):
        """Crea evento en Google Calendar"""
        if not config.GOOGLE_CALENDAR_ENABLED:
            await query.edit_message_text("❌ Google Calendar no está configurado.")
            return
        
        try:
            import calendar_sync
            result = calendar_sync.create_calendar_event(task_id)
            
            if result.get('success'):
                event_link = result.get('event_link', '')
                await query.edit_message_text(
                    f"✅ Evento creado en Google Calendar.\n\n"
                    f"🔗 {event_link}"
                )
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error', 'Error desconocido')}")
        except Exception as e:
            await query.edit_message_text(f"❌ Error al crear evento: {str(e)}")
    
    async def _show_pending_tasks(self, query, update):
        """Muestra las tareas pendientes del usuario"""
        user = update.effective_user
        tasks = self.db.get_tasks(user_id=user.id, status='open')
        
        if not tasks:
            await query.edit_message_text(
                "✅ No tienes tareas pendientes.",
                reply_markup=self._get_action_buttons()
            )
            return
        
        message = f"📋 Tienes {len(tasks)} tarea(s) pendiente(s):\n\n"
        for i, task in enumerate(tasks[:10], 1):  # Máximo 10 tareas
            priority_emoji = {
                'urgent': '🔴',
                'high': '🟠',
                'normal': '🟡',
                'low': '🟢'
            }.get(task.get('priority', 'normal'), '🟡')
            
            date_str = ""
            if task.get('task_date'):
                try:
                    from datetime import datetime
                    task_dt = datetime.fromisoformat(task['task_date'].replace('Z', '+00:00'))
                    date_str = f" - 📅 {task_dt.strftime('%d/%m/%Y')}"
                except:
                    pass
            
            client_str = ""
            if task.get('client_id'):
                client = self.db.get_client_by_id(task['client_id'])
                if client:
                    client_str = f" - 👤 {client['name']}"
            
            message += f"{i}. {priority_emoji} {task['title']}{date_str}{client_str}\n"
        
        if len(tasks) > 10:
            message += f"\n... y {len(tasks) - 10} tarea(s) más."
        
        await query.edit_message_text(message, reply_markup=self._get_action_buttons())
    
    async def _show_pending_tasks_text(self, update, user):
        """Muestra las tareas pendientes del usuario (desde teclado de respuesta)"""
        tasks = self.db.get_tasks(user_id=user.id, status='open')
        reply_markup = self._get_reply_keyboard()
        
        if not tasks:
            await update.message.reply_text(
                "✅ No tienes tareas pendientes.",
                reply_markup=reply_markup
            )
            return
        
        message = f"📋 Tienes {len(tasks)} tarea(s) pendiente(s):\n\n"
        for i, task in enumerate(tasks[:10], 1):  # Máximo 10 tareas
            priority_emoji = {
                'urgent': '🔴',
                'high': '🟠',
                'normal': '🟡',
                'low': '🟢'
            }.get(task.get('priority', 'normal'), '🟡')
            
            date_str = ""
            if task.get('task_date'):
                try:
                    from datetime import datetime
                    task_dt = datetime.fromisoformat(task['task_date'].replace('Z', '+00:00'))
                    date_str = f" - 📅 {task_dt.strftime('%d/%m/%Y')}"
                except:
                    pass
            
            client_str = ""
            if task.get('client_id'):
                client = self.db.get_client_by_id(task['client_id'])
                if client:
                    client_str = f" - 👤 {client['name']}"
            
            message += f"{i}. {priority_emoji} {task['title']}{date_str}{client_str}\n"
        
        if len(tasks) > 10:
            message += f"\n... y {len(tasks) - 10} tarea(s) más."
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def _show_close_tasks_menu(self, query, update):
        """Muestra menú para cerrar tareas"""
        user = update.effective_user
        tasks = self.db.get_tasks(user_id=user.id, status='open', limit=10)
        
        if not tasks:
            await query.edit_message_text(
                "✅ No tienes tareas pendientes para cerrar.",
                reply_markup=self._get_action_buttons()
            )
            return
        
        keyboard = []
        for task in tasks:
            priority_emoji = {
                'urgent': '🔴',
                'high': '🟠',
                'normal': '🟡',
                'low': '🟢'
            }.get(task.get('priority', 'normal'), '🟡')
            
            task_title = task['title'][:35] + "..." if len(task['title']) > 35 else task['title']
            keyboard.append([
                InlineKeyboardButton(
                    f"{priority_emoji} {task_title}",
                    callback_data=f"close_task:{task['id']}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"✅ Selecciona la tarea que quieres completar:\n\n"
            f"Tienes {len(tasks)} tarea(s) pendiente(s).",
            reply_markup=reply_markup
        )
    
    async def _show_close_tasks_menu_text(self, update, user):
        """Muestra menú para cerrar tareas (desde teclado de respuesta)"""
        tasks = self.db.get_tasks(user_id=user.id, status='open', limit=10)
        reply_markup = self._get_reply_keyboard()
        
        if not tasks:
            await update.message.reply_text(
                "✅ No tienes tareas pendientes para cerrar.",
                reply_markup=reply_markup
            )
            return
        
        keyboard = []
        for task in tasks:
            priority_emoji = {
                'urgent': '🔴',
                'high': '🟠',
                'normal': '🟡',
                'low': '🟢'
            }.get(task.get('priority', 'normal'), '🟡')
            
            task_title = task['title'][:35] + "..." if len(task['title']) > 35 else task['title']
            keyboard.append([
                InlineKeyboardButton(
                    f"{priority_emoji} {task_title}",
                    callback_data=f"close_task:{task['id']}"
                )
            ])
        
        inline_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"✅ Selecciona la tarea que quieres completar:\n\n"
            f"Tienes {len(tasks)} tarea(s) pendiente(s).",
            reply_markup=inline_markup
        )
    
    async def _show_ampliar_tasks_menu_text(self, update, user):
        """Muestra menú para ampliar tareas (desde teclado de respuesta)"""
        # Obtener todas las tareas excepto las completadas
        all_tasks = self.db.get_tasks(user_id=user.id, limit=20)
        # Filtrar tareas completadas
        tasks = [t for t in all_tasks if t.get('status') != 'completed']
        reply_markup = self._get_reply_keyboard()
        
        if not tasks:
            await update.message.reply_text(
                "✅ No tienes tareas para ampliar (las tareas completadas no se muestran).",
                reply_markup=reply_markup
            )
            return
        
        keyboard = []
        for task in tasks:
            priority_emoji = {
                'urgent': '🔴',
                'high': '🟠',
                'normal': '🟡',
                'low': '🟢'
            }.get(task.get('priority', 'normal'), '🟡')
            
            status_emoji = {
                'open': '🟦',
                'completed': '✅',
                'cancelled': '❌'
            }.get(task.get('status', 'open'), '🟦')
            
            task_title = task['title'][:30] + "..." if len(task['title']) > 30 else task['title']
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_emoji} {priority_emoji} {task_title}",
                    callback_data=f"select_task_for_ampliar:{task['id']}"
                )
            ])
        
        inline_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"📝 Selecciona la tarea que quieres ampliar:\n\n"
            f"Después de seleccionar, envía un mensaje de voz con la ampliación.\n\n"
            f"Tienes {len(tasks)} tarea(s).",
            reply_markup=inline_markup
        )
    
    async def _add_ampliacion_to_task(self, update, task_id: int, ampliacion_text: str, user):
        """Añade ampliación a una tarea"""
        reply_markup = self._get_reply_keyboard()
        
        try:
            task = self.db.get_task_by_id(task_id)
            if not task:
                await update.message.reply_text(
                    "❌ Tarea no encontrada.",
                    reply_markup=reply_markup
                )
                return
            
            # Obtener ampliación existente si hay
            ampliacion_existente = task.get('ampliacion', '') or ''
            
            # Si ya hay ampliación, añadir nueva línea y concatenar
            if ampliacion_existente:
                nueva_ampliacion = ampliacion_existente + "\n\n" + ampliacion_text
            else:
                nueva_ampliacion = ampliacion_text
            
            # Actualizar ampliación
            self.db.update_task(task_id, ampliacion=nueva_ampliacion)
            
            await update.message.reply_text(
                f"✅ Ampliación añadida a la tarea:\n\n"
                f"📝 {task['title']}\n\n"
                f"📄 Ampliación:\n{ampliacion_text}",
                reply_markup=reply_markup
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Error al añadir ampliación: {str(e)}",
                reply_markup=reply_markup
            )

