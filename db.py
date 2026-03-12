import json
import os
import pymysql
import datetime

CONFIG_FILE = 'nex.json'

def get_connection():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        config = data.get('MySqlConfig', {})
    
    return pymysql.connect(
        host=config.get('Server', 'localhost'),
        user=config.get('Uid', 'root'),
        password=config.get('Pwd', ''),
        database=config.get('Database', 'Nexus'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def init_db():
    conn = get_connection()
    if not conn:
        print("Could not connect to Database. Check nex.json.")
        return
    try:
        with conn.cursor() as cursor:
            # Create main config table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_items (
                    config_id VARCHAR(8) PRIMARY KEY,
                    category VARCHAR(1) NOT NULL,
                    abbr VARCHAR(3) NOT NULL,
                    seq VARCHAR(4) NOT NULL,
                    description LONGTEXT,
                    content LONGTEXT,
                    updated_at DATETIME NOT NULL,
                    is_deleted TINYINT(1) DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            # Create config history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    config_id VARCHAR(8) NOT NULL,
                    description LONGTEXT,
                    content LONGTEXT,
                    updated_at DATETIME NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
    finally:
        conn.close()

def get_configs(filters=None):
    if filters is None:
        filters = {}
    
    query = "SELECT * FROM config_items WHERE is_deleted = 0"
    params = []
    
    if 'config_id' in filters and filters['config_id']:
        query += " AND config_id LIKE %s"
        params.append(f"%{filters['config_id']}%")
    if 'category' in filters and filters['category']:
        query += " AND category = %s"
        params.append(filters['category'])
    if 'abbr' in filters and filters['abbr']:
        query += " AND abbr = %s"
        params.append(filters['abbr'])
    if 'seq' in filters and filters['seq']:
        query += " AND seq = %s"
        params.append(filters['seq'])
    
    if 'keyword' in filters and filters['keyword']:
        kw = f"%{filters['keyword']}%"
        query += " AND (description LIKE %s OR content LIKE %s)"
        params.extend([kw, kw])
        
    if 'update_time_start' in filters and filters['update_time_start']:
        query += " AND updated_at >= %s"
        params.append(filters['update_time_start'] + " 00:00:00")
        
    if 'update_time_end' in filters and filters['update_time_end']:
        query += " AND updated_at <= %s"
        params.append(filters['update_time_end'] + " 23:59:59")
        
    query += " ORDER BY updated_at DESC"
    
    conn = get_connection()
    if not conn: return []
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    finally:
        conn.close()

def get_config_by_id(config_id):
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM config_items WHERE config_id = %s AND is_deleted = 0", (config_id,))
            return cursor.fetchone()
    finally:
        conn.close()

def add_config(config_id, category, abbr, seq, description, content):
    conn = get_connection()
    if not conn: return False
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO config_items (config_id, category, abbr, seq, description, content, updated_at, is_deleted)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
            """, (config_id, category, abbr, seq, description, content, now))
            
            cursor.execute("""
                INSERT INTO config_history (config_id, description, content, updated_at)
                VALUES (%s, %s, %s, %s)
            """, (config_id, description, content, now))
        return True
    except Exception as e:
        print(f"Error adding config: {e}")
        return False
    finally:
        conn.close()

def update_config(config_id, description, content):
    conn = get_connection()
    if not conn: return False
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE config_items 
                SET description = %s, content = %s, updated_at = %s
                WHERE config_id = %s AND is_deleted = 0
            """, (description, content, now, config_id))
            
            cursor.execute("""
                INSERT INTO config_history (config_id, description, content, updated_at)
                VALUES (%s, %s, %s, %s)
            """, (config_id, description, content, now))
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
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE config_items 
                SET is_deleted = 1, updated_at = %s
                WHERE config_id = %s
            """, (now, config_id))
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
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM config_history 
                WHERE config_id = %s 
                ORDER BY updated_at DESC
            """, (config_id,))
            return cursor.fetchall()
    finally:
        conn.close()
