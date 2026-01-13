"""Parser de intenciones y entidades usando reglas + regex + rapidfuzz"""
import re
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import dateparser
from rapidfuzz import fuzz, process
import database
import config
from utils import normalize_text, extract_client_mentions


class IntentParser:
    """Parser de intenciones y extracción de entidades"""
    
    # Patrones para intenciones
    INTENT_PATTERNS = {
        'CREAR': [
            r'(?:crear|nueva|añadir|agregar|poner|hacer|tengo que|necesito)',
            r'(?:tarea|recordatorio|nota|evento|cosa)',
        ],
        'LISTAR': [
            r'(?:listar|mostrar|ver|dame|muéstrame|qué|cuáles)',
            r'(?:tareas|pendientes|cosas|recordatorios)',
        ],
        'CERRAR': [
            r'(?:cerrar|completar|terminar|hecho|realizado|finalizar|marcar como hecha|da por hecha)',
            r'(?:tarea|tareas|cosa|cosas)',
        ],
        'REPROGRAMAR': [
            r'(?:reprogramar|cambiar fecha|mover|posponer|aplazar|cambiar a)',
        ],
        'CAMBIAR_PRIORIDAD': [
            r'(?:cambiar prioridad|prioridad|urgente|importante|normal|baja)',
        ],
    }
    
    # Patrones para fechas relativas
    DATE_PATTERNS = {
        'hoy': lambda: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        'mañana': lambda: (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
        'pasado mañana': lambda: (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0),
        'esta semana': lambda: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        'próxima semana': lambda: (datetime.now() + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0),
        'el lunes': lambda: _next_weekday(0),
        'el martes': lambda: _next_weekday(1),
        'el miércoles': lambda: _next_weekday(2),
        'el jueves': lambda: _next_weekday(3),
        'el viernes': lambda: _next_weekday(4),
        'el sábado': lambda: _next_weekday(5),
        'el domingo': lambda: _next_weekday(6),
    }
    
    # Mapeo de prioridades
    PRIORITY_MAP = {
        'urgente': 'urgent',
        'urgent': 'urgent',
        'alta': 'high',
        'high': 'high',
        'importante': 'high',
        'normal': 'normal',
        'media': 'normal',
        'baja': 'low',
        'low': 'low',
        'sin prisa': 'low',
        'sin prisa': 'low',
    }
    
    def __init__(self):
        self.db = database.db
    
    def parse(self, text: str) -> Dict:
        """Parsea texto y extrae intención y entidades"""
        text_normalized = normalize_text(text)
        
        # Detectar intención
        intent = self._detect_intent(text_normalized)
        
        # Extraer entidades
        entities = {
            'client': self._extract_client(text),
            'date': self._extract_date(text),
            'priority': self._extract_priority(text_normalized),
            'title': self._extract_title(text, intent),
        }
        
        return {
            'intent': intent,
            'entities': entities,
            'original_text': text,
        }
    
    def _detect_intent(self, text: str) -> str:
        """Detecta intención principal"""
        text_lower = text.lower()
        
        # Verificar cada intención
        for intent, patterns in self.INTENT_PATTERNS.items():
            # Todos los patrones deben coincidir (AND)
            matches = [bool(re.search(pattern, text_lower, re.IGNORECASE)) for pattern in patterns]
            if all(matches):
                return intent
        
        # Si no coincide ninguna, asumir CREAR por defecto
        return 'CREAR'
    
    def _extract_client(self, text: str) -> Optional[Dict]:
        """Extrae cliente del texto usando fuzzy matching"""
        mentions = extract_client_mentions(text)
        
        if not mentions:
            return None
        
        # Usar la primera mención encontrada
        client_name_raw = mentions[0]
        
        # Buscar en base de datos
        match_result = self._fuzzy_match_client(client_name_raw)
        
        return {
            'raw': client_name_raw,
            'match': match_result,
        }
    
    def _fuzzy_match_client(self, name: str) -> Dict:
        """Busca cliente usando fuzzy matching"""
        # Obtener todos los clientes
        clients = self.db.get_all_clients()
        
        if not clients:
            return {
                'found': False,
                'confidence': 0,
                'action': 'create',
            }
        
        # Preparar lista de nombres y aliases para matching
        candidates = []
        for client in clients:
            candidates.append({
                'id': client['id'],
                'name': client['name'],
                'normalized': client['normalized_name'],
                'aliases': json.loads(client['aliases'] or '[]'),
            })
        
        # Buscar match exacto normalizado primero
        normalized_input = normalize_text(name)
        for candidate in candidates:
            if candidate['normalized'] == normalized_input:
                return {
                    'found': True,
                    'client_id': candidate['id'],
                    'client_name': candidate['name'],
                    'confidence': 100,
                    'action': 'auto',
                }
        
        # Fuzzy matching contra nombres y aliases
        all_names = []
        for candidate in candidates:
            all_names.append((candidate['id'], candidate['name'], candidate['normalized']))
            for alias in candidate['aliases']:
                all_names.append((candidate['id'], alias, normalize_text(alias)))
        
        # Usar rapidfuzz para encontrar mejores matches
        matches = process.extract(
            normalized_input,
            [name_tuple[2] for name_tuple in all_names],
            scorer=fuzz.ratio,
            limit=config.CLIENT_MATCH_MAX_CANDIDATES
        )
        
        if not matches or matches[0][1] < config.CLIENT_MATCH_THRESHOLD_CONFIRM:
            return {
                'found': False,
                'confidence': matches[0][1] if matches else 0,
                'action': 'create',
            }
        
        best_match = matches[0]
        confidence = best_match[1]
        
        # Encontrar el cliente correspondiente
        matched_name = best_match[0]
        client_id = None
        client_name = None
        
        for name_tuple in all_names:
            if name_tuple[2] == matched_name:
                client_id = name_tuple[0]
                # Obtener nombre original (no normalizado)
                for candidate in candidates:
                    if candidate['id'] == client_id:
                        client_name = candidate['name']
                        break
                break
        
        if confidence >= config.CLIENT_MATCH_THRESHOLD_AUTO:
            action = 'auto'
        else:
            action = 'confirm'
            # Preparar candidatos para confirmación
            candidates_list = []
            for match in matches[:config.CLIENT_MATCH_MAX_CANDIDATES]:
                matched_norm = match[0]
                for name_tuple in all_names:
                    if name_tuple[2] == matched_norm:
                        for candidate in candidates:
                            if candidate['id'] == name_tuple[0]:
                                candidates_list.append({
                                    'id': candidate['id'],
                                    'name': candidate['name'],
                                    'confidence': match[1],
                                })
                                break
                        break
        
        result = {
            'found': True,
            'client_id': client_id,
            'client_name': client_name,
            'confidence': confidence,
            'action': action,
        }
        
        if action == 'confirm':
            result['candidates'] = candidates_list
        
        return result
    
    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extrae fecha del texto usando dateparser"""
        # Primero verificar patrones relativos comunes
        text_lower = text.lower()
        for pattern, date_func in self.DATE_PATTERNS.items():
            if pattern in text_lower:
                return date_func()
        
        # Usar dateparser para fechas más complejas
        # Preferir fechas futuras
        settings = {
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.now(),
        }
        
        # languages es un parámetro directo, no va en settings
        parsed_date = dateparser.parse(text, languages=['es'], settings=settings)
        
        if parsed_date:
            # Si no tiene hora, poner a las 9:00 AM por defecto
            if parsed_date.hour == 0 and parsed_date.minute == 0:
                parsed_date = parsed_date.replace(hour=9, minute=0)
            return parsed_date
        
        return None
    
    def _extract_priority(self, text: str) -> str:
        """Extrae prioridad del texto"""
        text_lower = text.lower()
        
        for keyword, priority in self.PRIORITY_MAP.items():
            if keyword in text_lower:
                return priority
        
        return 'normal'
    
    def _extract_title(self, text: str, intent: str) -> str:
        """Extrae título de la tarea"""
        # Remover palabras de intención y entidades conocidas
        text_clean = text
        
        # Remover palabras de intención
        for intent_name, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                text_clean = re.sub(pattern, '', text_clean, flags=re.IGNORECASE)
        
        # Remover menciones de cliente
        mentions = extract_client_mentions(text_clean)
        for mention in mentions:
            text_clean = re.sub(
                rf'\b(?:cliente|del cliente|para el cliente)\s+{re.escape(mention)}\b',
                '',
                text_clean,
                flags=re.IGNORECASE
            )
        
        # Remover palabras de prioridad
        for keyword in self.PRIORITY_MAP.keys():
            text_clean = re.sub(rf'\b{re.escape(keyword)}\b', '', text_clean, flags=re.IGNORECASE)
        
        # Limpiar espacios extra
        text_clean = re.sub(r'\s+', ' ', text_clean).strip()
        
        # Si queda muy corto, usar el texto original
        if len(text_clean) < 5:
            text_clean = text
        
        return text_clean[:200]  # Limitar longitud


def _next_weekday(weekday: int) -> datetime:
    """Obtiene el próximo día de la semana (0=lunes, 6=domingo)"""
    today = datetime.now()
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)

