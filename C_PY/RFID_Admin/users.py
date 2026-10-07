from logger import log_error

# users.py
# Módulo para el manejo del CRUD de la tabla maestra 'tarjetas'

from database import conectar_db
import permissions


def registrar_usuario(uid: str, nombre: str, rol: str, areas_raw: str) -> bool:
    if not (conn := conectar_db()):
        return False
    try:
        conn.cursor().execute(
            "INSERT INTO tarjetas (uid, nombre, rol, areas) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE nombre=%s, rol=%s, areas=%s, activa=1",
            (uid, nombre, rol, areas_raw, nombre, rol, areas_raw),
        )
        conn.commit()
        permissions.limpiar_permisos(uid)
        permissions.asignar_permisos(uid, nombre, areas_raw)
        return True
    except Exception as e:
        log_error(f"Error registrando usuario: {e}")
        return False
    finally:
        conn.close()


def listar_usuarios(limit=None, offset=0) -> list:
    if not (conn := conectar_db()):
        return []
    try:
        import config

        cur = conn.cursor()
        query = "SELECT uid, nombre, rol, areas, fecha_registro, activa, fecha_modificacion FROM tarjetas ORDER BY nombre"
        params = []
        if limit:
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        cur.execute(query, tuple(params))
        res = []
        for u, n, r, a, fr, act, fm in cur.fetchall():
            a_list = [x.strip() for x in a.split(",") if x.strip()]
            if len(a_val := [x for x in a_list if str(x) in config.AREAS]) < len(
                a_list
            ):
                a = ", ".join(a_val)
                try:
                    cur.execute("UPDATE tarjetas SET areas=%s WHERE uid=%s", (a, u))
                    conn.commit()
                except:
                    pass
            res.append((u, n, r, a, fr, act, fm))
        return res
    except Exception as e:
        log_error(f"Error listando usuarios: {e}")
        return []
    finally:
        conn.close()


def buscar_usuario(uid: str):
    if not (conn := conectar_db()):
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT uid, nombre, rol, areas, activa FROM tarjetas WHERE uid=%s", (uid,)
        )
        return cur.fetchone()
    except:
        return None
    finally:
        conn.close()


def eliminar_usuario(uid: str) -> bool:
    if not (conn := conectar_db()):
        return False
    try:
        conn.cursor().execute("DELETE FROM tarjetas WHERE uid=%s", (uid,))
        conn.commit()
        permissions.limpiar_permisos(uid)
        return True
    except Exception as e:
        log_error(f"Error eliminando usuario: {e}")
        return False
    finally:
        conn.close()


def obtener_uids_activos() -> list:
    if not (conn := conectar_db()):
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT uid FROM tarjetas WHERE activa=1")
        return [r[0] for r in cur.fetchall()]
    except:
        return []
    finally:
        conn.close()


def obtener_uids_activos_por_area(area_id: str) -> list:
    if not (conn := conectar_db()):
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT uid FROM tarjetas WHERE activa=1 AND FIND_IN_SET(%s, areas) > 0",
            (area_id,),
        )
        return [r[0] for r in cur.fetchall()]
    except Exception as e:
        log_error(f"Error obteniendo UIDs por área: {e}")
        return []
    finally:
        conn.close()


def obtener_roles_unicos() -> list:
    if not (conn := conectar_db()):
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM roles ORDER BY nombre")
        return [r[0] for r in cur.fetchall()]
    except Exception as e:
        log_error(f"Error obteniendo roles: {e}")
        return []
    finally:
        conn.close()


def registrar_rol(nombre: str) -> bool:
    if not (conn := conectar_db()):
        return False
    try:
        conn.cursor().execute(
            "INSERT IGNORE INTO roles (nombre) VALUES (%s)", (nombre,)
        )
        conn.commit()
        return True
    except Exception as e:
        log_error(f"Error registrando rol: {e}")
        return False
    finally:
        conn.close()


def asignar_area_masiva(rol: str, area_id: str) -> int:
    if not (conn := conectar_db()):
        return 0
    afectados = 0
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT uid, nombre, areas FROM tarjetas WHERE rol=%s AND activa=1", (rol,)
        )
        for u, n, a in cur.fetchall():
            lista = [x.strip() for x in a.split(",")] if a else []
            if area_id not in lista:
                nuevas = ",".join(lista + [area_id])
                cur.execute("UPDATE tarjetas SET areas=%s WHERE uid=%s", (nuevas, u))
                permissions.limpiar_permisos(u)
                permissions.asignar_permisos(u, n, nuevas)
                afectados += 1
        conn.commit()
        return afectados
    except Exception as e:
        log_error(f"Error en asignación masiva: {e}")
        return 0
    finally:
        conn.close()
