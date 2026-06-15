# ============================================================
# Sistema de Control RFID — Administración y Registro
# ============================================================

import time
import json
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import mysql.connector
from mysql.connector import Error

# ── Configuracion Serial ─────────────────────────────────────
PUERTO   = "COM5"
BAUDRATE = 115200

# ── Configuracion MySQL (XAMPP) ──────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",
    "database": "rfid_db"
}

# ── Areas disponibles ────────────────────────────────────────
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

# ============================================================
# LOGICA DE BASE DE DATOS
# ============================================================

def conectar_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"Error DB: {e}")
        return None

def db_registrar_tarjeta(uid: str, nombre: str, areas: str) -> bool:
    conn = conectar_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tarjetas (uid, nombre, areas)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE nombre=%s, areas=%s, activa=1
        """, (uid, nombre, areas, nombre, areas))
        
        for tabla in AREAS_TABLAS.values():
            try:
                cur.execute(f"DELETE FROM {tabla} WHERE uid=%s", (uid,))
            except Error:
                pass
                
        areas_lista = [a.strip() for a in areas.split(",") if a.strip()]
        for area_id in areas_lista:
            tabla = AREAS_TABLAS.get(area_id)
            if tabla:
                try:
                    cur.execute(f"""
                        INSERT INTO {tabla} (uid, nombre, activa) 
                        VALUES (%s, %s, 1)
                        ON DUPLICATE KEY UPDATE nombre=%s, activa=1
                    """, (uid, nombre, nombre))
                except Error as e:
                    pass

        conn.commit()
        return True
    except Error as e:
        return False
    finally:
        conn.close()

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

def db_listar_tarjetas() -> list:
    conn = conectar_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT uid, nombre, areas, fecha_registro, activa FROM tarjetas ORDER BY nombre")
        return cur.fetchall()
    except Error:
        return []
    finally:
        conn.close()

def db_eliminar_tarjeta(uid: str) -> bool:
    conn = conectar_db()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM tarjetas WHERE uid=%s", (uid,))
        for tabla in AREAS_TABLAS.values():
            try:
                cur.execute(f"DELETE FROM {tabla} WHERE uid=%s", (uid,))
            except Error:
                pass
        conn.commit()
        return True
    except Error:
        return False
    finally:
        conn.close()

def db_obtener_uids_activos() -> list:
    conn = conectar_db()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT uid FROM tarjetas WHERE activa=1")
        return [row[0] for row in cur.fetchall()]
    except Error:
        return []
    finally:
        conn.close()

def areas_a_nombres(areas_raw: str) -> str:
    partes = [a.strip() for a in areas_raw.split(",") if a.strip()]
    return ", ".join(AREAS.get(p, p) for p in partes)


# ============================================================
# INTERFAZ DE REGISTRO
# ============================================================

class RegistroRFID(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema RFID - Panel de Administración")
        self.geometry("900x650")
        
        # Aplicar estilo moderno "mamalon"
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except:
            pass
            
        style.configure("TFrame", background="#2b2b2b")
        style.configure("TLabel", background="#2b2b2b", foreground="#ffffff", font=("Segoe UI", 11))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#4a90e2")
        style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#4a90e2", foreground="white", padding=6)
        style.map("TButton", background=[("active", "#357abd")])
        
        style.configure("Treeview", background="#3c3f41", foreground="white", rowheight=30, fieldbackground="#3c3f41", borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#1e1e1e", foreground="white")
        style.map("Treeview", background=[("selected", "#4a90e2")])

        self.configure(bg="#2b2b2b")
        
        self.running = True
        self.serial_conn = None
        self.uid_escaneado_reciente = None
        
        self.crear_interfaz()
        self.conectar_serial()
        self.cargar_tabla()

    def crear_interfaz(self):
        # Header
        frame_header = ttk.Frame(self)
        frame_header.pack(fill=tk.X, pady=15, padx=20)
        
        lbl_titulo = ttk.Label(frame_header, text="ADMINISTRACIÓN DE PERSONAL", style="Header.TLabel")
        lbl_titulo.pack(side=tk.LEFT)
        
        self.lbl_estado_serial = tk.Label(frame_header, text="USB Lector: Buscando...", fg="gray", bg="#2b2b2b", font=("Segoe UI", 10, "bold"))
        self.lbl_estado_serial.pack(side=tk.RIGHT)

        # Botones de Acción
        frame_botones = tk.Frame(self, bg="#2b2b2b")
        frame_botones.pack(fill=tk.X, pady=10, padx=20)

        ttk.Button(frame_botones, text="+ Registrar Nueva Tarjeta", command=self.abrir_formulario).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="✏️ Editar Selección", command=self.editar_seleccionada).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="🗑️ Eliminar", command=self.eliminar_seleccionada).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="🔄 Recargar Tabla", command=self.cargar_tabla).pack(side=tk.RIGHT, padx=5)

        # Tabla
        frame_tabla = tk.Frame(self, bg="#2b2b2b")
        frame_tabla.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        columnas = ("uid", "nombre", "areas", "fecha")
        self.tree = ttk.Treeview(frame_tabla, columns=columnas, show="headings")
        self.tree.heading("uid", text="UID TARJETA")
        self.tree.heading("nombre", text="NOMBRE EMPLEADO")
        self.tree.heading("areas", text="ÁREAS AUTORIZADAS")
        self.tree.heading("fecha", text="FECHA DE REGISTRO")
        
        self.tree.column("uid", width=120, anchor="center")
        self.tree.column("nombre", width=250)
        self.tree.column("areas", width=350)
        self.tree.column("fecha", width=150, anchor="center")

        scrollbar = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # ============================================================
    # LECTOR SERIAL (PARA AUTOFILLED DE NUEVAS TARJETAS)
    # ============================================================

    def conectar_serial(self):
        try:
            self.serial_conn = serial.Serial(PUERTO, BAUDRATE, timeout=1)
            self.lbl_estado_serial.config(text=f"🟢 USB Lector Conectado ({PUERTO})", fg="#00ff00")
            self.hilo_serial = threading.Thread(target=self.leer_serial, daemon=True)
            self.hilo_serial.start()
        except serial.SerialException:
            self.lbl_estado_serial.config(text="🔴 USB Lector Desconectado", fg="#ff4444")

    def leer_serial(self):
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                linea = self.serial_conn.readline().decode(errors="ignore").strip()
                if linea:
                    try:
                        data = json.loads(linea)
                        if isinstance(data, dict) and "uid" in data:
                            self.uid_escaneado_reciente = data["uid"].upper()
                    except json.JSONDecodeError:
                        pass
            except serial.SerialException:
                time.sleep(1)

    def sincronizar_esp32_inmediato(self):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                uids = db_obtener_uids_activos()
                payload = json.dumps(uids, separators=(',', ':')) + "\n"
                self.serial_conn.write(payload.encode())
            except:
                pass

    # ============================================================
    # CRUD
    # ============================================================

    def cargar_tabla(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        tarjetas = db_listar_tarjetas()
        for t in tarjetas:
            if t[4]: # activa
                uid = t[0]
                nombre = t[1]
                areas = areas_a_nombres(t[2])
                fecha = str(t[3])[:16]
                self.tree.insert("", tk.END, values=(uid, nombre, areas, fecha))

    def abrir_formulario(self, uid_editar=None, nombre_editar="", areas_editar=""):
        top = tk.Toplevel(self)
        top.title("Registrar Tarjeta" if not uid_editar else "Editar Tarjeta")
        top.geometry("450x650")
        top.configure(bg="#2b2b2b")
        top.transient(self)
        top.grab_set()

        lbl_inst = tk.Label(top, text="DATOS DEL EMPLEADO", bg="#2b2b2b", fg="#4a90e2", font=("Segoe UI", 14, "bold"))
        lbl_inst.pack(pady=15)

        tk.Label(top, text="UID de la tarjeta:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).pack(anchor="w", padx=30)
        
        frame_uid = tk.Frame(top, bg="#2b2b2b")
        frame_uid.pack(fill=tk.X, padx=30, pady=5)
        
        ent_uid = tk.Entry(frame_uid, font=("Segoe UI", 12), bg="#3c3f41", fg="white", insertbackground="white", relief=tk.FLAT)
        ent_uid.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        
        if uid_editar:
            ent_uid.insert(0, uid_editar)
            ent_uid.config(state="readonly")
        
        def autocompletar_uid():
            if self.uid_escaneado_reciente:
                ent_uid.delete(0, tk.END)
                ent_uid.insert(0, self.uid_escaneado_reciente)
            top.after(500, autocompletar_uid)
            
        if not uid_editar:
            top.after(500, autocompletar_uid)
            tk.Label(top, text="💡 Pasa la tarjeta por el lector USB para auto-completar", bg="#2b2b2b", fg="#aaaaaa", font=("Segoe UI", 8)).pack(anchor="w", padx=30)

        tk.Label(top, text="Nombre del Empleado:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).pack(anchor="w", padx=30, pady=(15,0))
        ent_nombre = tk.Entry(top, font=("Segoe UI", 12), bg="#3c3f41", fg="white", insertbackground="white", relief=tk.FLAT)
        ent_nombre.pack(fill=tk.X, padx=30, pady=5, ipady=5)
        if nombre_editar:
            ent_nombre.insert(0, nombre_editar)

        tk.Label(top, text="Permisos de Áreas:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=30, pady=(20, 5))
        
        frame_areas = tk.Frame(top, bg="#2b2b2b")
        frame_areas.pack(fill=tk.BOTH, expand=True, padx=40)
        
        var_areas = {}
        areas_actuales = [a.strip() for a in areas_editar.split(",")] if areas_editar else []
        
        for k, v in AREAS.items():
            var = tk.BooleanVar(value=(k in areas_actuales))
            var_areas[k] = var
            chk = tk.Checkbutton(frame_areas, text=v, variable=var, bg="#2b2b2b", fg="white", selectcolor="#3c3f41", activebackground="#2b2b2b", activeforeground="white", font=("Segoe UI", 10))
            chk.pack(anchor="w", pady=2)

        def guardar():
            uid = ent_uid.get().strip().upper()
            nombre = ent_nombre.get().strip()
            areas_seleccionadas = [k for k, v in var_areas.items() if v.get()]
            areas_str = ",".join(areas_seleccionadas)

            if not uid or not nombre:
                messagebox.showerror("Error", "UID y Nombre son obligatorios.")
                return
            if not areas_str:
                messagebox.showerror("Error", "Debes seleccionar al menos un área.")
                return

            if db_registrar_tarjeta(uid, nombre, areas_str):
                messagebox.showinfo("Éxito", "Tarjeta guardada correctamente en la base de datos.")
                self.sincronizar_esp32_inmediato()
                self.cargar_tabla()
                self.uid_escaneado_reciente = None
                top.destroy()
            else:
                messagebox.showerror("Error", "No se pudo guardar la tarjeta.")

        ttk.Button(top, text="💾 GUARDAR TARJETA", command=guardar).pack(pady=20, ipadx=20, ipady=5)

    def editar_seleccionada(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona una tarjeta para editarla.")
            return
        valores = self.tree.item(seleccion[0], "values")
        uid = valores[0]
        nombre = valores[1]
        row = db_buscar_tarjeta(uid)
        if row:
            self.abrir_formulario(uid_editar=uid, nombre_editar=nombre, areas_editar=row[2])

    def eliminar_seleccionada(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona una tarjeta para eliminarla.")
            return
        valores = self.tree.item(seleccion[0], "values")
        uid, nombre = valores[0], valores[1]

        if messagebox.askyesno("Confirmar Baja", f"¿Eliminar permanentemente los accesos de:\n\n{nombre} (UID: {uid})?"):
            if db_eliminar_tarjeta(uid):
                messagebox.showinfo("Éxito", "Tarjeta eliminada del sistema.")
                self.sincronizar_esp32_inmediato()
                self.cargar_tabla()

    def destroy(self):
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        super().destroy()

if __name__ == "__main__":
    app = RegistroRFID()
    app.mainloop()
