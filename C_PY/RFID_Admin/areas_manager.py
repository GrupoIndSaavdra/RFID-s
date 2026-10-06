from logger import log_error
# areas_manager.py
# Módulo para manejar la creación dinámica de áreas

import re, unicodedata
from database import conectar_db
import config

def sanitizar_nombre_tabla(nombre: str) -> str:
    """Convierte 'Baños Área' a 'banos_area'"""
    s = ''.join(c for c in unicodedata.normalize('NFD', nombre) if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'_+', '_', re.sub(r'[^a-z0-9]', '_', s)).strip('_')

def crear_nueva_area(nombre_area: str) -> bool:
    """Crea una nueva área en la BD y muta config en memoria."""
    if not (n := nombre_area.strip()) or not (t := sanitizar_nombre_tabla(n)): return False
    if n in config.AREAS.values() or t in config.AREAS_TABLAS.values(): return False
    
    if not (conn := conectar_db()): return False
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO config_areas (nombre, tabla) VALUES (%s, %s)", (n, t))
        nid = str(cur.lastrowid)
        cur.execute(f"CREATE TABLE IF NOT EXISTS {t} (uid VARCHAR(50) PRIMARY KEY, nombre VARCHAR(100), activa BOOLEAN DEFAULT 1)")
        conn.commit()
        config.AREAS[nid] = n
        config.AREAS_TABLAS[nid] = t
        return True
    except Exception as e: log_error(f"Error creando tabla o registrando area: {e}"); return False
    finally: conn.close()
