import hashlib
from typing import Optional, Any
import mysql.connector
from mysql.connector import pooling
from config import DB_CONFIG
from logger import log_error

try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="rfid_pool", pool_size=5, pool_reset_session=True, **DB_CONFIG
    )
except Exception as e:
    log_error(f"Error creating connection pool: {e}")
    db_pool = None


def conectar_db() -> Optional[Any]:
    """
    Retrieves a connection from the MySQL connection pool.

    Returns:
        Optional[Any]: A MySQL connection object if successful, None otherwise.
    """
    if not db_pool:
        return None
    try:
        return db_pool.get_connection()
    except Exception as e:
        log_error(f"Error obtaining connection from pool: {e}")
        return None


def inicializar_db() -> None:
    """
    Initializes the database schema by creating necessary tables and default data
    if they do not already exist. It also populates the in-memory global config.
    """
    conn = conectar_db()
    if not conn:
        return

    try:
        cur = conn.cursor()

        # Create admin_users table
        cur.execute(
            "CREATE TABLE IF NOT EXISTS admin_users ("
            "id INT AUTO_INCREMENT PRIMARY KEY, "
            "username VARCHAR(50) UNIQUE NOT NULL, "
            "password_hash VARCHAR(64) NOT NULL, "
            "rol VARCHAR(20) NOT NULL)"
        )
        conn.commit()

        # Insert default users if table is empty
        cur.execute("SELECT COUNT(*) FROM admin_users")
        if cur.fetchone()[0] == 0:
            p_a = hashlib.sha256(b"admin").hexdigest()
            p_r = hashlib.sha256(b"rh").hexdigest()
            cur.execute(
                "INSERT INTO admin_users (username, password_hash, rol) VALUES (%s, %s, %s), (%s, %s, %s)",
                ("admin", p_a, "ingeniero", "rh", p_r, "operador"),
            )
            conn.commit()

        # Create config_areas table
        cur.execute(
            "CREATE TABLE IF NOT EXISTS config_areas ("
            "id INT AUTO_INCREMENT PRIMARY KEY, "
            "nombre VARCHAR(100) UNIQUE, "
            "tabla VARCHAR(100) UNIQUE)"
        )
        conn.commit()

        # Insert default areas if table is empty
        cur.execute("SELECT COUNT(*) FROM config_areas")
        if cur.fetchone()[0] == 0:
            default_areas = [
                ("Baños", "banos"),
                ("Calidad", "calidad"),
                ("Almacén", "almacen"),
                ("RH", "rh"),
                ("Mantenimiento", "mantenimiento"),
                ("Comedor", "comedor"),
                ("Gerencia", "oficina_de_gerencia"),
                ("Producción", "oficina_de_produccion"),
                ("Sala de Juntas", "sala_de_juntas"),
                ("Programacion-Software", "programacion_software"),
            ]
            cur.executemany(
                "INSERT INTO config_areas (nombre, tabla) VALUES (%s, %s)",
                default_areas,
            )
            conn.commit()

        # Load areas into global config
        import config

        cur.execute("SELECT id, nombre, tabla FROM config_areas")
        config.AREAS.clear()
        config.AREAS_TABLAS.clear()
        for a_id, n, t in cur.fetchall():
            config.AREAS[str(a_id)] = n
            config.AREAS_TABLAS[str(a_id)] = t

        # Add indexes, ignore if they already exist
        try:
            cur.execute("ALTER TABLE tarjetas ADD INDEX idx_activa (activa)")
            cur.execute("ALTER TABLE tarjetas ADD INDEX idx_rol (rol)")
            cur.execute("ALTER TABLE puertas ADD INDEX idx_area_id (area_id)")
            conn.commit()
        except Exception:
            pass  # Indexes already exist or tables not created yet

    except Exception as e:
        log_error(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()
