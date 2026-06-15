# permisos.py
# Lógica para distribuir permisos a las tablas de áreas

from database import conectar_db
from config import AREAS_TABLAS, AREAS

def limpiar_permisos(uid: str):
    """Elimina la tarjeta de TODAS las tablas de áreas para limpiar el estado antes de actualizar"""
    conn = conectar_db()
    if not conn: return False
    
    try:
        cur = conn.cursor()
        for tabla in AREAS_TABLAS.values():
            try:
                cur.execute(f"DELETE FROM {tabla} WHERE uid=%s", (uid,))
            except Exception as e:
                # Si una tabla no existe, la ignoramos y continuamos
                pass
        conn.commit()
        return True
    except Exception as e:
        print(f"Error limpiando permisos: {e}")
        return False
    finally:
        conn.close()

def asignar_permisos(uid: str, nombre: str, areas_raw: str):
    """Inserta la tarjeta en las tablas de áreas correspondientes (ej. 'programacion_software')"""
    conn = conectar_db()
    if not conn: return False
    
    try:
        cur = conn.cursor()
        areas_lista = [a.strip() for a in areas_raw.split(",") if a.strip()]
        
        for area_id in areas_lista:
            tabla = AREAS_TABLAS.get(area_id)
            if tabla:
                try:
                    cur.execute(f"""
                        INSERT INTO {tabla} (uid, nombre, activa) 
                        VALUES (%s, %s, 1)
                        ON DUPLICATE KEY UPDATE nombre=%s, activa=1
                    """, (uid, nombre, nombre))
                except Exception as e:
                    print(f"Error asignando permiso a tabla '{tabla}': {e}")
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error asignando permisos: {e}")
        return False
    finally:
        conn.close()

def areas_a_nombres(areas_raw: str) -> str:
    """Convierte un string de IDs ('1,2,5') a los nombres legibles ('Baños, Programación-Software, RH')"""
    partes = [a.strip() for a in areas_raw.split(",") if a.strip()]
    return ", ".join(AREAS.get(p, p) for p in partes)
