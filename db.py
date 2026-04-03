import os
import sqlite3
import datetime

DB_FILE = 'nexus.db'

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Create main config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config_items (
                config_id VARCHAR(8) PRIMARY KEY,
                category VARCHAR(1) NOT NULL,
                abbr VARCHAR(3) NOT NULL,
                seq VARCHAR(4) NOT NULL,
                description TEXT,
                param_desc TEXT,
                content TEXT,
                updated_at DATETIME NOT NULL,
                is_deleted INTEGER DEFAULT 0
            );
        """)
        # Create config history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_id VARCHAR(8) NOT NULL,
                description TEXT,
                param_desc TEXT,
                content TEXT,
                updated_at DATETIME NOT NULL
            );
        """)
        conn.commit()
    except Exception as e:
        print(f"Error initializing db: {e}")
    finally:
        conn.close()

def get_configs(filters=None):
    if filters is None:
        filters = {}
    
    query = "SELECT * FROM config_items WHERE is_deleted = 0"
    params = []
    
    if 'config_id' in filters and filters['config_id']:
        query += " AND config_id LIKE ?"
        params.append(f"%{filters['config_id']}%")
    if 'category' in filters and filters['category']:
        query += " AND category = ?"
        params.append(filters['category'])
    if 'abbr' in filters and filters['abbr']:
        query += " AND abbr = ?"
        params.append(filters['abbr'])
    if 'seq' in filters and filters['seq']:
        query += " AND seq = ?"
        params.append(filters['seq'])
    
    if 'keyword' in filters and filters['keyword']:
        kw = f"%{filters['keyword']}%"
        query += " AND (description LIKE ? OR content LIKE ?)"
        params.extend([kw, kw])
        
    if 'update_time_start' in filters and filters['update_time_start']:
        query += " AND updated_at >= ?"
        params.append(filters['update_time_start'] + " 00:00:00")
        
    if 'update_time_end' in filters and filters['update_time_end']:
        query += " AND updated_at <= ?"
        params.append(filters['update_time_end'] + " 23:59:59")
        
    query += " ORDER BY updated_at DESC"
    
    conn = get_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_config_by_id(config_id):
    conn = get_connection()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM config_items WHERE config_id = ? AND is_deleted = 0", (config_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def add_config(config_id, category, abbr, seq, description, param_desc, content):
    conn = get_connection()
    if not conn: return False
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO config_items (config_id, category, abbr, seq, description, param_desc, content, updated_at, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (config_id, category, abbr, seq, description, param_desc, content, now))
        
        cursor.execute("""
            INSERT INTO config_history (config_id, description, param_desc, content, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (config_id, description, param_desc, content, now))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding config: {e}")
        return False
    finally:
        conn.close()

def update_config(config_id, description, param_desc, content):
    conn = get_connection()
    if not conn: return False
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE config_items 
            SET description = ?, param_desc = ?, content = ?, updated_at = ?
            WHERE config_id = ? AND is_deleted = 0
        """, (description, param_desc, content, now, config_id))
        
        cursor.execute("""
            INSERT INTO config_history (config_id, description, param_desc, content, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (config_id, description, param_desc, content, now))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating config: {e}")
        return False
    finally:
        conn.close()

def delete_config(config_id):
    conn = get_connection()
    if not conn: return False
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE config_items 
            SET is_deleted = 1, updated_at = ?
            WHERE config_id = ?
        """, (now, config_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting config: {e}")
        return False
    finally:
        conn.close()

def get_history(config_id):
    conn = get_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM config_history 
            WHERE config_id = ? 
            ORDER BY updated_at DESC
        """, (config_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
