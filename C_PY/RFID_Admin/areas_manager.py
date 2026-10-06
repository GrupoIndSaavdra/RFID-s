# areas_manager.py
# Módulo para manejar la creación dinámica de áreas

import re, unicodedata, os
from database import conectar_db
import config

def sanitizar_nombre_tabla(nombre: str) -> str:
    """Convierte 'Baños Área' a 'banos_area'"""
    s = ''.join(c for c in unicodedata.normalize('NFD', nombre) if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'_+', '_', re.sub(r'[^a-z0-9]', '_', s)).strip('_')

def crear_nueva_area(nombre_area: str) -> bool:
    """Crea una nueva área, muta config en memoria y actualiza config.py."""
    if not (n := nombre_area.strip()) or not (t := sanitizar_nombre_tabla(n)): return False
    if n in config.AREAS.values() or t in config.AREAS_TABLAS.values(): return False
    
    if not (conn := conectar_db()): return False
    try:
        conn.cursor().execute(f"CREATE TABLE IF NOT EXISTS {t} (uid VARCHAR(50) PRIMARY KEY, nombre VARCHAR(100), activa BOOLEAN DEFAULT 1)")
        conn.commit()
    except Exception as e: print(f"Error creando tabla: {e}"); return False
    finally: conn.close()

    nid = str(max([int(k) for k in config.AREAS if k.isdigit()] + [0]) + 1)
    config.AREAS[nid], config.AREAS_TABLAS[nid] = n, t
    actualizar_config_archivo()
    return True

def actualizar_config_archivo():
    """Sobrescribe config.py con AREAS y AREAS_TABLAS actualizadas"""
    try:
        ruta = os.path.join(os.path.dirname(__file__), "config.py")
        with open(ruta, "r", encoding="utf-8") as f: c = f.read()
        
        f_dict = lambda d, n: f"{n} = {{\n" + "".join(f'    "{k}": "{v}",\n' for k, v in d.items()) + "}\n"
        c = re.sub(r'AREAS\s*=\s*\{.*?\}(?=\n|$)', f_dict(config.AREAS, 'AREAS'), c, flags=re.DOTALL)
        c = re.sub(r'AREAS_TABLAS\s*=\s*\{.*?\}(?=\n|$)', f_dict(config.AREAS_TABLAS, 'AREAS_TABLAS'), c, flags=re.DOTALL)
        
        with open(ruta, "w", encoding="utf-8") as f: f.write(c)
    except Exception as e: print(f"Error actualizando config.py: {e}")
