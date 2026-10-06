# permissions.py
# Lógica para distribuir permisos a las tablas de áreas

from database import conectar_db
from config import AREAS_TABLAS, AREAS

def limpiar_permisos(uid: str):
    if not (conn := conectar_db()): return False
    try:
        cur = conn.cursor()
        for t in AREAS_TABLAS.values():
            try: cur.execute(f"UPDATE {t} SET activa=0 WHERE uid=%s", (uid,))
            except: pass
        conn.commit()
        return True
    except Exception as e: print(f"Error limpiando permisos: {e}"); return False
    finally: conn.close()

def asignar_permisos(uid: str, nombre: str, areas_raw: str):
    if not (conn := conectar_db()): return False
    try:
        cur = conn.cursor()
        for a_id in [a.strip() for a in areas_raw.split(",") if a.strip()]:
            if t := AREAS_TABLAS.get(a_id):
                try: cur.execute(f"INSERT INTO {t} (uid, nombre, activa) VALUES (%s, %s, 1) ON DUPLICATE KEY UPDATE nombre=%s, activa=1", (uid, nombre, nombre))
                except Exception as e: print(f"Error asignando permiso a tabla '{t}': {e}")
        conn.commit()
        return True
    except Exception as e: print(f"Error asignando permisos: {e}"); return False
    finally: conn.close()

def areas_a_nombres(areas_raw: str) -> str:
    return ", ".join(AREAS.get(p, p) for p in [a.strip() for a in areas_raw.split(",") if a.strip()])
