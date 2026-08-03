# usuarios.py
# Módulo para el manejo del CRUD de la tabla maestra 'tarjetas'

from database import conectar_db
import permisos

def registrar_usuario(uid: str, nombre: str, rol: str, areas_raw: str) -> bool:
    """Da de alta un usuario en el directorio y actualiza sus permisos."""
    conn = conectar_db()
    if not conn: return False
    
    try:
        cur = conn.cursor()
        
        # 1. Actualizar tabla maestra
        cur.execute("""
            INSERT INTO tarjetas (uid, nombre, rol, areas)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE nombre=%s, rol=%s, areas=%s, activa=1
        """, (uid, nombre, rol, areas_raw, nombre, rol, areas_raw))
        
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
        cur.execute("SELECT uid, nombre, rol, areas, fecha_registro, activa, fecha_modificacion FROM tarjetas ORDER BY nombre")
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
        cur.execute("SELECT uid, nombre, rol, areas, activa FROM tarjetas WHERE uid=%s", (uid,))
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

def obtener_roles_unicos() -> list:
    """Retorna una lista de todos los roles únicos desde la tabla oficial de roles."""
    conn = conectar_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM roles ORDER BY nombre")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"Error obteniendo roles: {e}")
        return []
    finally:
        conn.close()

def registrar_rol(nombre: str) -> bool:
    """Registra un nuevo rol en la base de datos."""
    conn = conectar_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("INSERT IGNORE INTO roles (nombre) VALUES (%s)", (nombre,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error registrando rol: {e}")
        return False
    finally:
        conn.close()

def asignar_area_masiva(rol: str, area_id: str) -> int:
    """Asigna un área a todos los usuarios que tengan el rol especificado."""
    conn = conectar_db()
    if not conn: return 0
    
    afectados = 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT uid, nombre, areas FROM tarjetas WHERE rol=%s AND activa=1", (rol,))
        usuarios = cur.fetchall()
        
        for u in usuarios:
            uid = u[0]
            nombre = u[1]
            areas = u[2]
            
            lista_areas = [a.strip() for a in areas.split(",")] if areas else []
            if area_id not in lista_areas:
                lista_areas.append(area_id)
                nuevas_areas = ",".join(lista_areas)
                
                # Actualizar tarjeta maestra
                cur.execute("UPDATE tarjetas SET areas=%s WHERE uid=%s", (nuevas_areas, uid))
                
                # Actualizar tablas de permisos
                permisos.limpiar_permisos(uid)
                permisos.asignar_permisos(uid, nombre, nuevas_areas)
                afectados += 1
                
        conn.commit()
        return afectados
    except Exception as e:
        print(f"Error en asignación masiva: {e}")
        return 0
    finally:
        conn.close()
