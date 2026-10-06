# database.py
import mysql.connector, hashlib
from mysql.connector import pooling
from config import DB_CONFIG

try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="rfid_pool", pool_size=5, pool_reset_session=True, **DB_CONFIG)
except Exception as e:
    print(f"Error creando el pool de conexiones: {e}"); db_pool = None

def conectar_db():
    if not db_pool: return None
    try: return db_pool.get_connection()
    except Exception as e: print(f"Error obteniendo conexión del pool: {e}"); return None

def inicializar_db():
    if not (conn := conectar_db()): return
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS admin_users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password_hash VARCHAR(64) NOT NULL, rol VARCHAR(20) NOT NULL)")
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM admin_users")
        if cur.fetchone()[0] == 0:
            p_a, p_r = hashlib.sha256(b"admin").hexdigest(), hashlib.sha256(b"rh").hexdigest()
            cur.execute("INSERT INTO admin_users (username, password_hash, rol) VALUES (%s, %s, %s), (%s, %s, %s)", ("admin", p_a, "ingeniero", "rh", p_r, "operador"))
            conn.commit()
            
        try:
            cur.execute("ALTER TABLE tarjetas ADD INDEX idx_activa (activa)")
            cur.execute("ALTER TABLE tarjetas ADD INDEX idx_rol (rol)")
            cur.execute("ALTER TABLE puertas ADD INDEX idx_area_id (area_id)")
            conn.commit()
        except: pass # Índices ya existen o tablas no creadas aún
            
    except Exception as e: print(f"Error al inicializar la base de datos: {e}")
    finally: conn.close()
