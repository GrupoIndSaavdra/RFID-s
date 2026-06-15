# puertas.py
# Módulo para el manejo del CRUD de la tabla 'puertas' (ESP32 Wi-Fi)

from database import conectar_db

def registrar_puerta(mac: str, nombre: str, area_id: str, tipo: str = "Entrada") -> bool:
    """Registra o actualiza un ESP32 en la base de datos."""
    conn = conectar_db()
    if not conn: return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO puertas (mac_address, nombre, area_id, tipo)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE nombre=%s, area_id=%s, tipo=%s
        """, (mac, nombre, area_id, tipo, nombre, area_id, tipo))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error registrando puerta: {e}")
        return False
    finally:
        conn.close()

def listar_puertas() -> list:
    """Obtiene la lista de todos los ESP32 registrados."""
    conn = conectar_db()
    if not conn: return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT mac_address, nombre, area_id, tipo FROM puertas ORDER BY nombre")
        return cur.fetchall()
    except Exception as e:
        print(f"Error listando puertas: {e}")
        return []
    finally:
        conn.close()

def eliminar_puerta(mac: str) -> bool:
    """Elimina permanentemente un ESP32."""
    conn = conectar_db()
    if not conn: return False
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM puertas WHERE mac_address=%s", (mac,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error eliminando puerta: {e}")
        return False
    finally:
        conn.close()
