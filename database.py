"""Modelos de base de datos SQLite"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
import json
import config


class Database:
    """Gestor de base de datos SQLite"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.SQLITE_PATH
        self.init_db()
    
    def get_connection(self):
        """Obtiene conexión a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Inicializa las tablas de la base de datos"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabla de clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                normalized_name TEXT NOT NULL,
                aliases TEXT,  -- JSON array de aliases
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de tareas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'open' CHECK(status IN ('open', 'completed', 'cancelled')),
                priority TEXT DEFAULT 'normal' CHECK(priority IN ('low', 'normal', 'high', 'urgent')),
                task_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                client_id INTEGER,
                client_name_raw TEXT,
                google_event_id TEXT,
                google_event_link TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
            )
        ''')
        
        # Añadir columna 'solution' si no existe (migración)
        try:
            cursor.execute('ALTER TABLE tasks ADD COLUMN solution TEXT')
        except sqlite3.OperationalError:
            # La columna ya existe, ignorar
            pass
        
        # Añadir columna 'ampliacion' si no existe (migración)
        try:
            cursor.execute('ALTER TABLE tasks ADD COLUMN ampliacion TEXT')
        except sqlite3.OperationalError:
            # La columna ya existe, ignorar
            pass
        
        # Añadir columna 'category' si no existe (migración)
        try:
            cursor.execute('ALTER TABLE tasks ADD COLUMN category TEXT CHECK(category IN ("administracion", "averias", "clientes", "servicios"))')
        except sqlite3.OperationalError:
            # La columna ya existe, ignorar
            pass
        
        # Tabla de categorías
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                icon TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#3498db',
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insertar categorías por defecto si no existen
        default_categories = [
            ('administracion', '📋', '#3498db', 'Administración'),
            ('averias', '🔧', '#e74c3c', 'Averías'),
            ('clientes', '👤', '#2ecc71', 'Clientes'),
            ('servicios', '⚙️', '#f39c12', 'Servicios')
        ]
        for cat_name, icon, color, display_name in default_categories:
            cursor.execute('''
                INSERT OR IGNORE INTO categories (name, icon, color, display_name)
                VALUES (?, ?, ?, ?)
            ''', (cat_name, icon, color, display_name))
        
        # Tabla de imágenes adjuntas a tareas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')
        
        # Índices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_client_id ON tasks(client_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_normalized_name ON clients(normalized_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_images_task_id ON task_images(task_id)')
        
        conn.commit()
        conn.close()
    
    # ========== CLIENTES ==========
    
    def create_client(self, name: str, aliases: List[str] = None) -> int:
        """Crea un nuevo cliente"""
        from utils import normalize_text
        normalized = normalize_text(name)
        aliases_json = json.dumps(aliases or [])
        
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO clients (name, normalized_name, aliases)
                VALUES (?, ?, ?)
            ''', (name, normalized, aliases_json))
            client_id = cursor.lastrowid
            conn.commit()
            return client_id
        except sqlite3.IntegrityError:
            raise ValueError(f"Cliente '{name}' ya existe")
        finally:
            conn.close()
    
    def get_client_by_id(self, client_id: int) -> Optional[Dict]:
        """Obtiene cliente por ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_client_by_name(self, name: str) -> Optional[Dict]:
        """Obtiene cliente por nombre exacto (normalizado)"""
        from utils import normalize_text
        normalized = normalize_text(name)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE normalized_name = ?', (normalized,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_clients(self) -> List[Dict]:
        """Obtiene todos los clientes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients ORDER BY name')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def update_client(self, client_id: int, name: str = None, aliases: List[str] = None):
        """Actualiza cliente"""
        from utils import normalize_text
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if name:
            normalized = normalize_text(name)
            updates.append('name = ?')
            updates.append('normalized_name = ?')
            params.extend([name, normalized])
        
        if aliases is not None:
            aliases_json = json.dumps(aliases)
            updates.append('aliases = ?')
            params.append(aliases_json)
        
        if updates:
            params.append(client_id)
            cursor.execute(f'''
                UPDATE clients SET {', '.join(updates)}
                WHERE id = ?
            ''', params)
            conn.commit()
        
        conn.close()
    
    def delete_client(self, client_id: int):
        """Elimina cliente (las tareas mantienen client_name_raw)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
        conn.commit()
        conn.close()
    
    # ========== TAREAS ==========
    
    def create_task(self, user_id: int, user_name: str, title: str,
                    description: str = None, priority: str = 'normal',
                    task_date: datetime = None, client_id: int = None,
                    client_name_raw: str = None, category: str = None) -> int:
        """Crea una nueva tarea"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        task_date_str = task_date.isoformat() if task_date else None
        
        cursor.execute('''
            INSERT INTO tasks (
                user_id, user_name, title, description, priority,
                task_date, client_id, client_name_raw, category
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, title, description, priority,
              task_date_str, client_id, client_name_raw, category))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id
    
    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """Obtiene tarea por ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_tasks(self, user_id: int = None, status: str = None,
                  client_id: int = None, limit: int = None) -> List[Dict]:
        """Obtiene tareas con filtros"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM tasks WHERE 1=1'
        params = []
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        if client_id:
            query += ' AND client_id = ?'
            params.append(client_id)
        
        query += ' ORDER BY created_at DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        """Actualiza tarea"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        allowed_fields = ['title', 'description', 'status', 'priority',
                         'task_date', 'client_id', 'client_name_raw',
                         'google_event_id', 'google_event_link', 'solution', 'ampliacion', 'category']
        
        updates = []
        params = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                if isinstance(value, datetime):
                    value = value.isoformat()
                updates.append(f'{key} = ?')
                params.append(value)
        
        if updates:
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(task_id)
            cursor.execute(f'''
                UPDATE tasks SET {', '.join(updates)}
                WHERE id = ?
            ''', params)
            conn.commit()
            success = cursor.rowcount > 0
        else:
            success = False
        
        conn.close()
        return success
    
    def delete_task(self, task_id: int) -> bool:
        """Elimina tarea"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def complete_task(self, task_id: int) -> bool:
        """Marca tarea como completada"""
        return self.update_task(task_id, status='completed')
    
    def get_open_tasks_by_client(self, user_id: int, client_id: int,
                                 limit: int = 5) -> List[Dict]:
        """Obtiene tareas abiertas de un cliente"""
        return self.get_tasks(
            user_id=user_id,
            status='open',
            client_id=client_id,
            limit=limit
        )
    
    # ========== CATEGORÍAS ==========
    
    def get_all_categories(self) -> List[Dict]:
        """Obtiene todas las categorías"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, icon, color, display_name, created_at, updated_at
            FROM categories
            ORDER BY name
        ''')
        
        categories = []
        for row in cursor.fetchall():
            categories.append({
                'id': row['id'],
                'name': row['name'],
                'icon': row['icon'],
                'color': row['color'],
                'display_name': row['display_name'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        conn.close()
        return categories
    
    def get_category(self, category_id: int) -> Optional[Dict]:
        """Obtiene una categoría por ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, icon, color, display_name, created_at, updated_at
            FROM categories
            WHERE id = ?
        ''', (category_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'icon': row['icon'],
                'color': row['color'],
                'display_name': row['display_name'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
        return None
    
    def update_category(self, category_id: int, icon: str = None, color: str = None, display_name: str = None) -> bool:
        """Actualiza una categoría"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if icon is not None:
            updates.append('icon = ?')
            params.append(icon)
        if color is not None:
            updates.append('color = ?')
            params.append(color)
        if display_name is not None:
            updates.append('display_name = ?')
            params.append(display_name)
        
        if not updates:
            conn.close()
            return False
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(category_id)
        
        cursor.execute(f'''
            UPDATE categories
            SET {', '.join(updates)}
            WHERE id = ?
        ''', params)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def add_category(self, name: str, icon: str, color: str, display_name: str = None) -> int:
        """Añade una nueva categoría"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO categories (name, icon, color, display_name)
            VALUES (?, ?, ?, ?)
        ''', (name, icon, color or '#3498db', display_name or name))
        
        category_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return category_id
    
    def delete_category(self, category_id: int) -> bool:
        """Elimina una categoría (solo si no hay tareas que la usen)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Verificar si hay tareas usando esta categoría
        cursor.execute('SELECT COUNT(*) as count FROM tasks WHERE category = (SELECT name FROM categories WHERE id = ?)', (category_id,))
        row = cursor.fetchone()
        
        if row and row['count'] > 0:
            conn.close()
            return False  # No se puede eliminar si hay tareas que la usan
        
        cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    # ========== IMÁGENES DE TAREAS ==========
    
    def add_image_to_task(self, task_id: int, file_id: str, file_path: str = None) -> int:
        """Añade una imagen a una tarea"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO task_images (task_id, file_id, file_path)
            VALUES (?, ?, ?)
        ''', (task_id, file_id, file_path))
        
        image_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return image_id
    
    def get_task_images(self, task_id: int) -> List[Dict]:
        """Obtiene todas las imágenes de una tarea"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM task_images WHERE task_id = ? ORDER BY created_at DESC', (task_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def delete_task_image(self, image_id: int) -> bool:
        """Elimina una imagen de una tarea"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM task_images WHERE id = ?', (image_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success


# Instancia global
db = Database()
