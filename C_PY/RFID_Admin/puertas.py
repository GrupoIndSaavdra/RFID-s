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
    """Obtiene la lista de todos los ESP32 registrados y su estado de actividad."""
    conn = conectar_db()
    if not conn: return []
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT mac_address, nombre, area_id, tipo,
                   IF(ultima_conexion IS NOT NULL AND TIMESTAMPDIFF(SECOND, ultima_conexion, NOW()) <= 15, 1, 0) as activa
            FROM puertas ORDER BY nombre
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"Error listando puertas: {e}")
        return []
    finally:
        conn.close()

def eliminar_puerta(mac: str) -> bool:
    """Elimina permanentemente un ESP32. Si es la última puerta de su área, elimina el área completa."""
    conn = conectar_db()
    if not conn: return False
    
    try:
        cur = conn.cursor()
        
        # 1. Obtener el area_id de la puerta antes de borrarla
        cur.execute("SELECT area_id FROM puertas WHERE mac_address=%s", (mac,))
        res = cur.fetchone()
        area_id = str(res[0]) if res else None
        
        # 2. Eliminar la puerta
        cur.execute("DELETE FROM puertas WHERE mac_address=%s", (mac,))
        conn.commit()
        
        # 3. Si se eliminó exitosamente, revisar si el área se quedó vacía
        if area_id:
            cur.execute("SELECT COUNT(*) FROM puertas WHERE area_id=%s", (area_id,))
            count = cur.fetchone()[0]
            if count == 0:
                # No quedan puertas para esta área, así que eliminamos el área (Opción A)
                import config
                import areas_manager
                
                nombre_tabla = config.AREAS_TABLAS.get(area_id)
                if nombre_tabla:
                    try:
                        cur.execute(f"DROP TABLE IF EXISTS {nombre_tabla}")
                        conn.commit()
                    except Exception as e:
                        print(f"Error borrando tabla del área {nombre_tabla}: {e}")
                
                # Remover de los diccionarios en memoria
                if area_id in config.AREAS:
                    del config.AREAS[area_id]
                if area_id in config.AREAS_TABLAS:
                    del config.AREAS_TABLAS[area_id]
                
                # Guardar en config.py
                areas_manager.actualizar_config_archivo()
                
        return True
    except Exception as e:
        print(f"Error eliminando puerta: {e}")
        return False
    finally:
        conn.close()
