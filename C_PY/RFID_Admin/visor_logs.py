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
        self.configure(bg="#FFFFFF")
        
        self.running = True
        self.last_log_id = 0 
        self.permitidos_count = 0
        self.denegados_count = 0
        
        self.tree_widgets = {}  # Diccionario para guardar los Treeview de cada pestaña
        
        self.crear_interfaz()
        
        # Iniciar el monitoreo de la BD
        self.after(1000, self.consultar_logs_wifi)

    def crear_interfaz(self):
        # Header Container
        header_frame = tk.Frame(self, bg="#FFFFFF", height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        lbl_titulo = tk.Label(
            header_frame, 
            text="📡 SISTEMA RFID — MONITOR DE ACCESOS EN VIVO", 
            font=("Segoe UI", 12, "bold"), 
            bg="#FFFFFF", 
            fg="#033966"
        )
        lbl_titulo.pack(side=tk.LEFT, padx=20, pady=15)

        # Status indicator
        self.lbl_status_indicator = tk.Label(
            header_frame,
            text="● ESP32 ONLINE",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#0A8504"
        )
        self.lbl_status_indicator.pack(side=tk.RIGHT, padx=20, pady=15)

        # Main container with Notebook
        main_frame = tk.Frame(self, bg="#FFFFFF")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Estilos oscuros para las pestañas
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background="#09090B", borderwidth=0)
        style.configure('TNotebook.Tab', background="#18181B", foreground="#A1A1AA", padding=[15, 8], font=("Segoe UI", 10))
        style.map('TNotebook.Tab', 
                  background=[('selected', '#033966')], 
                  foreground=[('selected', '#ffffff')])
                  
        # Estilos para Treeview
        style.configure('Treeview', font=("Segoe UI", 10), rowheight=25)
        style.configure('Treeview.Heading', font=("Segoe UI", 10, "bold"))

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Crear la pestaña "General"
        self.crear_pestana("General (Todas las puertas)")
        
        # Crear una pestaña por cada área configurada
        for area_id, area_nombre in AREAS.items():
            self.crear_pestana(area_nombre)

        # Stats footer
        footer_frame = tk.Frame(self, bg="#FFFFFF", height=40)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)

        self.lbl_stats = tk.Label(
            footer_frame,
            text="Resumen Global:  Permitidos: 0  |  Denegados: 0",
            font=("Segoe UI", 9, "bold"),
            bg="#FFFFFF",
            fg="#404040"
        )
        self.lbl_stats.pack(side=tk.LEFT, padx=20, pady=10)

        self.escribir_log({
            "uid": "-", "nombre": "Sistema", "area": "-", "motivo": "Iniciando conexión con base de datos...", "entrada": "-", "salida": "-"
        }, "gray", "General (Todas las puertas)")
        self.escribir_log({
            "uid": "-", "nombre": "Sistema", "area": "-", "motivo": "Esperando registros Wi-Fi...", "entrada": "-", "salida": "-"
        }, "gray", "General (Todas las puertas)")

    def crear_pestana(self, nombre_pestana):
        frame = tk.Frame(self.notebook, bg="#FFFFFF")
        self.notebook.add(frame, text=nombre_pestana)
        
        columns = ("uid", "nombre", "area", "motivo", "entrada", "salida")
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="none")
        
        tree.heading("uid", text="UID")
        tree.heading("nombre", text="Nombre")
        tree.heading("area", text="Área")
        tree.heading("motivo", text="Motivo")
        tree.heading("entrada", text="Entrada")
        tree.heading("salida", text="Salida")
        
        tree.column("uid", width=100, anchor=tk.CENTER)
        tree.column("nombre", width=150, anchor=tk.CENTER)
        tree.column("area", width=120, anchor=tk.CENTER)
        tree.column("motivo", width=250, anchor=tk.CENTER)
        tree.column("entrada", width=100, anchor=tk.CENTER)
        tree.column("salida", width=100, anchor=tk.CENTER)
        
        tree.tag_configure("red", foreground="#9C0303")
        tree.tag_configure("green", foreground="#0A8504")
        tree.tag_configure("gray", foreground="#808080")
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        self.tree_widgets[nombre_pestana] = tree

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
                    
                    entrada_val = ts if tipo == "Entrada" else "-"
                    salida_val = ts if tipo == "Salida" else "-"
                    
                    if not row:
                        self.denegados_count += 1
                        data = {
                            "uid": uid, "nombre": "Desconocido", "area": area_legible,
                            "motivo": "Tarjeta no registrada", "entrada": entrada_val, "salida": salida_val
                        }
                        self.escribir_log(data, "red", area_legible)
                    else:
                        uid_db, nombre, areas_raw, activa = row
                        if not activa:
                            self.denegados_count += 1
                            data = {
                                "uid": uid, "nombre": nombre, "area": area_legible,
                                "motivo": "Tarjeta inactiva / deshabilitada", "entrada": entrada_val, "salida": salida_val
                            }
                            self.escribir_log(data, "red", area_legible)
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
                                data = {
                                    "uid": uid, "nombre": nombre, "area": area_legible,
                                    "motivo": "Usuario sin permisos para esta área", "entrada": entrada_val, "salida": salida_val
                                }
                                self.escribir_log(data, "red", area_legible)
                            else:
                                self.permitidos_count += 1
                                data = {
                                    "uid": uid, "nombre": nombre, "area": area_legible,
                                    "motivo": "-", "entrada": entrada_val, "salida": salida_val
                                }
                                self.escribir_log(data, "green", area_legible)
                            
                    self.actualizar_stats()
            except Error:
                pass
            finally:
                conn.close()
        
        if self.running:
            self.after(2000, self.consultar_logs_wifi)

    def escribir_log(self, data, color="black", area_legible=""):
        def escribir(tree_widget):
            if tree_widget:
                tree_widget.insert("", tk.END, values=(
                    data.get("uid", "-"),
                    data.get("nombre", "-"),
                    data.get("area", "-"),
                    data.get("motivo", "-"),
                    data.get("entrada", "-"),
                    data.get("salida", "-")
                ), tags=(color,))
                children = tree_widget.get_children()
                if children:
                    tree_widget.see(children[-1])

        # Siempre escribimos en la pestaña General
        tree_gen = self.tree_widgets.get("General (Todas las puertas)")
        if tree_gen:
            escribir(tree_gen)
            
        # Escribimos también en la pestaña específica del área (si existe)
        if area_legible and area_legible != "General (Todas las puertas)":
            tree_area = self.tree_widgets.get(area_legible)
            if tree_area:
                escribir(tree_area)

    def destroy(self):
        self.running = False
        super().destroy()

if __name__ == "__main__":
    app = MonitorRFID()
    app.mainloop()
