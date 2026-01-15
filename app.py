"""Aplicación Flask principal con webhook de Telegram y web app"""
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from functools import wraps
import logging
import json
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import config
import database
import telegram_bot

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Filtro Jinja2 para parsear JSON
@app.template_filter('fromjson')
def fromjson_filter(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return []
    return value if isinstance(value, list) else []

@app.template_filter('tojson')
def tojson_filter(value):
    """Convierte valor a JSON string seguro para JavaScript"""
    return json.dumps(value) if value is not None else 'null'

@app.template_filter('format_date')
def format_date_filter(value):
    """Formatea fecha a dd/mm/yyyy"""
    if not value:
        return ''
    try:
        from datetime import datetime
        # Intentar parsear diferentes formatos
        if isinstance(value, str):
            # Si tiene formato ISO con hora
            if 'T' in value or ' ' in value:
                try:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return dt.strftime('%d/%m/%Y')
                except:
                    try:
                        dt = datetime.strptime(value[:10], '%Y-%m-%d')
                        return dt.strftime('%d/%m/%Y')
                    except:
                        return value[:10] if len(value) >= 10 else value
            else:
                # Solo fecha
                try:
                    dt = datetime.strptime(value[:10], '%Y-%m-%d')
                    return dt.strftime('%d/%m/%Y')
                except:
                    return value
        elif isinstance(value, datetime):
            return value.strftime('%d/%m/%Y')
        return str(value)
    except Exception:
        return str(value) if value else ''

@app.template_filter('date_weekday')
def date_weekday_filter(value):
    """Obtiene el día de la semana de una fecha"""
    if not value:
        return ''
    try:
        from datetime import datetime
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.strftime('%A')
            except:
                try:
                    dt = datetime.strptime(value[:10], '%Y-%m-%d')
                    return dt.strftime('%A')
                except:
                    return ''
        elif isinstance(value, datetime):
            return value.strftime('%A')
        return ''
    except Exception:
        return ''

# Inicializar bot de Telegram
bot_handler = telegram_bot.TelegramBotHandler()
telegram_app = None
telegram_loop = None  # Event loop del Application
executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="telegram_bot")
telegram_initialized = False

if config.TELEGRAM_BOT_TOKEN:
    telegram_app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Handlers
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handler.handle_text_message))
    telegram_app.add_handler(MessageHandler(filters.VOICE, bot_handler.handle_voice_message))
    telegram_app.add_handler(MessageHandler(filters.PHOTO, bot_handler.handle_photo_message))
    telegram_app.add_handler(CallbackQueryHandler(bot_handler.handle_callback_query))
    
    # Comando /start
    from telegram.ext import CommandHandler
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await bot_handler.handle_text_message(update, context)
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("help", start_command))
    
    # Inicializar el Application de forma lazy (cuando llegue el primer webhook)
    # Esto evita problemas con threads en gunicorn
    logger.info("Bot de Telegram configurado (modo webhook - inicialización lazy)")
else:
    logger.warning("TELEGRAM_BOT_TOKEN no configurado. Bot deshabilitado.")


# ========== AUTHENTICATION ==========

def login_required(f):
    """Decorador para requerir login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    """Login de administrador"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == config.ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('tasks'))
        return render_template('login.html', error='Contraseña incorrecta')
    return render_template('login.html')


@app.route('/admin/logout')
def logout():
    """Logout"""
    session.pop('logged_in', None)
    return redirect(url_for('login'))


# ========== WEBHOOK TELEGRAM ==========

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook para recibir actualizaciones de Telegram"""
    if not telegram_app:
        logger.error("Webhook recibido pero bot no configurado")
        return jsonify({'error': 'Bot no configurado'}), 503
    
    # Inicializar Application de forma lazy si no está inicializado
    if not telegram_initialized:
        logger.info("[WEBHOOK] Application no inicializado, inicializando ahora...")
        try:
            # Inicializar en un thread separado
            def init_app():
                global telegram_initialized, telegram_loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                telegram_loop = loop  # Guardar referencia al loop
                try:
                    logger.info("[INIT] Inicializando Application...")
                    loop.run_until_complete(telegram_app.initialize())
                    logger.info("[INIT] Application.initialize() completado")
                    # Para webhooks, NO llamamos a start() - solo initialize()
                    # start() es solo para polling y causa errores con webhooks
                    telegram_initialized = True
                    logger.info("[INIT] ✅ Application inicializado correctamente (modo webhook)")
                    # Mantener loop corriendo para procesar actualizaciones
                    loop.run_forever()
                except Exception as e:
                    logger.error(f"[INIT] Error: {e}", exc_info=True)
                    telegram_initialized = False
                    telegram_loop = None
                finally:
                    try:
                        loop.close()
                    except:
                        pass
            
            init_thread = threading.Thread(target=init_app, daemon=True, name="TelegramInit")
            init_thread.start()
            
            # Esperar un poco a que se inicialice
            import time
            for i in range(10):  # Esperar hasta 2 segundos
                time.sleep(0.2)
                if telegram_initialized:
                    break
            
            if not telegram_initialized:
                logger.warning("[WEBHOOK] Application aún no inicializado después de esperar")
                return jsonify({'error': 'Application no inicializado'}), 503
        except Exception as e:
            logger.error(f"[WEBHOOK] Error en inicialización lazy: {e}", exc_info=True)
            return jsonify({'error': 'Error inicializando'}), 500
    
    # Verificar secreto si está configurado
    if config.TELEGRAM_WEBHOOK_SECRET:
        secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if secret != config.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Intento de webhook con secreto incorrecto")
            return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        update_data = request.get_json()
        if not update_data:
            logger.warning("Webhook recibido sin datos")
            return jsonify({'error': 'No data'}), 400
        
        update = Update.de_json(update_data, telegram_app.bot)
        update_type = 'message' if update.message else 'callback_query' if update.callback_query else 'other'
        logger.info(f"[WEBHOOK] Recibida actualización {update.update_id}, tipo: {update_type}")
        
        # Procesar actualización directamente usando process_update en el event loop del Application
        def process_update_async():
            """Ejecuta process_update usando el event loop del Application"""
            try:
                if telegram_loop and telegram_loop.is_running():
                    # Si el loop está corriendo, usar call_soon_threadsafe para añadir la tarea
                    future = asyncio.run_coroutine_threadsafe(
                        telegram_app.process_update(update),
                        telegram_loop
                    )
                    logger.info(f"[WEBHOOK] Actualización {update.update_id} enviada para procesamiento")
                    # No esperamos el resultado para no bloquear
                else:
                    # Si el loop no está corriendo, crear uno nuevo
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Asegurarse de que el Application esté inicializado
                        if not telegram_app._initialized:
                            loop.run_until_complete(telegram_app.initialize())
                        loop.run_until_complete(telegram_app.process_update(update))
                        logger.info(f"[WEBHOOK] Actualización {update.update_id} procesada")
                    finally:
                        # No cerrar el loop si es el loop principal
                        if loop != telegram_loop:
                            loop.close()
            except Exception as e:
                logger.error(f"[WEBHOOK] Error procesando actualización {update.update_id}: {e}", exc_info=True)
        
        executor.submit(process_update_async)
        
        return jsonify({'ok': True})
    except Exception as e:
        logger.error(f"[WEBHOOK] Error procesando webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/webhook/set', methods=['POST'])
def set_webhook():
    """Configura webhook de Telegram (requiere autenticación)"""
    if not config.TELEGRAM_BOT_TOKEN:
        return jsonify({'error': 'Bot no configurado'}), 503
    
    webhook_url = config.TELEGRAM_WEBHOOK_URL or request.json.get('url')
    if not webhook_url:
        return jsonify({'error': 'URL de webhook requerida'}), 400
    
    secret_token = config.TELEGRAM_WEBHOOK_SECRET
    
    try:
        bot = telegram_app.bot if telegram_app else None
        if not bot:
            return jsonify({'error': 'Bot no inicializado'}), 503
        
        result = bot.set_webhook(
            url=webhook_url,
            secret_token=secret_token
        )
        
        return jsonify({
            'success': result,
            'webhook_url': webhook_url
        })
    except Exception as e:
        logger.error(f"Error configurando webhook: {e}")
        return jsonify({'error': str(e)}), 500


# ========== WEB APP ==========

@app.route('/')
@login_required
def index():
    """Redirigir a tareas"""
    return redirect(url_for('tasks'))


@app.route('/admin/tasks')
@login_required
def tasks():
    """Vista de tareas"""
    from datetime import datetime
    
    status = request.args.get('status', 'open')  # Por defecto mostrar tareas abiertas
    priority = request.args.get('priority', 'all')
    category = request.args.get('category', 'all')
    user_id = request.args.get('user_id', type=int)
    task_date = request.args.get('task_date', '')
    view_mode = request.args.get('view_mode', 'list')
    
    db = database.db
    tasks_list = db.get_tasks()
    
    # Filtrar
    if status != 'all':
        tasks_list = [t for t in tasks_list if t['status'] == status]
    if priority != 'all':
        tasks_list = [t for t in tasks_list if t['priority'] == priority]
    if category != 'all':
        tasks_list = [t for t in tasks_list if t.get('category') == category]
    if user_id:
        tasks_list = [t for t in tasks_list if t['user_id'] == user_id]
    if task_date:
        # Filtrar por fecha de tarea (comparar solo la fecha, sin hora)
        try:
            filter_date = datetime.strptime(task_date, '%Y-%m-%d').date()
            filtered_tasks = []
            for t in tasks_list:
                if t.get('task_date'):
                    try:
                        task_dt = datetime.fromisoformat(t['task_date'].replace('Z', '+00:00'))
                        if task_dt.date() == filter_date:
                            filtered_tasks.append(t)
                    except (ValueError, AttributeError):
                        # Si hay error al parsear la fecha, intentar formato alternativo
                        try:
                            task_dt = datetime.strptime(t['task_date'][:10], '%Y-%m-%d')
                            if task_dt.date() == filter_date:
                                filtered_tasks.append(t)
                        except (ValueError, AttributeError):
                            continue
            tasks_list = filtered_tasks
        except ValueError:
            # Si la fecha no es válida, ignorar el filtro
            pass
    
    # Obtener clientes para filtro
    clients = db.get_all_clients()
    
    # Obtener usuarios únicos
    users = {}
    for task in tasks_list:
        user_id = task['user_id']
        if user_id not in users:
            users[user_id] = task.get('user_name', f'Usuario {user_id}')
    
    # Asegurar que current_status tenga un valor válido
    if not status or status == '':
        status = 'open'
    
    # Separar tareas con fecha y sin fecha
    tasks_with_date = []
    tasks_without_date = []
    
    for task in tasks_list:
        if task.get('task_date'):
            tasks_with_date.append(task)
        else:
            tasks_without_date.append(task)
    
    # Ordenar tareas con fecha por fecha más reciente primero (descendente)
    tasks_with_date.sort(key=lambda x: x.get('task_date', '') or '', reverse=True)
    
    # Obtener imágenes para cada tarea
    for task in tasks_with_date:
        task['images'] = db.get_task_images(task['id'])
    for task in tasks_without_date:
        task['images'] = db.get_task_images(task['id'])
    
    # Para vista de calendario, organizar tareas por día de la semana
    tasks_by_weekday = {}
    if view_mode == 'calendar':
        for task in tasks_with_date:
            try:
                task_dt = datetime.fromisoformat(task['task_date'].replace('Z', '+00:00'))
                weekday = task_dt.strftime('%A')  # Monday, Tuesday, etc.
                if weekday not in tasks_by_weekday:
                    tasks_by_weekday[weekday] = []
                tasks_by_weekday[weekday].append(task)
            except (ValueError, AttributeError):
                try:
                    task_dt = datetime.strptime(task['task_date'][:10], '%Y-%m-%d')
                    weekday = task_dt.strftime('%A')
                    if weekday not in tasks_by_weekday:
                        tasks_by_weekday[weekday] = []
                    tasks_by_weekday[weekday].append(task)
                except (ValueError, AttributeError):
                    pass
    
    return render_template(
        'tasks.html',
        tasks_with_date=tasks_with_date,
        tasks_without_date=tasks_without_date,
        tasks_by_weekday=tasks_by_weekday,
        clients=clients,
        users=users,
        current_status=status,
        current_priority=priority,
        current_category=category,
        current_user_id=user_id,
        current_task_date=task_date,
        view_mode=view_mode
    )


@app.route('/admin/clients')
@login_required
def clients():
    """Vista de clientes"""
    db = database.db
    clients_list = db.get_all_clients()
    return render_template('clients.html', clients=clients_list)


@app.route('/admin/clients/create', methods=['POST'])
@login_required
def create_client():
    """Crear cliente"""
    name = request.form.get('name', '').strip()
    aliases_str = request.form.get('aliases', '').strip()
    
    if not name:
        return redirect(url_for('clients'))
    
    aliases = [a.strip() for a in aliases_str.split(',') if a.strip()]
    
    db = database.db
    try:
        db.create_client(name, aliases)
        return redirect(url_for('clients'))
    except ValueError as e:
        return render_template('clients.html', error=str(e), clients=db.get_all_clients())


@app.route('/admin/clients/<int:client_id>/edit', methods=['POST'])
@login_required
def edit_client(client_id):
    """Editar cliente"""
    name = request.form.get('name', '').strip()
    aliases_str = request.form.get('aliases', '').strip()
    
    aliases = [a.strip() for a in aliases_str.split(',') if a.strip()] if aliases_str else []
    
    db = database.db
    db.update_client(client_id, name=name if name else None, aliases=aliases if aliases else None)
    return redirect(url_for('clients'))


@app.route('/admin/clients/<int:client_id>/delete', methods=['POST'])
@login_required
def delete_client(client_id):
    """Eliminar cliente"""
    db = database.db
    db.delete_client(client_id)
    return redirect(url_for('clients'))


@app.route('/admin/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """Completar tarea"""
    db = database.db
    db.complete_task(task_id)
    return redirect(url_for('tasks'))


@app.route('/admin/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    """Eliminar tarea"""
    db = database.db
    db.delete_task(task_id)
    return redirect(url_for('tasks'))


@app.route('/admin/tasks/<int:task_id>/solution', methods=['POST'])
@login_required
def update_task_solution(task_id):
    """Actualizar solución/resolución de tarea"""
    solution = request.form.get('solution', '').strip()
    db = database.db
    db.update_task(task_id, solution=solution if solution else None)
    return redirect(url_for('tasks'))


@app.route('/admin/tasks/<int:task_id>/images/<int:image_id>')
@login_required
def get_task_image(task_id, image_id):
    """Sirve una imagen de una tarea"""
    from flask import send_file
    import os
    
    db = database.db
    images = db.get_task_images(task_id)
    
    # Buscar la imagen específica
    image = next((img for img in images if img['id'] == image_id), None)
    
    if not image or not image.get('file_path'):
        return jsonify({'error': 'Imagen no encontrada'}), 404
    
    file_path = image['file_path']
    
    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        return jsonify({'error': 'Archivo no encontrado'}), 404
    
    return send_file(file_path, mimetype='image/jpeg')


# ========== API JSON ==========

@app.route('/api/tasks', methods=['GET'])
def api_tasks():
    """API JSON para obtener tareas"""
    status = request.args.get('status')
    client_id = request.args.get('client_id', type=int)
    user_id = request.args.get('user_id', type=int)
    
    db = database.db
    tasks_list = db.get_tasks(status=status, client_id=client_id)
    
    if user_id:
        tasks_list = [t for t in tasks_list if t['user_id'] == user_id]
    
    return jsonify({'tasks': tasks_list})


@app.route('/api/clients', methods=['GET'])
def api_clients():
    """API JSON para obtener clientes"""
    db = database.db
    clients_list = db.get_all_clients()
    return jsonify({'clients': clients_list})


# ========== HEALTH CHECK ==========

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'telegram_configured': bool(config.TELEGRAM_BOT_TOKEN),
        'telegram_initialized': telegram_initialized,
        'calendar_configured': config.GOOGLE_CALENDAR_ENABLED,
        'database_path': config.SQLITE_PATH
    })

@app.route('/webhook/status')
def webhook_status():
    """Endpoint para verificar el estado del webhook y del bot"""
    if not telegram_app:
        return jsonify({
            'bot_configured': False,
            'error': 'Bot no configurado'
        }), 503
    
    try:
        # Obtener información del webhook desde Telegram
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            webhook_info = loop.run_until_complete(telegram_app.bot.get_webhook_info())
            return jsonify({
                'bot_configured': True,
                'bot_initialized': telegram_initialized,
                'webhook_info': {
                    'url': webhook_info.url or 'No configurado',
                    'has_custom_certificate': webhook_info.has_custom_certificate,
                    'pending_update_count': webhook_info.pending_update_count,
                    'last_error_date': str(webhook_info.last_error_date) if webhook_info.last_error_date else None,
                    'last_error_message': webhook_info.last_error_message,
                    'max_connections': webhook_info.max_connections
                },
                'expected_webhook_url': config.TELEGRAM_WEBHOOK_URL,
                'webhook_secret_configured': bool(config.TELEGRAM_WEBHOOK_SECRET)
            })
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error obteniendo estado del webhook: {e}", exc_info=True)
        return jsonify({
            'bot_configured': True,
            'bot_initialized': telegram_initialized,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    import asyncio
    import threading
    
    # Inicializar base de datos
    database.db.init_db()
    
    # Iniciar bot con polling en local (solo si hay token)
    def run_bot():
        if telegram_app:
            logger.info("Iniciando bot de Telegram con polling...")
            telegram_app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    
    # Iniciar bot en thread separado
    if telegram_app:
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        logger.info("Bot de Telegram iniciado en modo polling")
    
    # Iniciar aplicación Flask
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG
    )

