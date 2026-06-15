import tkinter as tk
from tkinter import ttk
import mysql.connector
from mysql.connector import Error

from config import DB_CONFIG, AREAS
import usuarios

def conectar_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        return None

def obtener_nombre_area(area_tabla: str) -> str:
    """Retorna el nombre legible exacto del área para que coincida con las pestañas."""
    if not area_tabla:
        return "Desconocido"
        
    # Buscar coincidencia ignorando mayúsculas y guiones bajos
    for val in AREAS.values():
        if area_tabla.lower().replace("_", " ") == val.lower().replace("_", " "):
            return val
            
    return area_tabla.replace("_", " ").title()

class MonitorRFID(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Monitor de Accesos Wi-Fi - RFID (Múltiples Puertas)")
        self.geometry("850x600")
        self.configure(bg="#09090B")
        
        self.running = True
        self.last_log_id = 0 
        self.permitidos_count = 0
        self.denegados_count = 0
        
        self.text_widgets = {}  # Diccionario para guardar los Text widgets de cada pestaña
        
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

        # Main container with Notebook
        main_frame = tk.Frame(self, bg="#09090B")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Estilos oscuros para las pestañas
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background="#09090B", borderwidth=0)
        style.configure('TNotebook.Tab', background="#18181B", foreground="#A1A1AA", padding=[15, 8], font=("Segoe UI", 10))
        style.map('TNotebook.Tab', 
                  background=[('selected', '#3f3f46')], 
                  foreground=[('selected', '#ffffff')])

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Crear la pestaña "General"
        self.crear_pestana("General (Todas las puertas)")
        
        # Crear una pestaña por cada área configurada
        for area_id, area_nombre in AREAS.items():
            self.crear_pestana(area_nombre)

        # Stats footer
        footer_frame = tk.Frame(self, bg="#18181B", height=40)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)

        self.lbl_stats = tk.Label(
            footer_frame,
            text="Resumen Global:  Permitidos: 0  |  Denegados: 0",
            font=("Segoe UI", 9, "bold"),
            bg="#18181B",
            fg="#A1A1AA"
        )
        self.lbl_stats.pack(side=tk.LEFT, padx=20, pady=10)

        self.escribir_log("Iniciando conexión con base de datos...\n", "gray", "General (Todas las puertas)")
        self.escribir_log("Esperando registros Wi-Fi de las puertas ESP32...\n", "gray", "General (Todas las puertas)")
        self.escribir_log("-" * 75 + "\n", "gray", "General (Todas las puertas)")

    def crear_pestana(self, nombre_pestana):
        frame = tk.Frame(self.notebook, bg="#18181B")
        self.notebook.add(frame, text=nombre_pestana)
        
        pane = tk.PanedWindow(frame, orient=tk.HORIZONTAL, bg="#18181B", sashwidth=4, sashpad=2)
        pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        frame_in = tk.Frame(pane, bg="#18181B")
        frame_out = tk.Frame(pane, bg="#18181B")
        pane.add(frame_in)
        pane.add(frame_out)
        
        lbl_in = tk.Label(frame_in, text="ENTRADAS", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#10B981")
        lbl_in.pack(anchor="w", padx=5, pady=5)
        
        lbl_out = tk.Label(frame_out, text="SALIDAS", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#0EA5E9")
        lbl_out.pack(anchor="w", padx=5, pady=5)
        
        def setup_text(parent):
            t = tk.Text(parent, state=tk.DISABLED, bg="#18181B", fg="#E4E4E7", font=("Consolas", 10), relief=tk.FLAT, padx=10, pady=10, insertbackground="white")
            t.pack(fill=tk.BOTH, expand=True)
            t.tag_config("red", foreground="#EF4444")
            t.tag_config("green", foreground="#10B981")
            t.tag_config("gray", foreground="#71717A")
            t.tag_config("white", foreground="#E4E4E7")
            return t
            
        txt_in = setup_text(frame_in)
        txt_out = setup_text(frame_out)
        
        self.text_widgets[nombre_pestana] = {"Entrada": txt_in, "Salida": txt_out}

    def actualizar_stats(self):
        self.lbl_stats.config(
            text=f"Resumen Global:  Permitidos: {self.permitidos_count}  |  Denegados: {self.denegados_count}"
        )

    def consultar_logs_wifi(self):
        conn = conectar_db()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT id, uid, area, fecha, tipo FROM registros_acceso WHERE id > %s ORDER BY id ASC", (self.last_log_id,))
                nuevos_logs = cur.fetchall()
                for log in nuevos_logs:
                    log_id, uid, area, fecha, tipo = log
                    self.last_log_id = log_id
                    
                    if not tipo:
                        tipo = "Entrada"
                    
                    row = usuarios.buscar_usuario(uid)
                    ts = str(fecha)[11:19]
                    area_legible = obtener_nombre_area(area)
                    
                    if not row:
                        self.denegados_count += 1
                        mensaje = (
                            f"[{ts}] ACCESO DENEGADO ❌\n"
                            f" ├─ UID: {uid}\n"
                            f" ├─ Usuario: Desconocido (No Registrado)\n"
                            f" ├─ Puerta: {area_legible}\n"
                            f" └─ Motivo: Tarjeta no registrada en el sistema\n"
                            f"{'-'*75}\n"
                        )
                        self.escribir_log(mensaje, "red", area_legible, tipo)
                    else:
                        uid_db, nombre, areas_raw, activa = row
                        if not activa:
                            self.denegados_count += 1
                            mensaje = (
                                f"[{ts}] ACCESO DENEGADO ❌\n"
                                f" ├─ UID: {uid}\n"
                                f" ├─ Usuario: {nombre}\n"
                                f" ├─ Puerta: {area_legible}\n"
                                f" └─ Motivo: Tarjeta inactiva / deshabilitada\n"
                                f"{'-'*75}\n"
                            )
                            self.escribir_log(mensaje, "red", area_legible, tipo)
                        else:
                            # Extraer ID del área a partir de su nombre legible
                            area_id = None
                            for k, v in AREAS.items():
                                if v == area_legible:
                                    area_id = str(k)
                                    break
                                    
                            lista_permisos = areas_raw.split(",") if areas_raw else []
                            
                            if area_id and area_id not in lista_permisos:
                                self.denegados_count += 1
                                mensaje = (
                                    f"[{ts}] ACCESO DENEGADO ❌\n"
                                    f" ├─ UID: {uid}\n"
                                    f" ├─ Usuario: {nombre}\n"
                                    f" ├─ Puerta: {area_legible}\n"
                                    f" └─ Motivo: Usuario sin permisos para esta área\n"
                                    f"{'-'*75}\n"
                                )
                                self.escribir_log(mensaje, "red", area_legible, tipo)
                            else:
                                self.permitidos_count += 1
                                mensaje = (
                                    f"[{ts}] ACCESO PERMITIDO ✔️\n"
                                    f" ├─ UID: {uid}\n"
                                    f" ├─ Usuario: {nombre}\n"
                                    f" └─ Puerta: {area_legible}\n"
                                    f"{'-'*75}\n"
                                )
                                self.escribir_log(mensaje, "green", area_legible, tipo)
                            
                    self.actualizar_stats()
            except Error:
                pass
            finally:
                conn.close()
        
        if self.running:
            self.after(2000, self.consultar_logs_wifi)

    def escribir_log(self, mensaje, color="white", area_legible="", tipo="Entrada"):
        def escribir(txt_widget):
            if txt_widget:
                txt_widget.config(state=tk.NORMAL)
                txt_widget.insert(tk.END, mensaje, color)
                txt_widget.see(tk.END)
                txt_widget.config(state=tk.DISABLED)

        # Siempre escribimos en la pestaña General
        dict_gen = self.text_widgets.get("General (Todas las puertas)")
        if dict_gen:
            escribir(dict_gen.get(tipo))
            
        # Escribimos también en la pestaña específica del área (si existe)
        dict_area = self.text_widgets.get(area_legible)
        if dict_area:
            escribir(dict_area.get(tipo))

    def destroy(self):
        self.running = False
        super().destroy()

if __name__ == "__main__":
    app = MonitorRFID()
    app.mainloop()
