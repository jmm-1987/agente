"""Aplicación Flask principal con webhook de Telegram y web app"""
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from functools import wraps
import logging
import json
import asyncio
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

# Inicializar bot de Telegram
bot_handler = telegram_bot.TelegramBotHandler()
telegram_app = None
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="telegram_bot")
telegram_initialized = False

if config.TELEGRAM_BOT_TOKEN:
    telegram_app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Handlers
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handler.handle_text_message))
    telegram_app.add_handler(MessageHandler(filters.VOICE, bot_handler.handle_voice_message))
    telegram_app.add_handler(CallbackQueryHandler(bot_handler.handle_callback_query))
    
    # Comando /start
    from telegram.ext import CommandHandler
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await bot_handler.handle_text_message(update, context)
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("help", start_command))
    
    # Inicializar el Application en un thread separado para modo webhook
    import threading
    def init_telegram_app():
        """Inicializa y ejecuta el Application en un event loop separado"""
        global telegram_initialized
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(telegram_app.initialize())
            loop.run_until_complete(telegram_app.start())
            telegram_initialized = True
            logger.info("Bot de Telegram inicializado y corriendo")
            # Mantener el loop corriendo
            loop.run_forever()
        except Exception as e:
            logger.error(f"Error inicializando bot: {e}", exc_info=True)
        finally:
            loop.close()
    
    bot_thread = threading.Thread(target=init_telegram_app, daemon=True)
    bot_thread.start()
    
    logger.info("Bot de Telegram configurado")
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
        return jsonify({'error': 'Bot no configurado'}), 503
    
    if not telegram_initialized:
        logger.warning("Bot aún no está inicializado, esperando...")
        return jsonify({'error': 'Bot no inicializado'}), 503
    
    # Verificar secreto si está configurado
    if config.TELEGRAM_WEBHOOK_SECRET:
        secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if secret != config.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Intento de webhook con secreto incorrecto")
            return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        update = Update.de_json(request.get_json(), telegram_app.bot)
        update_type = 'message' if update.message else 'callback_query' if update.callback_query else 'other'
        logger.info(f"Recibida actualización: {update.update_id}, tipo: {update_type}")
        
        # Usar update_queue que es thread-safe
        # El Application ya está corriendo en su propio thread con event loop
        try:
            telegram_app.update_queue.put_nowait(update)
            logger.info(f"Actualización {update.update_id} añadida a la cola correctamente")
        except Exception as queue_error:
            logger.error(f"Error añadiendo a la cola: {queue_error}")
            # Fallback: ejecutar directamente en un thread separado
            def process_update_sync():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(telegram_app.process_update(update))
                finally:
                    loop.close()
            executor.submit(process_update_sync)
            logger.info(f"Actualización {update.update_id} procesada en thread separado")
        
        return jsonify({'ok': True})
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}", exc_info=True)
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
    
    status = request.args.get('status', 'all')
    priority = request.args.get('priority', 'all')
    user_id = request.args.get('user_id', type=int)
    task_date = request.args.get('task_date', '')
    
    db = database.db
    tasks_list = db.get_tasks()
    
    # Filtrar
    if status != 'all':
        tasks_list = [t for t in tasks_list if t['status'] == status]
    if priority != 'all':
        tasks_list = [t for t in tasks_list if t['priority'] == priority]
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
    
    return render_template(
        'tasks.html',
        tasks=tasks_list,
        clients=clients,
        users=users,
        current_status=status,
        current_priority=priority,
        current_user_id=user_id,
        current_task_date=task_date
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
        'calendar_configured': config.GOOGLE_CALENDAR_ENABLED,
        'database_path': config.SQLITE_PATH
    })


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

