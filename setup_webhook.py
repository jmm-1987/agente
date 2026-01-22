#!/usr/bin/env python3
"""Script para configurar el webhook de Telegram en Render"""
import os
import sys
import requests

# Obtener variables de entorno
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')
TELEGRAM_WEBHOOK_SECRET = os.getenv('TELEGRAM_WEBHOOK_SECRET', '')

def check_webhook():
    """Verifica el estado actual del webhook"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN no está configurado")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            webhook_info = data.get('result', {})
            current_url = webhook_info.get('url', '')
            pending_updates = webhook_info.get('pending_update_count', 0)
            
            print(f"\n📊 Estado actual del webhook:")
            print(f"   URL: {current_url if current_url else 'No configurado'}")
            print(f"   Actualizaciones pendientes: {pending_updates}")
            
            if current_url:
                return True
            else:
                print("\n⚠️  El webhook no está configurado")
                return False
        else:
            print(f"❌ Error al obtener información del webhook: {data.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error al conectar con Telegram: {e}")
        return False

def set_webhook():
    """Configura el webhook en Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN no está configurado")
        return False
    
    if not TELEGRAM_WEBHOOK_URL:
        print("❌ ERROR: TELEGRAM_WEBHOOK_URL no está configurado")
        print("   Debe ser: https://tu-app.onrender.com/webhook")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    
    payload = {
        'url': TELEGRAM_WEBHOOK_URL
    }
    
    # Añadir secret token si está configurado
    if TELEGRAM_WEBHOOK_SECRET:
        payload['secret_token'] = TELEGRAM_WEBHOOK_SECRET
    
    try:
        print(f"\n🔧 Configurando webhook...")
        print(f"   URL: {TELEGRAM_WEBHOOK_URL}")
        if TELEGRAM_WEBHOOK_SECRET:
            print(f"   Secret Token: {'*' * len(TELEGRAM_WEBHOOK_SECRET)}")
        
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            print("✅ Webhook configurado correctamente!")
            print(f"   Descripción: {data.get('description', 'OK')}")
            return True
        else:
            print(f"❌ Error al configurar webhook: {data.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error al configurar webhook: {e}")
        return False

def delete_webhook():
    """Elimina el webhook (útil para debugging)"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN no está configurado")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
    
    try:
        print("\n🗑️  Eliminando webhook...")
        response = requests.post(url, json={'drop_pending_updates': True}, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            print("✅ Webhook eliminado correctamente")
            return True
        else:
            print(f"❌ Error al eliminar webhook: {data.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error al eliminar webhook: {e}")
        return False

def main():
    """Función principal"""
    print("=" * 60)
    print("🤖 Configurador de Webhook para Telegram Bot")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\nUso:")
        print("  python setup_webhook.py check    - Verifica el estado del webhook")
        print("  python setup_webhook.py set      - Configura el webhook")
        print("  python setup_webhook.py delete   - Elimina el webhook")
        print("\nVariables de entorno necesarias:")
        print("  - TELEGRAM_BOT_TOKEN (obligatorio)")
        print("  - TELEGRAM_WEBHOOK_URL (obligatorio para 'set')")
        print("  - TELEGRAM_WEBHOOK_SECRET (opcional pero recomendado)")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'check':
        check_webhook()
    elif command == 'set':
        if check_webhook():
            print("\n⚠️  Ya hay un webhook configurado. ¿Deseas sobrescribirlo?")
            response = input("   (s/n): ").lower()
            if response == 's':
                set_webhook()
        else:
            set_webhook()
    elif command == 'delete':
        delete_webhook()
    else:
        print(f"❌ Comando desconocido: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()









