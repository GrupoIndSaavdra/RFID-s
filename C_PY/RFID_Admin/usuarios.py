# usuarios.py
# Módulo para el manejo del CRUD de la tabla maestra 'tarjetas'

from database import conectar_db
import permisos

def registrar_usuario(uid: str, nombre: str, areas_raw: str) -> bool:
    """Da de alta un usuario en el directorio y actualiza sus permisos."""
    conn = conectar_db()
    if not conn: return False
    
    try:
        cur = conn.cursor()
        
        # 1. Actualizar tabla maestra
        cur.execute("""
            INSERT INTO tarjetas (uid, nombre, areas)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE nombre=%s, areas=%s, activa=1
        """, (uid, nombre, areas_raw, nombre, areas_raw))
        
        conn.commit()
        
        # 2. Re-asignar los permisos
        permisos.limpiar_permisos(uid)
        permisos.asignar_permisos(uid, nombre, areas_raw)
        
        return True
    except Exception as e:
        print(f"Error registrando usuario: {e}")
        return False
    finally:
        conn.close()

def listar_usuarios() -> list:
    """Obtiene la lista de todas las tarjetas registradas y ordenadas por nombre"""
    conn = conectar_db()
    if not conn: return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT uid, nombre, areas, fecha_registro, activa FROM tarjetas ORDER BY nombre")
        return cur.fetchall()
    except Exception as e:
        print(f"Error listando usuarios: {e}")
        return []
    finally:
        conn.close()

def buscar_usuario(uid: str):
    """Busca un usuario en la base de datos por su UID"""
    conn = conectar_db()
    if not conn: return None
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT uid, nombre, areas, activa FROM tarjetas WHERE uid=%s", (uid,))
        return cur.fetchone()
    except Exception as e:
        return None
    finally:
        conn.close()

def eliminar_usuario(uid: str) -> bool:
    """Elimina permanentemente una tarjeta de la tabla maestra y le retira todos los permisos"""
    conn = conectar_db()
    if not conn: return False
    
    try:
        cur = conn.cursor()
        
        # 1. Eliminar de la maestra
        cur.execute("DELETE FROM tarjetas WHERE uid=%s", (uid,))
        conn.commit()
        
        # 2. Retirar permisos en las demás tablas
        permisos.limpiar_permisos(uid)
        
        return True
    except Exception as e:
        print(f"Error eliminando usuario: {e}")
        return False
    finally:
        conn.close()

def obtener_uids_activos() -> list:
    """Retorna una lista de puros UIDs para sincronizar con el ESP32"""
    conn = conectar_db()
    if not conn: return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT uid FROM tarjetas WHERE activa=1")
        return [row[0] for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()

def obtener_uids_activos_por_area(area_id: str) -> list:
    """Retorna los UIDs de las tarjetas activas que tienen acceso a una área específica."""
    conn = conectar_db()
    if not conn: return []
    
    try:
        cur = conn.cursor()
        # Asumiendo que 'areas' contiene una lista separada por comas (ej: "1,2,5")
        cur.execute("SELECT uid FROM tarjetas WHERE activa=1 AND FIND_IN_SET(%s, areas) > 0", (area_id,))
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"Error obteniendo UIDs por área: {e}")
        return []
    finally:
        conn.close()
