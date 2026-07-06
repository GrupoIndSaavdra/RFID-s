# areas_manager.py
# Módulo para manejar la creación dinámica de áreas

import re
import unicodedata
from database import conectar_db
import config

def sanitizar_nombre_tabla(nombre: str) -> str:
    """Convierte un nombre como 'Baños Área' a 'banos_area'"""
    # Quitar tildes y diacríticos
    nombre_limpio = ''.join(c for c in unicodedata.normalize('NFD', nombre) if unicodedata.category(c) != 'Mn')
    # Convertir a minúsculas
    nombre_limpio = nombre_limpio.lower()
    # Reemplazar caracteres no alfanuméricos por guiones bajos
    nombre_limpio = re.sub(r'[^a-z0-9]', '_', nombre_limpio)
    # Remover guiones bajos duplicados
    nombre_limpio = re.sub(r'_+', '_', nombre_limpio).strip('_')
    return nombre_limpio

def crear_nueva_area(nombre_area: str) -> bool:
    """
    Crea una nueva área en la base de datos, muta los diccionarios en memoria 
    y actualiza config.py para persistencia.
    """
    nombre_area = nombre_area.strip()
    if not nombre_area:
        return False
        
    nombre_tabla = sanitizar_nombre_tabla(nombre_area)
    if not nombre_tabla:
        return False

    # Verificar si el área ya existe en memoria
    if nombre_area in config.AREAS.values() or nombre_tabla in config.AREAS_TABLAS.values():
        return False

    # 1. Crear la tabla en la base de datos
    conn = conectar_db()
    if not conn:
        return False
        
    try:
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {nombre_tabla} (
                uid VARCHAR(50) PRIMARY KEY,
                nombre VARCHAR(100),
                activa BOOLEAN DEFAULT 1
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Error creando tabla para la nueva área: {e}")
        return False
    finally:
        conn.close()

    # 2. Determinar nuevo ID
    ids = [int(k) for k in config.AREAS.keys() if k.isdigit()]
    nuevo_id = str(max(ids) + 1) if ids else "1"

    # 3. Mutar diccionarios en memoria
    config.AREAS[nuevo_id] = nombre_area
    config.AREAS_TABLAS[nuevo_id] = nombre_tabla

    # 4. Actualizar archivo config.py
    actualizar_config_archivo()
    return True

def actualizar_config_archivo():
    """Sobrescribe el archivo config.py actualizando los bloques AREAS y AREAS_TABLAS"""
    import os
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config.py")
        with open(config_path, "r", encoding="utf-8") as f:
            contenido = f.read()

        # Construir las representaciones en string de los diccionarios
        str_areas = "AREAS = {\n"
        for k, v in config.AREAS.items():
            str_areas += f'    "{k}": "{v}",\n'
        str_areas = str_areas.rstrip(",\n") + "\n}\n"

        str_tablas = "AREAS_TABLAS = {\n"
        for k, v in config.AREAS_TABLAS.items():
            str_tablas += f'    "{k}": "{v}",\n'
        str_tablas = str_tablas.rstrip(",\n") + "\n}\n"

        # Reemplazar en el contenido original usando expresiones regulares
        contenido = re.sub(r'AREAS\s*=\s*\{.*?\}(?=\n|$)', str_areas, contenido, flags=re.DOTALL)
        contenido = re.sub(r'AREAS_TABLAS\s*=\s*\{.*?\}(?=\n|$)', str_tablas, contenido, flags=re.DOTALL)

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(contenido)
            
    except Exception as e:
        print(f"Error al escribir config.py: {e}")
