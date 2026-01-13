"""Utilidades varias"""
import re
import unicodedata
from typing import Optional


def normalize_text(text: str) -> str:
    """Normaliza texto: lowercase, sin acentos, sin espacios extra"""
    if not text:
        return ""
    # Convertir a lowercase
    text = text.lower().strip()
    # Remover acentos
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Remover espacios extra
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_client_mentions(text: str) -> list[str]:
    """Extrae menciones de clientes del texto usando patrones comunes"""
    patterns = [
        r'cliente\s+(\w+(?:\s+\w+)*)',
        r'del\s+cliente\s+(\w+(?:\s+\w+)*)',
        r'para\s+el\s+cliente\s+(\w+(?:\s+\w+)*)',
        r'cliente\s+(\w+(?:\s+\w+)*)',
    ]
    
    mentions = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        mentions.extend(matches)
    
    # También buscar al inicio si dice "cliente X" o "del cliente X"
    text_lower = text.lower()
    if text_lower.startswith('cliente '):
        parts = text.split(' ', 1)
        if len(parts) > 1:
            client_part = parts[1].split()[0]  # Primera palabra después de "cliente"
            mentions.append(client_part)
    
    return list(set(mentions))  # Eliminar duplicados


def clean_temp_files(filepath: str) -> None:
    """Elimina archivo temporal si existe"""
    import os
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Warning: No se pudo eliminar archivo temporal {filepath}: {e}")
