# ============================================================
# Sistema de Control RFID — Monitor en Vivo (Wi-Fi)
# ============================================================

import time
import tkinter as tk
from tkinter import ttk
import mysql.connector
from mysql.connector import Error

# ── Configuracion MySQL (XAMPP) ──────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",
    "database": "rfid_db"
}

def conectar_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        return None

def db_buscar_tarjeta(uid: str):
    conn = conectar_db()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT uid, nombre, areas, activa FROM tarjetas WHERE uid=%s", (uid,))
        return cur.fetchone()
    except Error:
        return None
    finally:
        conn.close()

# ── Areas y Mapeos de Departamentos ──────────────────────────
AREAS = {
    "1": "Baños",
    "2": "Programación-Software",
    "3": "Calidad",
    "4": "Almacén",
    "5": "RH",
    "6": "Mantenimiento",
    "7": "Comedor",
    "8": "Gerencia",
    "9": "Producción",
    "10": "Sala de Juntas"
}

AREAS_TABLAS = {
    "1": "banos",
    "2": "programacion_software",
    "3": "calidad",
    "4": "almacen",
    "5": "rh",
    "6": "mantenimiento",
    "7": "comedor",
    "8": "oficina_de_gerencia",
    "9": "oficina_de_produccion",
    "10": "sala_de_juntas"
}

def obtener_id_por_tabla(area_tabla: str) -> str:
    """Busca el ID correspondiente al nombre de tabla del área"""
    if not area_tabla:
        return None
    for k, v in AREAS_TABLAS.items():
        if v == area_tabla.lower().strip():
            return k
    return None

def obtener_nombre_area(area_tabla: str) -> str:
    """Retorna el nombre legible del área"""
    aid = obtener_id_por_tabla(area_tabla)
    if aid and aid in AREAS:
        return AREAS[aid]
    if area_tabla:
        return area_tabla.replace("_", " ").title()
    return "Desconocido"

# ============================================================
# APLICACION GUI: MONITOR EN VIVO
# ============================================================

class MonitorRFID(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Monitor de Accesos Wi-Fi - RFID")
        self.geometry("750x550")
        self.configure(bg="#09090B")
        
        self.running = True
        self.last_log_id = 0 
        self.permitidos_count = 0
        self.denegados_count = 0
        
        self.crear_interfaz()
        
        # Iniciar el monitoreo de la BD
        self.after(1000, self.consultar_logs_wifi)

    def crear_interfaz(self):
        # Header Container
        header_frame = tk.Frame(self, bg="#18181B", height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        lbl_titulo = tk.Label(
            header_frame, 
            text="📡 SISTEMA RFID — MONITOR DE ACCESOS EN VIVO", 
            font=("Segoe UI", 12, "bold"), 
            bg="#18181B", 
            fg="#F4F4F5"
        )
        lbl_titulo.pack(side=tk.LEFT, padx=20, pady=15)

        # Status indicator
        self.lbl_status_indicator = tk.Label(
            header_frame,
            text="● ESP32 ONLINE",
            font=("Segoe UI", 10, "bold"),
            bg="#18181B",
            fg="#10B981"
        )
        self.lbl_status_indicator.pack(side=tk.RIGHT, padx=20, pady=15)

        # Main container with nice dark background
        main_frame = tk.Frame(self, bg="#09090B")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Consola de logs with custom padding & style
        self.txt_log = tk.Text(
            main_frame, 
            state=tk.DISABLED, 
            bg="#18181B", 
            fg="#E4E4E7", 
            font=("Consolas", 11), 
            relief=tk.FLAT,
            padx=15,
            pady=15,
            insertbackground="white" # cursor color
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # Configure tags
        self.txt_log.tag_config("red", foreground="#EF4444")
        self.txt_log.tag_config("green", foreground="#10B981")
        self.txt_log.tag_config("gray", foreground="#71717A")
        self.txt_log.tag_config("white", foreground="#E4E4E7")
        
        # Stats & footer bar
        footer_frame = tk.Frame(self, bg="#18181B", height=40)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)

        self.lbl_stats = tk.Label(
            footer_frame,
            text="Resumen de Sesión:  Permitidos: 0  |  Denegados: 0",
            font=("Segoe UI", 9, "bold"),
            bg="#18181B",
            fg="#A1A1AA"
        )
        self.lbl_stats.pack(side=tk.LEFT, padx=20, pady=10)

        lbl_footer_right = tk.Label(
            footer_frame,
            text="Antigravity Secure v2.0",
            font=("Segoe UI", 9, "italic"),
            bg="#18181B",
            fg="#71717A"
        )
        lbl_footer_right.pack(side=tk.RIGHT, padx=20, pady=10)
        
        self.escribir_log("Iniciando conexión con base de datos...\n", "gray")
        self.escribir_log("Esperando registros Wi-Fi de los módulos ESP32...\n", "gray")
        self.escribir_log("-" * 75 + "\n", "gray")

    def actualizar_stats(self):
        self.lbl_stats.config(
            text=f"Resumen de Sesión:  Permitidos: {self.permitidos_count}  |  Denegados: {self.denegados_count}"
        )

    def consultar_logs_wifi(self):
        """Consulta la base de datos por nuevos accesos enviados vía Wi-Fi"""
        conn = conectar_db()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT id, uid, area, fecha FROM registros_acceso WHERE id > %s ORDER BY id ASC", (self.last_log_id,))
                nuevos_logs = cur.fetchall()
                for log in nuevos_logs:
                    log_id, uid, area, fecha = log
                    self.last_log_id = log_id
                    
                    row = db_buscar_tarjeta(uid)
                    ts = str(fecha)[11:19]
                    area_legible = obtener_nombre_area(area)
                    
                    if not row:
                        # Tarjeta no registrada
                        self.denegados_count += 1
                        mensaje = (
                            f"[{ts}] ACCESO DENEGADO ❌\n"
                            f" ├─ UID: {uid}\n"
                            f" ├─ Usuario: Desconocido (No Registrado)\n"
                            f" ├─ Área: {area_legible}\n"
                            f" └─ Motivo: Tarjeta no registrada en el sistema\n"
                            f"{'-'*75}\n"
                        )
                        self.escribir_log(mensaje, "red")
                    else:
                        uid_db, nombre, areas_raw, activa = row
                        if not activa:
                            # Tarjeta inactiva
                            self.denegados_count += 1
                            mensaje = (
                                f"[{ts}] ACCESO DENEGADO ❌\n"
                                f" ├─ UID: {uid}\n"
                                f" ├─ Usuario: {nombre}\n"
                                f" ├─ Área: {area_legible}\n"
                                f" └─ Motivo: Tarjeta inactiva / deshabilitada\n"
                                f"{'-'*75}\n"
                            )
                            self.escribir_log(mensaje, "red")
                        else:
                            # Tarjeta activa. Verificar areas.
                            area_id = obtener_id_por_tabla(area)
                            areas_usuario = [a.strip() for a in (areas_raw or "").split(",") if a.strip()]
                            
                            if area_id in areas_usuario:
                                # ACCESO PERMITIDO
                                self.permitidos_count += 1
                                mensaje = (
                                    f"[{ts}] ACCESO PERMITIDO ✔️\n"
                                    f" ├─ UID: {uid}\n"
                                    f" ├─ Usuario: {nombre}\n"
                                    f" └─ Área: {area_legible}\n"
                                    f"{'-'*75}\n"
                                )
                                self.escribir_log(mensaje, "green")
                            else:
                                # ACCESO DENEGADO por falta de acceso a este área específica.
                                self.denegados_count += 1
                                # Obtener nombres de los departamentos asignados
                                departamentos_asignados = [AREAS[aid] for aid in areas_usuario if aid in AREAS]
                                dept_str = ", ".join(departamentos_asignados) if departamentos_asignados else "Ninguno"
                                
                                mensaje = (
                                    f"[{ts}] ACCESO DENEGADO ❌\n"
                                    f" ├─ UID: {uid}\n"
                                    f" ├─ Usuario: {nombre}\n"
                                    f" ├─ Área: {area_legible}\n"
                                    f" ├─ Motivo: Área no autorizada para el usuario\n"
                                    f" └─ Deptos. Asignados (Sin acceso a esta área): {dept_str}\n"
                                    f"{'-'*75}\n"
                                )
                                self.escribir_log(mensaje, "red")
                                
                    self.actualizar_stats()
            except Error:
                pass
            finally:
                conn.close()
        
        if self.running:
            self.after(2000, self.consultar_logs_wifi)

    def escribir_log(self, mensaje, color="white"):
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, mensaje, color)
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def destroy(self):
        self.running = False
        super().destroy()

if __name__ == "__main__":
    app = MonitorRFID()
    app.mainloop()
