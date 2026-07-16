# database.py
# Módulo de conexión a la base de datos

import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG
import hashlib

def conectar_db():
    """Establece la conexión con la base de datos MySQL usando los datos de config.py"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"Error al conectar con la base de datos: {e}")
        return None

def inicializar_db():
    """Crea la tabla de admin_users si no existe y un usuario por defecto."""
    conn = conectar_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(64) NOT NULL,
                rol VARCHAR(20) NOT NULL
            )
        """)
        conn.commit()

        # Verificar si hay usuarios, si no, crear el usuario por defecto
        cur.execute("SELECT COUNT(*) FROM admin_users")
        count = cur.fetchone()[0]
        if count == 0:
            # Crear usuario administrador por defecto (admin/admin con rol ingeniero)
            # y un usuario de RH (rh/rh con rol operador)
            default_pass_hash = hashlib.sha256("admin".encode()).hexdigest()
            rh_pass_hash = hashlib.sha256("rh".encode()).hexdigest()
            
            cur.execute("""
                INSERT INTO admin_users (username, password_hash, rol)
                VALUES (%s, %s, %s), (%s, %s, %s)
            """, ("admin", default_pass_hash, "ingeniero", "rh", rh_pass_hash, "operador"))
            conn.commit()
            print("Se crearon los usuarios administradores por defecto (admin y rh).")
    except Error as e:
        print(f"Error al inicializar la base de datos: {e}")
    finally:
        conn.close()
