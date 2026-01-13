"""Integración con Google Calendar"""
from datetime import datetime, timedelta
from typing import Dict, Optional
import config
import database


def create_calendar_event(task_id: int) -> Dict:
    """Crea evento en Google Calendar para una tarea"""
    if not config.GOOGLE_CALENDAR_ENABLED:
        return {
            'success': False,
            'error': 'Google Calendar no está configurado'
        }
    
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        import json
        
        # Obtener tarea
        db = database.db
        task = db.get_task_by_id(task_id)
        if not task:
            return {'success': False, 'error': 'Tarea no encontrada'}
        
        # Si ya tiene evento, no crear otro
        if task.get('google_event_id'):
            return {
                'success': False,
                'error': 'La tarea ya tiene un evento en Google Calendar'
            }
        
        # Configurar credenciales
        creds = Credentials(
            token=None,
            refresh_token=config.GOOGLE_REFRESH_TOKEN,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=config.GOOGLE_CLIENT_ID,
            client_secret=config.GOOGLE_CLIENT_SECRET
        )
        
        # Refrescar token si es necesario
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
        
        # Construir servicio
        service = build('calendar', 'v3', credentials=creds)
        
        # Preparar fecha/hora del evento
        if task.get('task_date'):
            start_dt = datetime.fromisoformat(task['task_date'])
        else:
            # Si no hay fecha, usar fecha de creación + 1 día a las 9:00 AM
            start_dt = datetime.now() + timedelta(days=1)
            start_dt = start_dt.replace(hour=9, minute=0, second=0, microsecond=0)
        
        end_dt = start_dt + timedelta(hours=1)  # Duración 1 hora por defecto
        
        # Preparar descripción
        description_parts = [task.get('description', task['title'])]
        
        if task.get('client_id'):
            client = db.get_client_by_id(task['client_id'])
            if client:
                description_parts.append(f"\nCliente: {client['name']}")
        
        description = '\n'.join(description_parts)
        
        # Crear evento
        event = {
            'summary': task['title'],
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Europe/Madrid',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'Europe/Madrid',
            },
        }
        
        # Insertar evento
        created_event = service.events().insert(
            calendarId=config.GOOGLE_CALENDAR_ID,
            body=event
        ).execute()
        
        # Actualizar tarea con información del evento
        db.update_task(
            task_id,
            google_event_id=created_event.get('id'),
            google_event_link=created_event.get('htmlLink')
        )
        
        return {
            'success': True,
            'event_id': created_event.get('id'),
            'event_link': created_event.get('htmlLink')
        }
        
    except ImportError:
        return {
            'success': False,
            'error': 'Bibliotecas de Google Calendar no instaladas. Instala con: pip install google-auth google-auth-oauthlib google-api-python-client'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
