# doors.py
# Módulo para el manejo del CRUD de la tabla 'puertas' (ESP32 Wi-Fi)

from database import conectar_db

def registrar_puerta(mac: str, nombre: str, area_id: str, tipo: str = "Entrada") -> bool:
    if not (conn := conectar_db()): return False
    try:
        conn.cursor().execute("INSERT INTO puertas (mac_address, nombre, area_id, tipo) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE nombre=%s, area_id=%s, tipo=%s", (mac, nombre, area_id, tipo, nombre, area_id, tipo))
        conn.commit()
        return True
    except Exception as e: print(f"Error registrando puerta: {e}"); return False
    finally: conn.close()

def listar_puertas() -> list:
    if not (conn := conectar_db()): return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT mac_address, nombre, area_id, tipo, IF(ultima_conexion IS NOT NULL AND TIMESTAMPDIFF(SECOND, ultima_conexion, NOW()) <= 15, 1, 0) as activa FROM puertas ORDER BY nombre")
        return cur.fetchall()
    except Exception as e: print(f"Error listando puertas: {e}"); return []
    finally: conn.close()

def eliminar_puerta(mac: str) -> bool:
    if not (conn := conectar_db()): return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT area_id FROM puertas WHERE mac_address=%s", (mac,))
        area_id = str(res[0]) if (res := cur.fetchone()) else None
        
        cur.execute("DELETE FROM puertas WHERE mac_address=%s", (mac,))
        conn.commit()
        
        if area_id:
            cur.execute("SELECT COUNT(*) FROM puertas WHERE area_id=%s", (area_id,))
            if cur.fetchone()[0] == 0:
                import config, areas_manager
                if t_name := config.AREAS_TABLAS.get(area_id):
                    try: cur.execute(f"DROP TABLE IF EXISTS {t_name}"); conn.commit()
                    except Exception as e: print(f"Error borrando tabla del área {t_name}: {e}")
                
                config.AREAS.pop(area_id, None)
                config.AREAS_TABLAS.pop(area_id, None)
                areas_manager.actualizar_config_archivo()
        return True
    except Exception as e: print(f"Error eliminando puerta: {e}"); return False
    finally: conn.close()
