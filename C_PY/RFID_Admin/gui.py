# gui.py
# Módulo de Interfaz Gráfica (Tkinter) para Administración

import time
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import serial

# Importar configuraciones y lógica de negocio
from config import PUERTO, BAUDRATE, AREAS
import usuarios
import permisos
import puertas

class AdminGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema RFID - Panel de Administración")
        self.geometry("900x650")
        
        # Tema Oscuro Moderno ("Mamalon")
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except: pass
            
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
        frame_header = ttk.Frame(self)
        frame_header.pack(fill=tk.X, pady=15, padx=20)
        
        ttk.Label(frame_header, text="ADMINISTRACIÓN DE PERSONAL", style="Header.TLabel").pack(side=tk.LEFT)
        self.lbl_estado_serial = tk.Label(frame_header, text="USB Lector: Buscando...", fg="gray", bg="#2b2b2b", font=("Segoe UI", 10, "bold"))
        self.lbl_estado_serial.pack(side=tk.RIGHT)

        frame_botones = tk.Frame(self, bg="#2b2b2b")
        frame_botones.pack(fill=tk.X, pady=10, padx=20)
        ttk.Button(frame_botones, text="+ Registrar Nueva Tarjeta", command=self.abrir_formulario).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="✏️ Editar Selección", command=self.editar_seleccionada).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="🗑️ Eliminar", command=self.eliminar_seleccionada).pack(side=tk.LEFT, padx=5)
        
        # Botones derechos
        ttk.Button(frame_botones, text="🔄 Recargar Tabla", command=self.cargar_tabla).pack(side=tk.RIGHT, padx=5)
        ttk.Button(frame_botones, text="🚪 Administrar Puertas", command=self.abrir_puertas).pack(side=tk.RIGHT, padx=5)

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

    def conectar_serial(self):
        if self.serial_conn and self.serial_conn.is_open:
            return
        try:
            self.serial_conn = serial.Serial(PUERTO, BAUDRATE, timeout=1)
            self.lbl_estado_serial.config(text=f"🟢 USB Lector Conectado ({PUERTO})", fg="#00ff00")
            self.hilo_serial = threading.Thread(target=self.leer_serial, daemon=True)
            self.hilo_serial.start()
        except:
            self.lbl_estado_serial.config(text="🔴 USB Lector Desconectado", fg="#ff4444")
            if self.running:
                self.after(5000, self.conectar_serial)

    def leer_serial(self):
        while self.running and self.serial_conn and self.serial_conn.is_open:
            try:
                linea = self.serial_conn.readline().decode(errors="ignore").strip()
                if linea:
                    try:
                        data = json.loads(linea)
                        if isinstance(data, dict) and "uid" in data:
                            self.uid_escaneado_reciente = data["uid"].upper()
                    except: pass
            except: 
                time.sleep(1)
                break
        
        # Al salir del bucle por error o desconexión
        if self.running:
            if self.serial_conn:
                try: self.serial_conn.close()
                except: pass
                self.serial_conn = None
            self.lbl_estado_serial.config(text="🔴 USB Lector Desconectado", fg="#ff4444")
            self.after(5000, self.conectar_serial)

    def sincronizar_esp32_inmediato(self):
        """Ya no se requiere enviar nada por USB. El ESP32 se encarga de descargar vía Wi-Fi."""
        pass

    def cargar_tabla(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for t in usuarios.listar_usuarios():
            if t[4]: # Si la tarjeta está activa
                self.tree.insert("", tk.END, values=(t[0], t[1], permisos.areas_a_nombres(t[2]), str(t[3])[:16]))

    def abrir_formulario(self, uid_editar=None, nombre_editar="", areas_editar=""):
        top = tk.Toplevel(self)
        top.title("Registrar Tarjeta" if not uid_editar else "Editar Tarjeta")
        top.geometry("450x650")
        top.configure(bg="#2b2b2b")
        top.transient(self)
        top.grab_set()

        tk.Label(top, text="DATOS DEL EMPLEADO", bg="#2b2b2b", fg="#4a90e2", font=("Segoe UI", 14, "bold")).pack(pady=15)
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
        if nombre_editar: ent_nombre.insert(0, nombre_editar)

        tk.Label(top, text="Permisos de Áreas:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=30, pady=(20, 5))
        
        frame_areas = tk.Frame(top, bg="#2b2b2b")
        frame_areas.pack(fill=tk.BOTH, expand=True, padx=40)
        
        var_areas = {}
        areas_actuales = [a.strip() for a in areas_editar.split(",")] if areas_editar else []
        
        for k, v in AREAS.items():
            var = tk.BooleanVar(value=(k in areas_actuales))
            var_areas[k] = var
            tk.Checkbutton(frame_areas, text=v, variable=var, bg="#2b2b2b", fg="white", selectcolor="#3c3f41", activebackground="#2b2b2b", activeforeground="white", font=("Segoe UI", 10)).pack(anchor="w", pady=2)

        def guardar():
            uid, nombre = ent_uid.get().strip().upper(), ent_nombre.get().strip()
            areas_str = ",".join([k for k, v in var_areas.items() if v.get()])
            
            if not uid or not nombre: return messagebox.showerror("Error", "UID y Nombre son obligatorios.")
            if not areas_str: return messagebox.showerror("Error", "Debes seleccionar al menos un área.")

            if usuarios.registrar_usuario(uid, nombre, areas_str):
                messagebox.showinfo("Éxito", "Tarjeta guardada correctamente en el directorio y áreas correspondientes.")
                self.sincronizar_esp32_inmediato()
                self.cargar_tabla()
                self.uid_escaneado_reciente = None
                top.destroy()
            else: messagebox.showerror("Error", "No se pudo guardar la tarjeta.")

        ttk.Button(top, text="💾 GUARDAR TARJETA", command=guardar).pack(pady=20, ipadx=20, ipady=5)

    def editar_seleccionada(self):
        seleccion = self.tree.selection()
        if not seleccion: return messagebox.showwarning("Aviso", "Selecciona una tarjeta para editarla.")
        uid, nombre = self.tree.item(seleccion[0], "values")[0:2]
        
        row = usuarios.buscar_usuario(uid)
        if row: self.abrir_formulario(uid_editar=uid, nombre_editar=nombre, areas_editar=row[2])

    def eliminar_seleccionada(self):
        seleccion = self.tree.selection()
        if not seleccion: return messagebox.showwarning("Aviso", "Selecciona una tarjeta para eliminarla.")
        uid, nombre = self.tree.item(seleccion[0], "values")[0:2]
        
        if messagebox.askyesno("Confirmar Baja", f"¿Estás seguro de eliminar a:\n{nombre} ({uid})?\n\nSe le revocará el acceso en todas las áreas."):
            if usuarios.eliminar_usuario(uid):
                messagebox.showinfo("Éxito", "Tarjeta eliminada permanentemente.")
                self.sincronizar_esp32_inmediato()
                self.cargar_tabla()

    def destroy(self):
        self.running = False
        if self.serial_conn and self.serial_conn.is_open: 
            try: self.serial_conn.close()
            except: pass
        super().destroy()

    def abrir_puertas(self):
        top = tk.Toplevel(self)
        top.title("Administrar Puertas ESP32 (Wi-Fi)")
        top.geometry("700x500")
        top.configure(bg="#2b2b2b")
        top.transient(self)
        top.grab_set()

        tk.Label(top, text="PUERTAS ESP32 REGISTRADAS", bg="#2b2b2b", fg="#4a90e2", font=("Segoe UI", 14, "bold")).pack(pady=15)

        # Formulario de alta
        frame_form = tk.Frame(top, bg="#2b2b2b")
        frame_form.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(frame_form, text="MAC Address:", bg="#2b2b2b", fg="white").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ent_mac = tk.Entry(frame_form, width=20, font=("Segoe UI", 10), bg="#3c3f41", fg="white")
        ent_mac.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(frame_form, text="Nombre:", bg="#2b2b2b", fg="white").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        ent_nombre_puerta = tk.Entry(frame_form, width=25, font=("Segoe UI", 10), bg="#3c3f41", fg="white")
        ent_nombre_puerta.grid(row=0, column=3, sticky="w", padx=5)

        tk.Label(frame_form, text="Área:", bg="#2b2b2b", fg="white").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        areas_list = [f"{k} - {v}" for k,v in AREAS.items()]
        cb_area = ttk.Combobox(frame_form, values=areas_list, state="readonly", width=18)
        cb_area.grid(row=1, column=1, sticky="w", padx=5)
        if areas_list: cb_area.current(0)

        tk.Label(frame_form, text="Tipo:", bg="#2b2b2b", fg="white").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        cb_tipo = ttk.Combobox(frame_form, values=["Entrada", "Salida"], state="readonly", width=18)
        cb_tipo.grid(row=2, column=1, sticky="w", padx=5)
        cb_tipo.current(0)

        def guardar_puerta():
            mac = ent_mac.get().strip().upper()
            nombre = ent_nombre_puerta.get().strip()
            area_sel = cb_area.get()
            tipo_sel = cb_tipo.get()
            if not mac or not nombre or not area_sel or not tipo_sel:
                return messagebox.showerror("Error", "Todos los campos son obligatorios", parent=top)
            area_id = area_sel.split(" - ")[0]
            
            if puertas.registrar_puerta(mac, nombre, area_id, tipo_sel):
                ent_mac.delete(0, tk.END)
                ent_nombre_puerta.delete(0, tk.END)
                cargar_tabla_puertas()
            else:
                messagebox.showerror("Error", "No se pudo guardar la puerta. ¿MAC duplicada?", parent=top)

        ttk.Button(frame_form, text="Guardar / Añadir Puerta", command=guardar_puerta).grid(row=1, column=3, sticky="w", padx=5)

        # Tabla
        frame_tabla = tk.Frame(top, bg="#2b2b2b")
        frame_tabla.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        col_puertas = ("mac", "nombre", "area", "tipo")
        tree_p = ttk.Treeview(frame_tabla, columns=col_puertas, show="headings", height=8)
        tree_p.heading("mac", text="MAC ADDRESS")
        tree_p.heading("nombre", text="NOMBRE DE PUERTA")
        tree_p.heading("area", text="ÁREA ASIGNADA")
        tree_p.heading("tipo", text="TIPO")
        tree_p.column("mac", width=150, anchor="center")
        tree_p.column("nombre", width=200)
        tree_p.column("area", width=150, anchor="center")
        tree_p.column("tipo", width=100, anchor="center")
        
        scroll_p = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=tree_p.yview)
        tree_p.configure(yscroll=scroll_p.set)
        tree_p.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_p.pack(side=tk.RIGHT, fill=tk.Y)

        def cargar_tabla_puertas():
            for item in tree_p.get_children(): tree_p.delete(item)
            for p in puertas.listar_puertas():
                area_nombre = AREAS.get(p[2], p[2])
                tipo_puerta = p[3] if len(p) > 3 else "Entrada"
                tree_p.insert("", tk.END, values=(p[0], p[1], area_nombre, tipo_puerta))

        def eliminar_p():
            sel = tree_p.selection()
            if not sel: return messagebox.showwarning("Aviso", "Selecciona una puerta para eliminarla", parent=top)
            mac, nombre = tree_p.item(sel[0], "values")[0:2]
            if messagebox.askyesno("Confirmar", f"¿Eliminar la puerta '{nombre}' ({mac})?", parent=top):
                if puertas.eliminar_puerta(mac):
                    cargar_tabla_puertas()

        ttk.Button(top, text="🗑️ Eliminar Puerta", command=eliminar_p).pack(side=tk.RIGHT, padx=20, pady=10)

        def editar_p():
            sel = tree_p.selection()
            if not sel: return messagebox.showwarning("Aviso", "Selecciona una puerta para editarla", parent=top)
            values = tree_p.item(sel[0], "values")
            mac, nombre, area_nombre = values[0:3]
            tipo_puerta = values[3] if len(values) > 3 else "Entrada"
            
            ent_mac.delete(0, tk.END)
            ent_mac.insert(0, mac)
            
            ent_nombre_puerta.delete(0, tk.END)
            ent_nombre_puerta.insert(0, nombre)
            
            for i, val in enumerate(areas_list):
                if area_nombre in val:
                    cb_area.current(i)
                    break
            
            if tipo_puerta == "Salida":
                cb_tipo.current(1)
            else:
                cb_tipo.current(0)

        ttk.Button(top, text="✏️ Editar Selección", command=editar_p).pack(side=tk.RIGHT, padx=5, pady=10)
        
        cargar_tabla_puertas()
