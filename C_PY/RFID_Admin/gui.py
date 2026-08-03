# gui.py
# Módulo de Interfaz Gráfica (Tkinter) para Administración

import time
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import os
from PIL import Image, ImageTk
import auth

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.widget.bind("<Enter>", self.enter, add="+")
        self.widget.bind("<Leave>", self.leave, add="+")

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(400, self.showtip)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def showtip(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Poppins", "9", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

# Importar configuraciones y lógica de negocio
from config import PUERTO, BAUDRATE, AREAS
import usuarios
import permisos
import puertas

class AdminGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Grupo Industrial Saavedra")
        self.geometry("950x700")
        
        try:
            import os
            import ctypes
            myappid = 'csproject.rfid_admin.gui.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Imagenes", "G.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            print("Error cargando ícono de ventana:", e)
        
        # Tema Moderno Dashboard
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except: pass
            
        style.configure("TFrame", background="#F4F6F9")
        style.configure("Sidebar.TFrame", background="#2B2D30")
        style.configure("TLabel", background="#F4F6F9", foreground="#333333", font=("Segoe UI", 10))
        style.configure("Sidebar.TLabel", background="#2B2D30", foreground="#A1A1AA", font=("Segoe UI", 10, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1A1A1A", background="#F4F6F9")
        
        style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#007BFF", foreground="#FFFFFF", padding=8, borderwidth=0)
        style.map("TButton", background=[("active", "#0056b3")])
        
        style.configure("Menu.TButton", font=("Segoe UI", 10, "bold"), background="#2B2D30", foreground="#FFFFFF", borderwidth=0, anchor="w", padding=(20, 10))
        style.map("Menu.TButton", background=[("active", "#007BFF")])
        
        style.configure("SubMenu.TButton", font=("Segoe UI", 9), background="#1E1F22", foreground="#A1A1AA", borderwidth=0, anchor="w", padding=(40, 5))
        style.map("SubMenu.TButton", background=[("active", "#007BFF")], foreground=[("active", "#FFFFFF")])
        
        style.configure("Treeview", background="#FFFFFF", foreground="#333333", rowheight=35, fieldbackground="#FFFFFF", borderwidth=0, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#FFFFFF", foreground="#6c757d", relief="flat")
        style.map("Treeview", background=[("selected", "#E8F0FE")], foreground=[("selected", "#007BFF")])

        self.configure(bg="#F4F6F9")
        self.running = True
        self.serial_conn = None
        self.uid_escaneado_reciente = None
        self.menu_visible = True
        self.submenu_usuarios_visible = False
        self.submenu_puertas_visible = False
        self.submenu_visor_visible = False
        self.rol_actual = None
        self.usuario_actual = None
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.img_paths = {
            "accept": os.path.join(base_dir, "Imagenes", "Agregar.png"),
            "alarm": os.path.join(base_dir, "Imagenes", "DELET.png"),
            "hourglass": os.path.join(base_dir, "Imagenes", "Recarga de tablas.png"),
            "save": os.path.join(base_dir, "Imagenes", "Guardar información de tarjetas-puertas.png"),
            "write": os.path.join(base_dir, "Imagenes", "editar-informacion.png"),
            "menu": os.path.join(base_dir, "Imagenes", "Menú.png"),
            "fondo_inicio": os.path.join(base_dir, "Imagenes", "Fondo de inicio.jpg"),
            "fondo_usuarios": os.path.join(base_dir, "Imagenes", "Fondo de usuarios.png"),
            "logo": os.path.join(base_dir, "Imagenes", "Logo.png"),
            "buscar": os.path.join(base_dir, "Imagenes", "Buscar.png"),
            "activar": os.path.join(base_dir, "Imagenes", "Activar.png"),
            "eliminar": os.path.join(base_dir, "Imagenes", "Eliminar.png")
        }
        self.iconos = {}
        
        self.crear_interfaz_principal()
        self.conectar_serial()
        self.mantener_frame_acciones()
        self.loop_actualizar_puertas()

    def cargar_icono(self, name, size=24):
        key = f"{name}_{size}x{size}"
        if key not in self.iconos:
            try:
                path = self.img_paths.get(name)
                if path and os.path.exists(path):
                    img = Image.open(path)
                    img = img.resize((size, size), Image.Resampling.LANCZOS)
                    self.iconos[key] = ImageTk.PhotoImage(img)
                else:
                    self.iconos[key] = ""
            except Exception as e:
                print(f"Error cargando {name}: {e}")
                self.iconos[key] = ""
        return self.iconos[key]

    def auto_ajustar_columnas(self, tree):
        from tkinter import font as tkfont
        font = tkfont.Font(family="Poppins", size=10)
        for col in tree["columns"]:
            if col == "acciones":
                tree.column(col, width=130, anchor="center")
                continue
                
            col_title = tree.heading(col, "text")
            max_width = font.measure(col_title) + 30
            
            for item in tree.get_children(""):
                val = tree.set(item, col)
                w = font.measure(str(val)) + 30
                if w > max_width: max_width = w
                
            max_width = max(max_width, 100)
            max_width = min(max_width, 600)
            tree.column(col, width=max_width)

    def mantener_frame_acciones(self):
        if getattr(self, 'animating_menu', False):
            if getattr(self, 'running', False):
                self.after(50, self.mantener_frame_acciones)
            return

        # 1. Limpieza si los widgets fueron destruidos al cambiar de vista
        if hasattr(self, 'pool_frames_u') and self.pool_frames_u and not self.pool_frames_u[0].winfo_exists():
            delattr(self, 'pool_frames_u')
        if hasattr(self, 'pool_frames_p') and self.pool_frames_p and not self.pool_frames_p[0].winfo_exists():
            delattr(self, 'pool_frames_p')

        # 2. Creación del pool si no existe
        if not hasattr(self, 'pool_frames_u') and hasattr(self, 'tree_usuarios') and self.tree_usuarios.winfo_exists():
            self.pool_frames_u = []
            for i in range(35):
                f = tk.Frame(self.tree_usuarios, bg="#FFFFFF")
                btn_edit = tk.Button(f, image=self.cargar_icono("write", 30), bg="#FFFFFF", bd=0, activebackground="#F0F0F0", cursor="hand2", relief=tk.FLAT, highlightthickness=0)
                btn_edit.pack(side=tk.LEFT, expand=True, pady=2)
                ToolTip(btn_edit, "Editar Usuario")
                
                btn_del = tk.Button(f, image=self.cargar_icono("alarm", 30), bg="#FFFFFF", bd=0, activebackground="#F0F0F0", cursor="hand2", relief=tk.FLAT, highlightthickness=0)
                btn_del.pack(side=tk.LEFT, expand=True, pady=2)
                
                def action_edit_u(fr=f):
                    if hasattr(fr, 'item_id'):
                        self.tree_usuarios.selection_set(fr.item_id)
                        self.editar_usuario_seleccionado()
                def action_del_u(fr=f):
                    if hasattr(fr, 'item_id'):
                        self.tree_usuarios.selection_set(fr.item_id)
                        self.eliminar_usuario_seleccionado()

                btn_edit.config(command=action_edit_u)
                btn_del.config(command=action_del_u)
                self.pool_frames_u.append(f)
                
        if not hasattr(self, 'pool_frames_p') and hasattr(self, 'tree_puertas') and self.tree_puertas.winfo_exists():
            self.pool_frames_p = []
            for i in range(35):
                f = tk.Frame(self.tree_puertas, bg="#FFFFFF")
                btn_edit = tk.Button(f, image=self.cargar_icono("write", 30), bg="#FFFFFF", bd=0, activebackground="#F0F0F0", cursor="hand2", relief=tk.FLAT, highlightthickness=0)
                btn_edit.pack(side=tk.LEFT, expand=True, pady=2)
                ToolTip(btn_edit, "Editar Puerta")
                
                btn_del = tk.Button(f, image=self.cargar_icono("alarm", 30), bg="#FFFFFF", bd=0, activebackground="#F0F0F0", cursor="hand2", relief=tk.FLAT, highlightthickness=0)
                btn_del.pack(side=tk.LEFT, expand=True, pady=2)
                
                def action_edit_p(fr=f):
                    if hasattr(fr, 'item_id'):
                        self.tree_puertas.selection_set(fr.item_id)
                        self.editar_puerta_seleccionada()
                def action_del_p(fr=f):
                    if hasattr(fr, 'item_id'):
                        self.tree_puertas.selection_set(fr.item_id)
                        self.eliminar_puerta_seleccionada()

                btn_edit.config(command=action_edit_p)
                btn_del.config(command=action_del_p)
                self.pool_frames_p.append(f)

        # Check hover globally
        hovered_item_u = None
        hovered_item_p = None
        
        try:
            x_root, y_root = self.winfo_pointerxy()
            if self.vista_actual == "usuarios" and hasattr(self, 'tree_usuarios') and self.tree_usuarios.winfo_exists():
                x = x_root - self.tree_usuarios.winfo_rootx()
                y = y_root - self.tree_usuarios.winfo_rooty()
                if 0 <= x <= self.tree_usuarios.winfo_width() and 0 <= y <= self.tree_usuarios.winfo_height():
                    hovered_item_u = self.tree_usuarios.identify_row(y)
                    
                last_u = getattr(self.tree_usuarios, 'last_hovered', None)
                if last_u and last_u != hovered_item_u:
                    try: self.tree_usuarios.item(last_u, tags=())
                    except: pass
                if hovered_item_u:
                    self.tree_usuarios.item(hovered_item_u, tags=("hover",))
                self.tree_usuarios.last_hovered = hovered_item_u
                
            if self.vista_actual == "puertas" and hasattr(self, 'tree_puertas') and self.tree_puertas.winfo_exists():
                x = x_root - self.tree_puertas.winfo_rootx()
                y = y_root - self.tree_puertas.winfo_rooty()
                if 0 <= x <= self.tree_puertas.winfo_width() and 0 <= y <= self.tree_puertas.winfo_height():
                    hovered_item_p = self.tree_puertas.identify_row(y)
                    
                last_p = getattr(self.tree_puertas, 'last_hovered', None)
                if last_p and last_p != hovered_item_p:
                    try: self.tree_puertas.item(last_p, tags=())
                    except: pass
                if hovered_item_p:
                    self.tree_puertas.item(hovered_item_p, tags=("hover",))
                self.tree_puertas.last_hovered = hovered_item_p
        except Exception:
            pass

        # 3 y 4. Actualizar posiciones y ocultar solo los frames no utilizados
        try:
            used_u = 0
            if self.vista_actual == "usuarios" and hasattr(self, 'tree_usuarios') and hasattr(self, 'pool_frames_u') and self.tree_usuarios.winfo_exists():
                for item in self.tree_usuarios.get_children():
                    bbox = self.tree_usuarios.bbox(item, "acciones")
                    if bbox and used_u < len(self.pool_frames_u):
                        x, y, w, h = bbox
                        f = self.pool_frames_u[used_u]
                        if f.winfo_exists():
                            f.item_id = item
                            
                            # Actualizar color basado en el hover
                            bg_color = "#0A8504" if item == hovered_item_u else "#FFFFFF"
                            if f.cget("bg") != bg_color:
                                f.config(bg=bg_color)
                                for btn in f.winfo_children():
                                    btn.config(bg=bg_color, activebackground=bg_color)
                                    
                            if getattr(f, 'last_place', None) != (x, y, w, h):
                                f.place(x=x, y=y, width=w, height=h)
                                f.last_place = (x, y, w, h)
                            used_u += 1
                            
            if hasattr(self, 'pool_frames_u'):
                for i in range(used_u, len(self.pool_frames_u)):
                    f = self.pool_frames_u[i]
                    if f.winfo_exists() and hasattr(f, 'last_place'):
                        f.place_forget()
                        delattr(f, 'last_place')

            used_p = 0
            if self.vista_actual == "puertas" and hasattr(self, 'tree_puertas') and hasattr(self, 'pool_frames_p') and self.tree_puertas.winfo_exists():
                for item in self.tree_puertas.get_children():
                    bbox = self.tree_puertas.bbox(item, "acciones")
                    if bbox and used_p < len(self.pool_frames_p):
                        x, y, w, h = bbox
                        f = self.pool_frames_p[used_p]
                        if f.winfo_exists():
                            f.item_id = item
                            
                            # Actualizar color basado en el hover
                            bg_color = "#0A8504" if item == hovered_item_p else "#FFFFFF"
                            if f.cget("bg") != bg_color:
                                f.config(bg=bg_color)
                                for btn in f.winfo_children():
                                    btn.config(bg=bg_color, activebackground=bg_color)
                                    
                            if getattr(f, 'last_place', None) != (x, y, w, h):
                                f.place(x=x, y=y, width=w, height=h)
                                f.last_place = (x, y, w, h)
                            used_p += 1
                            
            if hasattr(self, 'pool_frames_p'):
                for i in range(used_p, len(self.pool_frames_p)):
                    f = self.pool_frames_p[i]
                    if f.winfo_exists() and hasattr(f, 'last_place'):
                        f.place_forget()
                        delattr(f, 'last_place')
        except Exception as e:
            pass # Ignorar errores temporales durante transiciones de vista

        if getattr(self, 'running', False):
            self.after(50, self.mantener_frame_acciones)

    def cargar_imagen_original(self, name):
        if name not in self.iconos:
            try:
                path = self.img_paths.get(name)
                if path and os.path.exists(path):
                    img = Image.open(path)
                    self.iconos[name] = ImageTk.PhotoImage(img)
                else:
                    self.iconos[name] = ""
            except Exception as e:
                print(f"Error cargando {name}: {e}")
                self.iconos[name] = ""
        return self.iconos[name]

    def cargar_logo(self, name, height=40):
        key = f"{name}_logo_{height}"
        if key not in self.iconos:
            try:
                path = self.img_paths.get(name)
                if path and os.path.exists(path):
                    img = Image.open(path)
                    w, h = img.size
                    new_w = int(w * (height / h))
                    img = img.resize((new_w, height), Image.Resampling.LANCZOS)
                    self.iconos[key] = ImageTk.PhotoImage(img)
                else:
                    self.iconos[key] = ""
            except Exception as e:
                print(f"Error cargando logo {name}: {e}")
                self.iconos[key] = ""
        return self.iconos[key]

    def crear_interfaz_principal(self):
        # Sidebar Frame (takes full height on the left)
        self.frame_sidebar = tk.Frame(self, bg="#2B2D30", width=220)
        self.frame_sidebar.pack_propagate(False)
        self.frame_sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        # Main content area
        self.frame_main = tk.Frame(self, bg="#F4F6F9")
        self.frame_main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Top Bar inside Main Content
        self.frame_top = tk.Frame(self.frame_main, bg="#FFFFFF", height=70)
        self.frame_top.pack(fill=tk.X, side=tk.TOP)
        self.frame_top.pack_propagate(False)
        
        self.frame_top_sep = tk.Frame(self.frame_main, bg="#E0E0E0", height=1)
        self.frame_top_sep.pack(fill=tk.X, side=tk.TOP)
        
        ico_menu = self.cargar_icono("menu", 28)
        btn_hamburguesa = tk.Button(self.frame_top, image=ico_menu if ico_menu else None, text="☰" if not ico_menu else "", font=("Segoe UI", 18), bg="#FFFFFF", fg="#2B2D30", bd=0, activebackground="#F4F6F9", cursor="hand2", command=self.toggle_menu)
        btn_hamburguesa.pack(side=tk.LEFT, padx=15, pady=10)
        
        # Titulo superior
        self.lbl_titulo = tk.Label(self.frame_top, text="REGISTROS DE RFID - SISTEMA CENTRAL", bg="#FFFFFF", fg="#1A1A1A", font=("Segoe UI", 14, "bold"))
        self.lbl_titulo.pack(side=tk.LEFT, padx=20)
        
        btn_logout = tk.Button(self.frame_top, text="Cerrar Sesión", bg="#A00000", fg="#FFFFFF", font=("Segoe UI", 9, "bold"), bd=0, activebackground="#D00000", activeforeground="#FFFFFF", command=self.cerrar_sesion)
        btn_logout.pack(side=tk.RIGHT, padx=20, pady=15)

        self.lbl_estado_serial = tk.Label(self.frame_top, text="Lector: Buscando...", fg="#6c757d", bg="#FFFFFF", font=("Segoe UI", 9, "bold"))
        self.lbl_estado_serial.pack(side=tk.RIGHT, padx=15)
        
        self.menu_visible = True
        self.animating_menu = False
        
        self.construir_sidebar()
        
        self.vista_actual = None
        self.mostrar_vista_login() # Vista por defecto inicial

    def construir_sidebar(self):
        for widget in self.frame_sidebar.winfo_children():
            widget.destroy()
            
        # Header sidebar
        frame_logo = tk.Frame(self.frame_sidebar, bg="#2B2D30", height=70)
        frame_logo.pack(fill=tk.X, side=tk.TOP)
        frame_logo.pack_propagate(False)
        ico_logo = self.cargar_logo("logo", 30)
        if ico_logo:
            tk.Label(frame_logo, image=ico_logo, bg="#2B2D30").pack(side=tk.LEFT, padx=15, pady=20)
        tk.Label(frame_logo, text="SISTEMA RFID", font=("Segoe UI", 12, "bold"), bg="#2B2D30", fg="#FFFFFF").pack(side=tk.LEFT, pady=20)
        
        tk.Frame(self.frame_sidebar, bg="#1E1F22", height=1).pack(fill=tk.X, pady=(0, 10))
        
        # Botón Tablero (Logs)
        if self.rol_actual in ['Superadmin', 'Admin', 'ingeniero']:
            btn_tablero = ttk.Button(self.frame_sidebar, text="  Tablero", image=self.cargar_icono("buscar", 16), compound=tk.LEFT, style="Menu.TButton", command=self.mostrar_vista_tablero)
            btn_tablero.pack(fill=tk.X, pady=2)
        
        # Botón principal Usuarios
        self.btn_main_usuarios = ttk.Button(self.frame_sidebar, text="  Usuarios", image=self.cargar_icono("accept", 16), compound=tk.LEFT, style="Menu.TButton", command=self.toggle_submenu_usuarios)
        self.btn_main_usuarios.pack(fill=tk.X, pady=2)
        
        self.frame_sub_usuarios = tk.Frame(self.frame_sidebar, bg="#1E1F22", height=0)
        self.frame_sub_usuarios.pack_propagate(False)
        
        btn_reg_u = ttk.Button(self.frame_sub_usuarios, text="  Nuevos Registros", style="SubMenu.TButton", command=self.mostrar_vista_formulario_usuario)
        btn_reg_u.pack(fill=tk.X, pady=2)

        # Botón principal Puertas
        self.btn_main_puertas = ttk.Button(self.frame_sidebar, text="  Puertas", image=self.cargar_icono("accept", 16), compound=tk.LEFT, style="Menu.TButton", command=self.toggle_submenu_puertas)
        self.btn_main_puertas.pack(fill=tk.X, pady=2)
        
        self.frame_sub_puertas = tk.Frame(self.frame_sidebar, bg="#1E1F22", height=0)
        self.frame_sub_puertas.pack_propagate(False)
        
        btn_add_p = ttk.Button(self.frame_sub_puertas, text="  Agregar", style="SubMenu.TButton", command=self.mostrar_vista_formulario_puerta)
        btn_add_p.pack(fill=tk.X, pady=2)

            
        # Botón principal Visor
        self.btn_main_visor = ttk.Button(self.frame_sidebar, text="  Visor", image=self.cargar_icono("buscar", 16), compound=tk.LEFT, style="Menu.TButton", command=self.toggle_submenu_visor)
        self.btn_main_visor.pack(fill=tk.X, pady=2)
        
        self.frame_sub_visor = tk.Frame(self.frame_sidebar, bg="#1E1F22", height=0)
        self.frame_sub_visor.pack_propagate(False)
        
        from config import AREAS
        
        btn_visor_gen = ttk.Button(self.frame_sub_visor, text="  General", style="SubMenu.TButton", command=lambda: self.mostrar_vista_visor("General"))
        btn_visor_gen.pack(fill=tk.X, pady=2)
        
        for a_id, a_name in AREAS.items():
            btn_v = ttk.Button(self.frame_sub_visor, text=f"  {a_name}", style="SubMenu.TButton", command=lambda an=a_name: self.mostrar_vista_visor(an))
            btn_v.pack(fill=tk.X, pady=2)
            
        # Botón Activar en el sidebar principal
        btn_activar = ttk.Button(self.frame_sidebar, text="  Activar puerta", image=self.cargar_icono("activar", 16), compound=tk.LEFT, style="Menu.TButton", command=self.mostrar_vista_flashear_esp32)
        btn_activar.pack(fill=tk.X, pady=5)
        
        btn_formatear = ttk.Button(self.frame_sidebar, text="  Desactivar puerta", image=self.cargar_icono("eliminar", 16), compound=tk.LEFT, style="Menu.TButton", command=self.mostrar_vista_formatear_esp32)
        btn_formatear.pack(fill=tk.X, pady=5)

        # Sección Lectores Activos
        tk.Frame(self.frame_sidebar, bg="#1E1F22", height=1).pack(fill=tk.X, pady=(20, 10))
        ttk.Label(self.frame_sidebar, text="PUERTAS", style="Sidebar.TLabel").pack(anchor="w", padx=20, pady=5)
        
        self.frame_lista_puertas = tk.Frame(self.frame_sidebar, bg="#2B2D30")
        self.frame_lista_puertas.pack(fill=tk.BOTH, expand=True)
        self.render_lista_puertas_sidebar()

    def render_lista_puertas_sidebar(self):
        if not hasattr(self, 'frame_lista_puertas') or not self.frame_lista_puertas.winfo_exists():
            return
            
        if not hasattr(self, 'estado_anterior_puertas'):
            self.estado_anterior_puertas = {}
            
        if not hasattr(self, 'widgets_puertas'):
            self.widgets_puertas = {}
            
        # Limpiar referencias a widgets muertos (si se recargó la vista)
        dead_macs = [m for m, w in self.widgets_puertas.items() if not w["frame"].winfo_exists()]
        for m in dead_macs:
            del self.widgets_puertas[m]
            
        try:
            import puertas
            from config import AREAS
            lista_puertas = puertas.listar_puertas()
            macs_actuales = set()
            
            if not lista_puertas:
                if not hasattr(self, 'lbl_no_puertas') or not self.lbl_no_puertas.winfo_exists():
                    self.lbl_no_puertas = tk.Label(self.frame_lista_puertas, text="Ningún lector registrado", fg="#6c757d", bg="#2B2D30", font=("Segoe UI", 9))
                    self.lbl_no_puertas.pack(anchor="w", padx=20, pady=5)
            else:
                if hasattr(self, 'lbl_no_puertas') and self.lbl_no_puertas.winfo_exists():
                    self.lbl_no_puertas.destroy()
                    delattr(self, 'lbl_no_puertas')
                    
                for p in lista_puertas:
                    if len(p) == 5:
                        mac, nombre, area_id, tipo, activa = p
                    else:
                        mac, nombre, area_id, tipo = p
                        activa = 0
                    
                    macs_actuales.add(mac)
                    estado_previo = self.estado_anterior_puertas.get(mac, -1)
                    
                    import time
                    current_time = time.time()
                    if not hasattr(self, 'ultimo_aviso_inactividad'):
                        self.ultimo_aviso_inactividad = {}
                        
                    if getattr(self, 'rol_actual', None):
                        if activa == 0:
                            ultimo_aviso = self.ultimo_aviso_inactividad.get(mac, 0)
                            
                            if estado_previo in (1, -1):
                                from tkinter import messagebox
                                self.after(1500, lambda n=nombre: messagebox.showwarning("Puerta Inactiva", f"¡Alerta!\n\nLa puerta '{n}' está inactiva.\nPor favor, revise el problema."))
                                self.ultimo_aviso_inactividad[mac] = current_time
                            else:
                                if (current_time - ultimo_aviso) >= 900:
                                    from tkinter import messagebox
                                    self.after(1500, lambda n=nombre: messagebox.showinfo("Recordatorio", f"Recordatorio:\n\nLa puerta '{n}' sigue inactiva.\nPor favor, revise el problema."))
                                    self.ultimo_aviso_inactividad[mac] = current_time
                                    
                        elif activa == 1 and estado_previo == 0:
                            from tkinter import messagebox
                            self.after(1500, lambda n=nombre: messagebox.showinfo("Puerta Conectada", f"¡Buenas noticias!\n\nLa puerta '{n}' ya se encuentra activa y conectada nuevamente."))
                            
                        self.estado_anterior_puertas[mac] = activa
                    
                    area_nombre = AREAS.get(str(area_id), f"Área {area_id}")
                    color_estado = "#0A8504" if activa else "#9C0303"
                    
                    if mac not in self.widgets_puertas:
                        f_lector = tk.Frame(self.frame_lista_puertas, bg="#2B2D30")
                        f_lector.pack(fill=tk.X, padx=20, pady=5)
                        
                        lbl_circulo = tk.Label(f_lector, text="●", fg=color_estado, bg="#2B2D30", font=("Segoe UI", 10))
                        lbl_circulo.pack(side=tk.LEFT, anchor="n", pady=(2, 0))
                        
                        f_textos = tk.Frame(f_lector, bg="#2B2D30")
                        f_textos.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
                        
                        lbl_nombre = tk.Label(f_textos, text=nombre, fg="#A1A1AA", bg="#2B2D30", font=("Segoe UI", 9), anchor="w", justify="left", wraplength=140)
                        lbl_nombre.pack(fill=tk.X)
                        
                        lbl_area = tk.Label(f_textos, text=area_nombre, fg="#6c757d", bg="#2B2D30", font=("Segoe UI", 8), anchor="w", justify="left", wraplength=140)
                        lbl_area.pack(fill=tk.X)
                        
                        self.widgets_puertas[mac] = {
                            "frame": f_lector,
                            "circulo": lbl_circulo,
                            "nombre": lbl_nombre,
                            "area": lbl_area
                        }
                    else:
                        w = self.widgets_puertas[mac]
                        if w["circulo"].cget("fg") != color_estado:
                            w["circulo"].config(fg=color_estado)
                        if w["nombre"].cget("text") != nombre:
                            w["nombre"].config(text=nombre)
                        if w["area"].cget("text") != area_nombre:
                            w["area"].config(text=area_nombre)
                            
            macs_borrar = [m for m in self.widgets_puertas if m not in macs_actuales]
            for m in macs_borrar:
                self.widgets_puertas[m]["frame"].destroy()
                del self.widgets_puertas[m]
                
        except Exception as e:
            print(f"Error en render_lista_puertas_sidebar: {e}")

    def loop_actualizar_puertas(self):
        if getattr(self, 'running', False):
            self.render_lista_puertas_sidebar()
            self.after(2000, self.loop_actualizar_puertas)

    def mostrar_vista_tablero(self):
        if getattr(self, 'vista_actual', None) == "tablero": return
        self.limpiar_vista()
        self.vista_actual = "tablero"
        self.lbl_titulo.config(text="MONITOR GENERAL")
        
        # Filtro superior
        frame_filtro = tk.Frame(self.frame_main, bg="#FFFFFF")
        frame_filtro.pack(fill=tk.X, padx=25, pady=(25, 0))
        
        tk.Label(frame_filtro, text="Filtrar por Área:", font=("Segoe UI", 10, "bold"), bg="#FFFFFF").pack(side=tk.LEFT, padx=(10, 5))
        
        from config import AREAS
        opciones_area = ["Todas"] + [f"{k} - {v}" for k, v in AREAS.items()]
        
        self.area_filtro_tablero = tk.StringVar(value="Todas")
        cb_area = ttk.Combobox(frame_filtro, textvariable=self.area_filtro_tablero, values=opciones_area, state="readonly", font=("Segoe UI", 10), width=30)
        cb_area.pack(side=tk.LEFT, padx=5, pady=10)
        
        def on_area_change(event):
            self.last_log_id = 0
            for item in self.tree_logs.get_children(): self.tree_logs.delete(item)
            self.cargar_usuarios_activos_tablero()
            
        cb_area.bind("<<ComboboxSelected>>", on_area_change)
        
        # Tarjeta superior: Usuarios Activos en el Área
        card_usuarios = tk.Frame(self.frame_main, bg="#FFFFFF", bd=0, highlightbackground="#E0E0E0", highlightthickness=1)
        card_usuarios.pack(fill=tk.BOTH, expand=False, padx=25, pady=(15, 10))
        
        tk.Label(card_usuarios, text="USUARIOS AUTORIZADOS", bg="#FFFFFF", fg="#6c757d", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=10)
        
        col_us = ("uid", "nombre", "areas")
        self.tree_usuarios_tablero = ttk.Treeview(card_usuarios, columns=col_us, show="headings", selectmode="none", height=5)
        self.tree_usuarios_tablero.heading("uid", text="UID Tarjeta")
        self.tree_usuarios_tablero.heading("nombre", text="Nombre")
        self.tree_usuarios_tablero.heading("areas", text="Áreas Permitidas")
        self.tree_usuarios_tablero.column("uid", width=150, anchor=tk.W)
        self.tree_usuarios_tablero.column("nombre", width=250, anchor=tk.W)
        self.tree_usuarios_tablero.column("areas", width=300, anchor=tk.W)
        
        scroll_ux = ttk.Scrollbar(card_usuarios, orient=tk.HORIZONTAL, command=self.tree_usuarios_tablero.xview)
        scroll_ux.pack(side=tk.BOTTOM, fill=tk.X, padx=(15, 15))
        
        scroll_u = ttk.Scrollbar(card_usuarios, orient=tk.VERTICAL, command=self.tree_usuarios_tablero.yview)
        scroll_u.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 15), pady=(0, 15))
        
        self.tree_usuarios_tablero.configure(yscrollcommand=scroll_u.set, xscrollcommand=scroll_ux.set)
        self.tree_usuarios_tablero.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0), pady=(0, 15))
        
        # Tarjeta inferior: Registros
        card_logs = tk.Frame(self.frame_main, bg="#FFFFFF", bd=0, highlightbackground="#E0E0E0", highlightthickness=1)
        card_logs.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))
        
        tk.Label(card_logs, text="REGISTROS DE ACCESO EN TIEMPO REAL", bg="#FFFFFF", fg="#6c757d", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=10)
        
        col_logs = ("id_tag", "tipo", "ubicacion", "estado", "fecha", "hora_ent", "hora_sal")
        self.tree_logs = ttk.Treeview(card_logs, columns=col_logs, show="headings", selectmode="none")
        self.tree_logs.heading("id_tag", text="ID Tag")
        self.tree_logs.heading("tipo", text="Nombre / Usuario")
        self.tree_logs.heading("ubicacion", text="Ubicación")
        self.tree_logs.heading("estado", text="Estado")
        self.tree_logs.heading("fecha", text="Fecha")
        self.tree_logs.heading("hora_ent", text="Hora Entrada")
        self.tree_logs.heading("hora_sal", text="Hora Salida")
        self.tree_logs.column("id_tag", width=120, anchor=tk.W)
        self.tree_logs.column("tipo", width=200, anchor=tk.W)
        self.tree_logs.column("ubicacion", width=150, anchor=tk.W)
        self.tree_logs.column("estado", width=100, anchor=tk.W)
        self.tree_logs.column("fecha", width=100, anchor=tk.W)
        self.tree_logs.column("hora_ent", width=120, anchor=tk.W)
        self.tree_logs.column("hora_sal", width=120, anchor=tk.W)
        
        self.tree_logs.tag_configure("Leido", foreground="#0A8504")
        self.tree_logs.tag_configure("Denegado", foreground="#9C0303")
        
        scroll_l = ttk.Scrollbar(card_logs, orient=tk.VERTICAL, command=self.tree_logs.yview)
        self.tree_logs.configure(yscrollcommand=scroll_l.set)
        self.tree_logs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0), pady=(0, 15))
        scroll_l.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 15), pady=(0, 15))
        
        self.cargar_usuarios_activos_tablero()
        self.last_log_id = 0
        self.actualizar_logs_tablero()

    def cargar_usuarios_activos_tablero(self):
        if getattr(self, 'vista_actual', None) != "tablero": return
        for item in self.tree_usuarios_tablero.get_children(): self.tree_usuarios_tablero.delete(item)
        
        from database import conectar_db
        conn = conectar_db()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT uid, nombre, areas FROM tarjetas WHERE activa=1 ORDER BY nombre ASC")
            usuarios_activos = cur.fetchall()
            
            filtro_texto = self.area_filtro_tablero.get()
            filtro_id = None
            if filtro_texto != "Todas" and " - " in filtro_texto:
                filtro_id = filtro_texto.split(" - ")[0]
                
            for u in usuarios_activos:
                uid, nombre, areas = u
                if not areas: areas = ""
                # Si hay filtro, checar que el filtro_id este en la lista de areas del usuario
                if filtro_id:
                    areas_list = [a.strip() for a in areas.split(",")]
                    if filtro_id not in areas_list:
                        continue
                import permisos
                nombres_areas = permisos.areas_a_nombres(areas)
                self.tree_usuarios_tablero.insert("", tk.END, values=(uid, nombre, nombres_areas))
        except Exception as e:
            print(f"Error cargando usuarios en tablero: {e}")
        finally:
            conn.close()

    def actualizar_logs_tablero(self):
        if getattr(self, 'vista_actual', None) != "tablero": return
        import threading
        from database import conectar_db
        
        def fetch_task():
            conn = conectar_db()
            if not conn:
                self.after(2000, self.actualizar_logs_tablero)
                return
            try:
                cur = conn.cursor()
                
                filtro_texto = self.area_filtro_tablero.get()
                filtro_id = None
                if filtro_texto != "Todas" and " - " in filtro_texto:
                    filtro_id = filtro_texto.split(" - ")[0]
                
                # Fetch latest 50 logs every time to catch updates
                query = """
                    SELECT r.id, r.uid, r.area, r.fecha, r.fecha_salida, r.tipo, t.nombre, t.activa
                    FROM registros_acceso r
                    LEFT JOIN tarjetas t ON r.uid = t.uid
                """
                params = []
                if filtro_id:
                    query += " WHERE r.area = %s "
                    params.append(filtro_id)
                    
                query += " ORDER BY r.id DESC LIMIT 50"
                
                cur.execute(query, tuple(params))
                nuevos_logs = cur.fetchall()
                # Reverse to insert older first at top, wait, if we insert at 0, the last one inserted ends up at the very top.
                # Since we want DESC order in UI, we should insert the newest last at index 0. So we process from oldest to newest.
                nuevos_logs.reverse()
                
                self.after(0, lambda: self.render_logs_tablero(nuevos_logs))
            except Exception as e:
                print(f"Error actualizando logs: {e}")
                self.after(2000, self.actualizar_logs_tablero)
            finally:
                conn.close()
                
        threading.Thread(target=fetch_task, daemon=True).start()

    def render_logs_tablero(self, nuevos_logs):
        if getattr(self, 'vista_actual', None) != "tablero": return
        from config import AREAS
        for log in nuevos_logs:
            log_id, uid, area, fecha, fecha_salida, tipo, nombre_db, activa = log
            
            estado = "Leído" if activa else "Denegado"
            tag_color = "Leido" if estado == "Leído" else "Denegado"
            nombre = nombre_db if nombre_db else "Desconocido"
            
            area_nombre = AREAS.get(str(area), str(area))
            
            fecha_str = str(fecha) if fecha else ""
            fs_str = str(fecha_salida) if fecha_salida else ""
            
            base_date = fecha_str if fecha_str else fs_str
            fecha_solo = base_date[0:10] if len(base_date) >= 10 else "--/--/----"
            
            hora_ent = fecha_str[11:19] if len(fecha_str) >= 19 else "--:--:--"
            hora_sal = fs_str[11:19] if len(fs_str) >= 19 else "--:--:--"
            
            iid = str(log_id)
            vals = ("● " + uid, nombre, area_nombre, estado, fecha_solo, hora_ent, hora_sal)
            
            if self.tree_logs.exists(iid):
                self.tree_logs.item(iid, values=vals, tags=(tag_color,))
            else:
                self.tree_logs.insert("", 0, iid=iid, values=vals, tags=(tag_color,))
            
        self.after(2000, self.actualizar_logs_tablero)

    def animate_height(self, frame, current_height, target_height, step, on_complete=None):
        if current_height != target_height:
            current_height += step
            if (step > 0 and current_height > target_height) or (step < 0 and current_height < target_height):
                current_height = target_height
            frame.config(height=current_height)
            self.after(10, self.animate_height, frame, current_height, target_height, step, on_complete)
        else:
            if on_complete:
                on_complete()

    def toggle_submenu_usuarios(self):
        if self.vista_actual != "usuarios":
            self.mostrar_vista_usuarios()
            
        self.submenu_usuarios_visible = not getattr(self, 'submenu_usuarios_visible', False)
        
        target_h = 40
        if self.submenu_usuarios_visible:
            self.frame_sub_usuarios.pack(fill=tk.X, padx=10, after=self.btn_main_usuarios)
            self.animate_height(self.frame_sub_usuarios, 0, target_h, 8)
            if getattr(self, 'submenu_puertas_visible', False):
                self.submenu_puertas_visible = False
                self.animate_height(self.frame_sub_puertas, 40, 0, -8, on_complete=lambda: self.frame_sub_puertas.pack_forget())
            if getattr(self, 'submenu_visor_visible', False):
                self.submenu_visor_visible = False
                from config import AREAS
                h_visor = 40 * (len(AREAS) + 1)
                self.animate_height(self.frame_sub_visor, h_visor, 0, -8, on_complete=lambda: self.frame_sub_visor.pack_forget())
        else:
            self.animate_height(self.frame_sub_usuarios, target_h, 0, -8, on_complete=lambda: self.frame_sub_usuarios.pack_forget())
            
    def toggle_submenu_puertas(self):
        if self.vista_actual != "puertas":
            self.mostrar_vista_puertas()
            
        self.submenu_puertas_visible = not getattr(self, 'submenu_puertas_visible', False)
        
        target_h = 40
        if self.submenu_puertas_visible:
            self.frame_sub_puertas.pack(fill=tk.X, padx=10, after=self.btn_main_puertas)
            self.animate_height(self.frame_sub_puertas, 0, target_h, 8)
            if getattr(self, 'submenu_usuarios_visible', False):
                self.submenu_usuarios_visible = False
                self.animate_height(self.frame_sub_usuarios, 40, 0, -8, on_complete=lambda: self.frame_sub_usuarios.pack_forget())
            if getattr(self, 'submenu_visor_visible', False):
                self.submenu_visor_visible = False
                from config import AREAS
                h_visor = 40 * (len(AREAS) + 1)
                self.animate_height(self.frame_sub_visor, h_visor, 0, -8, on_complete=lambda: self.frame_sub_visor.pack_forget())
        else:
            self.animate_height(self.frame_sub_puertas, target_h, 0, -8, on_complete=lambda: self.frame_sub_puertas.pack_forget())

    def toggle_submenu_visor(self):
        self.submenu_visor_visible = not getattr(self, 'submenu_visor_visible', False)
        from config import AREAS
        target_h = 40 * (len(AREAS) + 1)
        if self.submenu_visor_visible:
            self.frame_sub_visor.pack(fill=tk.X, padx=10, after=self.btn_main_visor)
            self.animate_height(self.frame_sub_visor, 0, target_h, 8)
            
            if getattr(self, 'submenu_usuarios_visible', False):
                self.submenu_usuarios_visible = False
                self.animate_height(self.frame_sub_usuarios, 40, 0, -8, on_complete=lambda: self.frame_sub_usuarios.pack_forget())
            if getattr(self, 'submenu_puertas_visible', False):
                self.submenu_puertas_visible = False
                self.animate_height(self.frame_sub_puertas, 40, 0, -8, on_complete=lambda: self.frame_sub_puertas.pack_forget())
        else:
            self.animate_height(self.frame_sub_visor, target_h, 0, -8, on_complete=lambda: self.frame_sub_visor.pack_forget())

    def toggle_menu(self):
        if getattr(self, 'animating_menu', False): return
        self.animating_menu = True
        
        if self.menu_visible:
            target_w = 1
            step = -20
        else:
            self.frame_sidebar.config(width=1)
            self.frame_sidebar.pack(side=tk.LEFT, fill=tk.Y, before=self.frame_main)
            target_w = 220
            step = 20
            
        def animate(current_w):
            if (step > 0 and current_w < target_w) or (step < 0 and current_w > target_w):
                current_w += step
                if current_w < 1: current_w = 1
                if current_w > 220: current_w = 220
                self.frame_sidebar.config(width=current_w)
                self.after(10, animate, current_w)
            else:
                if step < 0:
                    self.frame_sidebar.pack_forget()
                    self.menu_visible = False
                else:
                    self.frame_sidebar.config(width=220)
                    self.menu_visible = True
                self.animating_menu = False
                
        animate(self.frame_sidebar.winfo_width())

    def _check_sidebar_close(self, event):
        if not self.menu_visible: return
        # Cerrar si se hace click/mueve el mouse fuera del menú (170px)
        if event.x_root > self.winfo_rootx() + 170:
            self.toggle_menu()

    def limpiar_vista(self):
        for widget in self.frame_main.winfo_children():
            if widget in (getattr(self, 'frame_top', None), getattr(self, 'frame_top_sep', None)): continue
            widget.destroy()
            
        img_fondo = self.cargar_imagen_original("fondo_inicio")
        if img_fondo:
            lbl_fondo = tk.Label(self.frame_main, image=img_fondo, bg="#F4F6F9")
            lbl_fondo.place(x=0, y=0, relwidth=1, relheight=1)
            lbl_fondo.lower()

    # ========================== LOGIN ==========================
    def mostrar_vista_login(self):
        self.vista_actual = "login"
        if hasattr(self, 'frame_top'): self.frame_top.pack_forget()
        if hasattr(self, 'frame_top_sep'): self.frame_top_sep.pack_forget()
        if getattr(self, 'menu_visible', False):
            self.frame_sidebar.pack_forget()
            self.menu_visible = False
            
        self.limpiar_vista()
        
        frame_login = tk.Frame(self.frame_main, bg="#FFFFFF", bd=0, highlightbackground="#E0E0E0", highlightthickness=1)
        frame_login.place(relx=0.5, rely=0.5, anchor="center", width=400, height=350)
        
        ico_logo = self.cargar_logo("logo", 50)
        if ico_logo:
            tk.Label(frame_login, image=ico_logo, bg="#FFFFFF").pack(pady=(20,10))
            
        tk.Label(frame_login, text="Iniciar Sesión", font=("Segoe UI", 18, "bold"), fg="#1A1A1A", bg="#FFFFFF").pack(pady=10)
        
        tk.Label(frame_login, text="Usuario:", font=("Segoe UI", 10), bg="#FFFFFF").pack(anchor="w", padx=50)
        ent_user = ttk.Entry(frame_login, font=("Segoe UI", 12))
        ent_user.pack(fill=tk.X, padx=50, pady=5)
        
        tk.Label(frame_login, text="Contraseña:", font=("Segoe UI", 10), bg="#FFFFFF").pack(anchor="w", padx=50, pady=(10,0))
        ent_pass = ttk.Entry(frame_login, font=("Segoe UI", 12), show="*")
        ent_pass.pack(fill=tk.X, padx=50, pady=5)
        
        def intentar_login(event=None):
            usuario = ent_user.get()
            clave = ent_pass.get()
            import auth
            rol = auth.login(usuario, clave)
            if rol:
                self.rol_actual = rol
                self.usuario_actual = usuario
                self.frame_top.pack(fill=tk.X, side=tk.TOP)
                self.frame_top_sep.pack(fill=tk.X, side=tk.TOP)
                self.construir_sidebar()
                self.frame_sidebar.config(width=220)
                self.frame_sidebar.pack(side=tk.LEFT, fill=tk.Y, before=self.frame_main)
                self.menu_visible = True
                
                if rol in ['Superadmin', 'Admin', 'ingeniero']:
                    self.mostrar_vista_tablero()
                else:
                    self.mostrar_vista_usuarios()
            else:
                messagebox.showerror("Error", "Credenciales incorrectas", parent=self)
                
        btn_login = tk.Button(frame_login, text="Entrar", bg="#007BFF", fg="#FFFFFF", font=("Segoe UI", 12, "bold"), command=intentar_login)
        btn_login.pack(fill=tk.X, padx=50, pady=20)
        ent_pass.bind("<Return>", intentar_login)
        
        self.focus_force()
        ent_user.focus_set()
        
    def cerrar_sesion(self):
        self.rol_actual = None
        self.usuario_actual = None
        self.mostrar_vista_login()

    # ========================== VISTA BIENVENIDA ==========================
    def mostrar_vista_bienvenida(self):
        if self.vista_actual == "bienvenida": return
        self.limpiar_vista()
        self.vista_actual = "bienvenida"
        self.lbl_titulo.config(text="INICIO")
        
        frame_bienvenida = tk.Frame(self.frame_main, bg="#FFFFFF")
        frame_bienvenida.pack(expand=True, fill=tk.BOTH)
        
        img_fondo = self.cargar_imagen_original("fondo_inicio")
        if img_fondo:
            # Mostrar la imagen cubriendo el frame o centrada
            lbl_img = tk.Label(frame_bienvenida, image=img_fondo, bg="#FFFFFF")
            lbl_img.place(relx=0.5, rely=0.5, anchor="center")
        else:
            lbl_titulo = tk.Label(frame_bienvenida, text="Bienvenido al Panel de Administración RFID", font=("Poppins", 24, "bold"), fg="#033966", bg="#FFFFFF")
            lbl_titulo.pack(pady=(200, 20))
            lbl_subtitulo = tk.Label(frame_bienvenida, text="Seleccione una opción del menú lateral izquierdo para comenzar.", font=("Poppins", 14), fg="#404040", bg="#FFFFFF")
            lbl_subtitulo.pack(pady=10)

    # ========================== VISTA USUARIOS ==========================
    def mostrar_vista_usuarios(self):
        if getattr(self, 'vista_actual', None) == "usuarios": return
        self.limpiar_vista()
        self.vista_actual = "usuarios"
        self.lbl_titulo.config(text="USUARIOS")
        
        # Barra de búsqueda y filtrado
        frame_busqueda = tk.Frame(self.frame_main, bg="#FFFFFF")
        frame_busqueda.pack(fill=tk.X, pady=10, padx=20)
        
        ico_buscar = self.cargar_icono("buscar", 16)
        tk.Label(frame_busqueda, text=" Buscar:", image=ico_buscar if ico_buscar else None, compound=tk.LEFT, bg="#FFFFFF", font=("Poppins", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        
        self.var_busqueda = tk.StringVar()
        self.var_busqueda.trace("w", lambda name, index, mode: self.cargar_tabla_usuarios())
        ent_busqueda = ttk.Entry(frame_busqueda, textvariable=self.var_busqueda, font=("Poppins", 10), width=30)
        ent_busqueda.pack(side=tk.LEFT, padx=5)
        
        tk.Label(frame_busqueda, text="Filtrar por Área:", bg="#FFFFFF", font=("Poppins", 10, "bold")).pack(side=tk.LEFT, padx=(20, 5))
        
        a_list = ["Todas"] + [f"{k} - {v}" for k,v in AREAS.items()]
        self.var_area_filtro = tk.StringVar(value="Todas")
        
        btn_filtro = tk.Button(frame_busqueda, text="Todas ▼", bg="#033966", fg="#FFFFFF", font=("Poppins", 10, "bold"), bd=0, activebackground="#0A8504", activeforeground="#FFFFFF")
        btn_filtro.pack(side=tk.LEFT, padx=5, ipady=3, ipadx=10)
        
        ico_hourglass = self.cargar_icono("hourglass", 24)
        ttk.Button(frame_busqueda, text=" Recargar", image=ico_hourglass, compound=tk.LEFT, command=self.cargar_tabla_usuarios).pack(side=tk.RIGHT, padx=5)

        # Dropdown flotante (sin contenedor que empuje)
        frame_filtro = tk.Frame(self.frame_main, bg="#F0F0F0", height=0)
        frame_filtro.pack_propagate(False)
        
        target_h_f = len(a_list) * 28 + 10
        btn_filtro.is_open = False
        
        def toggle_filtro():
            if btn_filtro.is_open:
                btn_filtro.is_open = False
                self.animate_height(frame_filtro, target_h_f, 0, -20, on_complete=lambda: frame_filtro.place_forget())
            else:
                btn_filtro.is_open = True
                
                # Calcular posición flotante relativa a frame_main
                bx = btn_filtro.winfo_x() + btn_filtro.master.winfo_x()
                by = btn_filtro.winfo_y() + btn_filtro.master.winfo_y() + btn_filtro.winfo_height()
                bw = max(btn_filtro.winfo_width(), 150)
                
                frame_filtro.place(x=bx, y=by, width=bw)
                frame_filtro.lift() # Poner por encima de la tabla
                self.animate_height(frame_filtro, 0, target_h_f, 20)
                
        btn_filtro.config(command=toggle_filtro)
        
        def select_filtro(val):
            self.var_area_filtro.set(val)
            btn_filtro.config(text=f"{val.split(' - ')[0]} ▼")
            toggle_filtro()
            self.cargar_tabla_usuarios()
            
        for val in a_list:
            tk.Button(frame_filtro, text=val, bg="#F0F0F0", fg="#000000", bd=0, anchor="w", font=("Poppins", 10), command=lambda v=val: select_filtro(v)).pack(fill=tk.X, padx=10, pady=2)

        frame_tabla = tk.Frame(self.frame_main, bg="#FFFFFF")
        frame_tabla.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        columnas = ("uid", "nombre", "areas", "fecha", "modificacion", "acciones")
        self.tree_usuarios = ttk.Treeview(frame_tabla, columns=columnas, show="headings")
        self.tree_usuarios.heading("uid", text="UID TARJETA")
        self.tree_usuarios.heading("nombre", text="NOMBRE EMPLEADO")
        self.tree_usuarios.heading("areas", text="ÁREAS AUTORIZADAS")
        self.tree_usuarios.heading("fecha", text="FECHA DE REGISTRO")
        self.tree_usuarios.heading("modificacion", text="ÚLTIMA MODIFICACIÓN")
        self.tree_usuarios.heading("acciones", text="ACCIONES")
        
        self.tree_usuarios.column("uid", width=120, anchor="center")
        self.tree_usuarios.column("nombre", width=250, anchor="center")
        self.tree_usuarios.column("areas", width=350, anchor="center")
        self.tree_usuarios.column("fecha", width=150, anchor="center")
        self.tree_usuarios.column("modificacion", width=280, anchor="center")
        self.tree_usuarios.column("acciones", width=120, anchor="center")

        self.tree_usuarios.tag_configure("hover", background="#0A8504", foreground="#FFFFFF")

        scrollbar_x = ttk.Scrollbar(frame_tabla, orient=tk.HORIZONTAL, command=self.tree_usuarios.xview)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        scrollbar = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree_usuarios.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_usuarios.configure(yscrollcommand=scrollbar.set, xscrollcommand=scrollbar_x.set)
        
        self.tree_usuarios.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        


        self.tree_usuarios.bind("<ButtonRelease-1>", self.on_click_tree_usuarios)
        self.tree_usuarios.bind("<Button-3>", self.on_right_click_tree_usuarios)
        
        self.cargar_tabla_usuarios()

    def cargar_tabla_usuarios(self):
        if self.vista_actual != "usuarios": return
        for item in self.tree_usuarios.get_children(): self.tree_usuarios.delete(item)
        

        
        texto_busqueda = ""
        if hasattr(self, 'var_busqueda'):
            texto_busqueda = self.var_busqueda.get().strip().lower()
            
        area_filtro = "Todas"
        if hasattr(self, 'var_area_filtro'):
            area_filtro = self.var_area_filtro.get()
            
        area_id_filtro = None
        if area_filtro != "Todas" and " - " in area_filtro:
            area_id_filtro = area_filtro.split(" - ")[0]
        
        for t in usuarios.listar_usuarios():
            if t[4]: # activa
                uid = t[0]
                nombre = t[1]
                areas_raw = t[2]
                
                # Filtro por texto
                if texto_busqueda:
                    if texto_busqueda not in uid.lower() and texto_busqueda not in nombre.lower():
                        continue
                        
                # Filtro por área
                if area_id_filtro:
                    lista_areas_ids = [a.strip() for a in areas_raw.split(",") if a.strip()]
                    if area_id_filtro not in lista_areas_ids:
                        continue
                
                nombres_areas = permisos.areas_a_nombres(areas_raw)
                
                fecha_mod = str(t[5])[:16] if len(t) > 5 and t[5] else str(t[3])[:16]
                
                self.tree_usuarios.insert("", tk.END, values=(uid, nombre, nombres_areas, str(t[3])[:16], fecha_mod, ""))
                
        self.auto_ajustar_columnas(self.tree_usuarios)

    def mostrar_vista_formulario_usuario(self, uid_editar=None, nombre_editar="", areas_editar=""):
        self.limpiar_vista()
        self.vista_actual = "formulario_usuario"
        self.lbl_titulo.config(text="EDITAR USUARIO" if uid_editar else "REGISTRAR USUARIO")
        
        frame_header = tk.Frame(self.frame_main, bg="#FFFFFF")
        frame_header.pack(fill=tk.X, pady=(20, 10), padx=30)
        
        ttk.Button(frame_header, text="← Volver", command=self.mostrar_vista_usuarios).pack(side=tk.LEFT)
        titulo_texto = "Editar Usuario" if uid_editar else "Registrar Usuario"
        tk.Label(frame_header, text=titulo_texto, font=("Poppins", 16, "bold"), bg="#FFFFFF", fg="#033966").pack(side=tk.LEFT, padx=20)

        top = tk.Frame(self.frame_main, bg="#FFFFFF")
        top.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        tk.Label(top, text="UID de la tarjeta:", bg="#FFFFFF", fg="#000000", font=("Poppins", 10)).pack(anchor="w", padx=30)
        
        frame_uid = tk.Frame(top, bg="#FFFFFF")
        frame_uid.pack(fill=tk.X, padx=30, pady=5)
        
        ent_uid = tk.Entry(frame_uid, font=("Poppins", 12), bg="#FFFFFF", fg="#000000", insertbackground="#000000", highlightbackground="#CCCCCC", highlightthickness=1, relief=tk.SOLID)
        ent_uid.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        
        if uid_editar:
            ent_uid.insert(0, uid_editar)
            ent_uid.config(state="readonly")
        
        def autocompletar_uid():
            if self.vista_actual != "formulario_usuario": return
            if self.uid_escaneado_reciente:
                ent_uid.delete(0, tk.END)
                ent_uid.insert(0, self.uid_escaneado_reciente)
            top.after(500, autocompletar_uid)
            
        if not uid_editar:
            top.after(500, autocompletar_uid)
            tk.Label(top, text="💡 Pasa la tarjeta por el lector USB para auto-completar", bg="#FFFFFF", fg="#404040", font=("Poppins", 8)).pack(anchor="w", padx=30)

        tk.Label(top, text="Nombre del Empleado:", bg="#FFFFFF", fg="#000000", font=("Poppins", 10)).pack(anchor="w", padx=30, pady=(15,0))
        ent_nombre = tk.Entry(top, font=("Poppins", 12), bg="#FFFFFF", fg="#000000", insertbackground="#000000", highlightbackground="#CCCCCC", highlightthickness=1, relief=tk.SOLID)
        ent_nombre.pack(fill=tk.X, padx=30, pady=5, ipady=5)
        if nombre_editar: ent_nombre.insert(0, nombre_editar)

        tk.Label(top, text="Permisos de Áreas:", bg="#FFFFFF", fg="#000000", font=("Poppins", 10, "bold")).pack(anchor="w", padx=30, pady=(20, 5))
        
        btn_areas = tk.Button(top, text="Desplegar Áreas ▼", bg="#033966", fg="#FFFFFF", font=("Poppins", 10, "bold"), bd=0, activebackground="#0A8504", activeforeground="#FFFFFF")
        btn_areas.pack(fill=tk.X, padx=30, ipady=5)
        
        frame_areas_container = tk.Frame(top, bg="#FFFFFF")
        frame_areas_container.pack(fill=tk.BOTH, expand=False, padx=30)
        
        frame_areas = tk.Frame(frame_areas_container, bg="#F0F0F0", height=0)
        frame_areas.pack_propagate(False)
        
        var_areas = {}
        areas_actuales = [a.strip() for a in areas_editar.split(",")] if areas_editar else []
        
        for k, v in AREAS.items():
            var = tk.BooleanVar(value=(k in areas_actuales))
            var_areas[k] = var
            tk.Checkbutton(frame_areas, text=v, variable=var, bg="#F0F0F0", fg="#000000", selectcolor="#FFFFFF", activebackground="#F0F0F0", activeforeground="#000000", font=("Poppins", 10)).pack(anchor="w", pady=2, padx=10)

        target_h = len(AREAS) * 35 + 20
        btn_areas.is_open = False
        
        def toggle_areas():
            if btn_areas.is_open:
                btn_areas.is_open = False
                btn_areas.config(text="Desplegar Áreas ▼")
                self.animate_height(frame_areas, target_h, 0, -20, on_complete=lambda: frame_areas.pack_forget())
            else:
                btn_areas.is_open = True
                btn_areas.config(text="Ocultar Áreas ▲")
                frame_areas.pack(fill=tk.X)
                self.animate_height(frame_areas, 0, target_h, 20)

        btn_areas.config(command=toggle_areas)

        def guardar():
            uid, nombre = ent_uid.get().strip().upper(), ent_nombre.get().strip()
            areas_str = ",".join([k for k, v in var_areas.items() if v.get()])
            
            if not uid or not nombre: return messagebox.showerror("Error", "UID y Nombre son obligatorios.")
            if not areas_str: return messagebox.showerror("Error", "Debes seleccionar al menos un área.")

            if usuarios.registrar_usuario(uid, nombre, areas_str):
                messagebox.showinfo("Éxito", "Usuario guardado correctamente.")
                self.sincronizar_esp32_inmediato()
                self.uid_escaneado_reciente = None
                self.mostrar_vista_usuarios()
            else: messagebox.showerror("Error", "No se pudo guardar el usuario.")

        ico_save = self.cargar_icono("save", 18)
        ttk.Button(frame_header, text=" GUARDAR USUARIO", image=ico_save, compound=tk.LEFT, command=guardar).pack(side=tk.RIGHT, ipadx=10, ipady=3)

    def editar_usuario_seleccionado(self, *args):
        if not hasattr(self, 'tree_usuarios') or not self.tree_usuarios.winfo_exists(): return
        seleccion = self.tree_usuarios.selection()
        if not seleccion: return messagebox.showwarning("Aviso", "Selecciona un usuario para editar.")
        uid, nombre = self.tree_usuarios.item(seleccion[0], "values")[0:2]
        row = usuarios.buscar_usuario(uid)
        if row: 
            self.mostrar_vista_formulario_usuario(uid_editar=uid, nombre_editar=nombre, areas_editar=row[2])
        else:
            messagebox.showerror("Error", "No se encontró el usuario en la base de datos.")

    def eliminar_usuario_seleccionado(self, *args):
        if not hasattr(self, 'tree_usuarios') or not self.tree_usuarios.winfo_exists(): return
        seleccion = self.tree_usuarios.selection()
        if not seleccion: return messagebox.showwarning("Aviso", "Selecciona un usuario para eliminar.")
        uid, nombre = self.tree_usuarios.item(seleccion[0], "values")[0:2]
        
        if messagebox.askyesno("Confirmar Baja", f"¿Eliminar permanentemente a:\n{nombre} ({uid})?"):
            if usuarios.eliminar_usuario(uid):
                messagebox.showinfo("Éxito", "Usuario eliminado.")
                self.sincronizar_esp32_inmediato()
                self.cargar_tabla_usuarios()



    def on_click_tree_usuarios(self, event):
        region = self.tree_usuarios.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree_usuarios.identify_column(event.x)
            if column == "#6":
                item_id = self.tree_usuarios.identify_row(event.y)
                if item_id:
                    self.tree_usuarios.selection_set(item_id)
                    self.mostrar_menu_contextual_usuario(event.x_root, event.y_root)

    def on_right_click_tree_usuarios(self, event):
        item_id = self.tree_usuarios.identify_row(event.y)
        if item_id:
            self.tree_usuarios.selection_set(item_id)
            self.mostrar_menu_contextual_usuario(event.x_root, event.y_root)

    def mostrar_menu_contextual_usuario(self, x, y):
        menu = tk.Menu(self, tearoff=0, font=("Poppins", 10))
        ico_write = self.cargar_icono("write", 16)
        ico_alarm = self.cargar_icono("alarm", 16)
        menu.ico_write = ico_write
        menu.ico_alarm = ico_alarm
        menu.add_command(label=" Editar Usuario", image=ico_write, compound=tk.LEFT, command=self.editar_usuario_seleccionado)
        menu.add_command(label=" Eliminar Usuario", image=ico_alarm, compound=tk.LEFT, command=self.eliminar_usuario_seleccionado)
        menu.post(x, y)


    # ========================== VISTA PUERTAS ==========================
    def mostrar_vista_puertas(self):
        if getattr(self, 'vista_actual', None) == "puertas": return
        self.limpiar_vista()
        self.vista_actual = "puertas"
        self.lbl_titulo.config(text="PUERTAS")

        frame_busqueda = tk.Frame(self.frame_main, bg="#FFFFFF")
        frame_busqueda.pack(fill=tk.X, pady=10, padx=20)
        
        ico_hourglass = self.cargar_icono("hourglass", 24)
        ttk.Button(frame_busqueda, text=" Recargar", image=ico_hourglass, compound=tk.LEFT, command=self.cargar_tabla_puertas).pack(side=tk.RIGHT, padx=5)

        frame_tabla = tk.Frame(self.frame_main, bg="#FFFFFF")
        frame_tabla.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        columnas = ("mac", "nombre", "area", "tipo", "acciones")
        self.tree_puertas = ttk.Treeview(frame_tabla, columns=columnas, show="headings")
        self.tree_puertas.heading("mac", text="MAC ADDRESS")
        self.tree_puertas.heading("nombre", text="NOMBRE")
        self.tree_puertas.heading("area", text="ÁREA")
        self.tree_puertas.heading("tipo", text="TIPO")
        self.tree_puertas.heading("acciones", text="ACCIONES")
        self.tree_puertas.column("mac", width=150, anchor="center")
        self.tree_puertas.column("nombre", width=200, anchor="center")
        self.tree_puertas.column("area", width=150, anchor="center")
        self.tree_puertas.column("tipo", width=150, anchor="center")
        self.tree_puertas.column("acciones", width=120, anchor="center")
        
        self.tree_puertas.tag_configure("hover", background="#0A8504", foreground="#FFFFFF")
        
        scrollbar_x = ttk.Scrollbar(frame_tabla, orient=tk.HORIZONTAL, command=self.tree_puertas.xview)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        scrollbar = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree_puertas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_puertas.configure(yscrollcommand=scrollbar.set, xscrollcommand=scrollbar_x.set)
        
        self.tree_puertas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        


        self.tree_puertas.bind("<ButtonRelease-1>", self.on_click_tree_puertas)
        self.tree_puertas.bind("<Button-3>", self.on_right_click_tree_puertas)
        
        self.cargar_tabla_puertas()

    def cargar_tabla_puertas(self):
        if self.vista_actual != "puertas": return
        for item in self.tree_puertas.get_children(): self.tree_puertas.delete(item)
        for p in puertas.listar_puertas():
            area_nombre = AREAS.get(p[2], p[2])
            tipo_puerta = p[3] if len(p) > 3 else "Entrada"
            self.tree_puertas.insert("", tk.END, values=(p[0], p[1], area_nombre, tipo_puerta, ""))
            
        self.auto_ajustar_columnas(self.tree_puertas)

    def mostrar_vista_formulario_puerta(self, mac_editar=None, nombre_editar="", area_editar="", tipo_editar="Entrada"):
        self.limpiar_vista()
        self.vista_actual = "formulario_puerta"
        self.lbl_titulo.config(text="EDITAR PUERTA" if mac_editar else "REGISTRAR PUERTA")
        
        frame_header = tk.Frame(self.frame_main, bg="#FFFFFF")
        frame_header.pack(fill=tk.X, pady=(20, 10), padx=30)
        
        ttk.Button(frame_header, text="← Volver", command=self.mostrar_vista_puertas).pack(side=tk.LEFT)
        titulo_texto = "Editar Puerta" if mac_editar else "Registrar Puerta"
        tk.Label(frame_header, text=titulo_texto, font=("Poppins", 16, "bold"), bg="#FFFFFF", fg="#033966").pack(side=tk.LEFT, padx=20)

        top = tk.Frame(self.frame_main, bg="#FFFFFF")
        top.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tk.Label(top, text="MAC Address:", bg="#FFFFFF", fg="#000000", font=("Poppins", 10)).pack(anchor="w", padx=40)
        ent_mac = tk.Entry(top, font=("Poppins", 12), bg="#FFFFFF", fg="#000000", highlightbackground="#CCCCCC", highlightthickness=1, relief=tk.SOLID)
        ent_mac.pack(fill=tk.X, padx=40, pady=5, ipady=5)
        if mac_editar:
            ent_mac.insert(0, mac_editar)
            ent_mac.config(state="readonly")
            
        tk.Label(top, text="Nombre de Puerta:", bg="#FFFFFF", fg="#000000", font=("Poppins", 10)).pack(anchor="w", padx=40, pady=(10, 0))
        ent_nombre = tk.Entry(top, font=("Poppins", 12), bg="#FFFFFF", fg="#000000", highlightbackground="#CCCCCC", highlightthickness=1, relief=tk.SOLID)
        ent_nombre.pack(fill=tk.X, padx=40, pady=5, ipady=5)
        if nombre_editar: ent_nombre.insert(0, nombre_editar)

        tk.Label(top, text="Área:", bg="#FFFFFF", fg="#000000", font=("Poppins", 10)).pack(anchor="w", padx=40, pady=(10, 0))
        
        a_list = [f"{k} - {v}" for k,v in AREAS.items()]
        val_inicial = "Seleccionar Área"
        if area_editar:
            for val in a_list:
                # Comparamos exactamente con el nombre del área
                if len(val.split(" - ", 1)) > 1 and area_editar == val.split(" - ", 1)[1]:
                    val_inicial = val
                    break
        elif a_list:
            val_inicial = a_list[0]
            
        var_area_sel = tk.StringVar(value=val_inicial)
        
        btn_area_puerta = tk.Button(top, text=f"{val_inicial} ▼", bg="#033966", fg="#FFFFFF", font=("Poppins", 10, "bold"), bd=0, activebackground="#0A8504", activeforeground="#FFFFFF")
        btn_area_puerta.pack(fill=tk.X, padx=40, ipady=5)
        
        frame_area_container = tk.Frame(top, bg="#FFFFFF")
        frame_area_container.pack(fill=tk.BOTH, expand=False, padx=40)
        
        frame_area_puerta = tk.Frame(frame_area_container, bg="#F0F0F0", height=0)
        frame_area_puerta.pack_propagate(False)
        
        target_h_p = len(a_list) * 35 + 20
        btn_area_puerta.is_open = False
        
        def toggle_area_puerta():
            if btn_area_puerta.is_open:
                btn_area_puerta.is_open = False
                self.animate_height(frame_area_puerta, target_h_p, 0, -20, on_complete=lambda: frame_area_puerta.pack_forget())
            else:
                btn_area_puerta.is_open = True
                frame_area_puerta.pack(fill=tk.X)
                self.animate_height(frame_area_puerta, 0, target_h_p, 20)
                
        btn_area_puerta.config(command=toggle_area_puerta)
        
        def select_area(val):
            var_area_sel.set(val)
            btn_area_puerta.config(text=f"{val} ▼")
            toggle_area_puerta()
            
        for val in a_list:
            btn_opt = tk.Button(frame_area_puerta, text=val, bg="#F0F0F0", fg="#000000", bd=0, anchor="w", font=("Poppins", 10), command=lambda v=val: select_area(v))
            btn_opt.pack(fill=tk.X, padx=10, pady=2)

        tk.Label(top, text="Tipo de Acceso:", bg="#FFFFFF", fg="#000000", font=("Poppins", 10)).pack(anchor="w", padx=40, pady=(10, 0))
        
        val_inicial_tipo = tipo_editar if tipo_editar in ["Entrada", "Salida"] else "Entrada"
        var_tipo_sel = tk.StringVar(value=val_inicial_tipo)
        
        btn_tipo = tk.Button(top, text=f"{val_inicial_tipo} ▼", bg="#033966", fg="#FFFFFF", font=("Poppins", 10, "bold"), bd=0, activebackground="#0A8504", activeforeground="#FFFFFF")
        btn_tipo.pack(fill=tk.X, padx=40, ipady=5)
        
        frame_tipo_container = tk.Frame(top, bg="#FFFFFF")
        frame_tipo_container.pack(fill=tk.BOTH, expand=False, padx=40)
        
        frame_tipo = tk.Frame(frame_tipo_container, bg="#F0F0F0", height=0)
        frame_tipo.pack_propagate(False)
        
        target_h_t = 2 * 30 + 10
        btn_tipo.is_open = False
        
        def toggle_tipo():
            if btn_tipo.is_open:
                btn_tipo.is_open = False
                self.animate_height(frame_tipo, target_h_t, 0, -20, on_complete=lambda: frame_tipo.pack_forget())
            else:
                btn_tipo.is_open = True
                frame_tipo.pack(fill=tk.X)
                self.animate_height(frame_tipo, 0, target_h_t, 20)
                
        btn_tipo.config(command=toggle_tipo)
        
        def select_tipo(val):
            var_tipo_sel.set(val)
            btn_tipo.config(text=f"{val} ▼")
            toggle_tipo()
            
        for val in ["Entrada", "Salida"]:
            tk.Button(frame_tipo, text=val, bg="#F0F0F0", fg="#000000", bd=0, anchor="w", font=("Poppins", 10), command=lambda v=val: select_tipo(v)).pack(fill=tk.X, padx=10, pady=2)

        def guardar_puerta():
            mac = ent_mac.get().strip().upper()
            nombre = ent_nombre.get().strip()
            area_sel = var_area_sel.get()
            tipo_sel = var_tipo_sel.get()
            if not mac or not nombre or area_sel == "Seleccionar Área" or not tipo_sel:
                return messagebox.showerror("Error", "Todos los campos son obligatorios")
            area_id = area_sel.split(" - ")[0]

            if puertas.registrar_puerta(mac, nombre, area_id, tipo_sel):
                messagebox.showinfo("Éxito", "Puerta guardada correctamente.")
                self.mostrar_vista_puertas()
            else:
                messagebox.showerror("Error", "No se pudo guardar la puerta. ¿MAC duplicada?")

        ico_save = self.cargar_icono("save", 18)
        ttk.Button(frame_header, text=" GUARDAR PUERTA", image=ico_save, compound=tk.LEFT, command=guardar_puerta).pack(side=tk.RIGHT, ipadx=10, ipady=3)

    def editar_puerta_seleccionada(self, *args):
        if not hasattr(self, 'tree_puertas') or not self.tree_puertas.winfo_exists(): return
        sel = self.tree_puertas.selection()
        if not sel: return messagebox.showwarning("Aviso", "Selecciona una puerta para editarla.")
        values = self.tree_puertas.item(sel[0], "values")
        mac, nombre, area_nombre = values[0:3]
        tipo_puerta = values[3] if len(values) > 3 else "Entrada"
        self.mostrar_vista_formulario_puerta(mac_editar=mac, nombre_editar=nombre, area_editar=area_nombre, tipo_editar=tipo_puerta)

    def eliminar_puerta_seleccionada(self, *args):
        if not hasattr(self, 'tree_puertas') or not self.tree_puertas.winfo_exists(): return
        sel = self.tree_puertas.selection()
        if not sel: return messagebox.showwarning("Aviso", "Selecciona una puerta para eliminarla.")
        mac, nombre = self.tree_puertas.item(sel[0], "values")[0:2]
        if messagebox.askyesno("Confirmar", f"¿Eliminar la puerta '{nombre}' ({mac})?"):
            if puertas.eliminar_puerta(mac):
                messagebox.showinfo("Éxito", "Puerta eliminada correctamente.")
                self.cargar_tabla_puertas()


    def on_click_tree_puertas(self, event):
        region = self.tree_puertas.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree_puertas.identify_column(event.x)
            if column == "#5":
                item_id = self.tree_puertas.identify_row(event.y)
                if item_id:
                    self.tree_puertas.selection_set(item_id)
                    self.mostrar_menu_contextual_puerta(event.x_root, event.y_root)

    def on_right_click_tree_puertas(self, event):
        item_id = self.tree_puertas.identify_row(event.y)
        if item_id:
            self.tree_puertas.selection_set(item_id)
            self.mostrar_menu_contextual_puerta(event.x_root, event.y_root)

    def mostrar_menu_contextual_puerta(self, x, y):
        menu = tk.Menu(self, tearoff=0, font=("Poppins", 10))
        ico_write = self.cargar_icono("write", 16)
        ico_alarm = self.cargar_icono("alarm", 16)
        menu.ico_write = ico_write
        menu.ico_alarm = ico_alarm
        menu.add_command(label=" Editar Puerta", image=ico_write, compound=tk.LEFT, command=self.editar_puerta_seleccionada)
        menu.add_command(label=" Eliminar Puerta", image=ico_alarm, compound=tk.LEFT, command=self.eliminar_puerta_seleccionada)
        menu.post(x, y)

    # ========================== COMUNES ==========================
    def agregar_area_principal(self):
        from areas_manager import crear_nueva_area
        
        dlg = tk.Toplevel(self)
        dlg.title("Nueva Área")
        dlg.geometry("380x220")
        dlg.configure(bg="#FFFFFF")
        dlg.transient(self)
        dlg.grab_set()
        
        # Centrar en la ventana padre
        x = self.winfo_x() + (self.winfo_width() // 2) - (380 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (220 // 2)
        dlg.geometry(f"+{x}+{y}")
        
        # Eliminar el ícono por defecto
        try: dlg.wm_attributes("-toolwindow", True)
        except: pass
        
        lbl_titulo = tk.Label(dlg, text="Registrar Nueva Área", font=("Poppins", 14, "bold"), bg="#FFFFFF", fg="#033966")
        lbl_titulo.pack(pady=(20, 10))
        
        lbl_desc = tk.Label(dlg, text="Ingresa el nombre de la nueva área:", font=("Poppins", 10), bg="#FFFFFF", fg="#333333")
        lbl_desc.pack(pady=(0, 10))
        
        var_nombre = tk.StringVar()
        ent_nombre = tk.Entry(dlg, textvariable=var_nombre, font=("Poppins", 12), bg="#FFFFFF", fg="#000000", highlightbackground="#CCCCCC", highlightthickness=1, relief=tk.SOLID)
        ent_nombre.pack(fill=tk.X, padx=40, ipady=5)
        ent_nombre.focus()
        
        frame_btn = tk.Frame(dlg, bg="#FFFFFF")
        frame_btn.pack(pady=20)
        
        def on_guardar(*args):
            nombre = var_nombre.get().strip()
            if nombre:
                if crear_nueva_area(nombre):
                    messagebox.showinfo("Éxito", f"Área '{nombre}' agregada correctamente.", parent=self)
                    if self.vista_actual == "usuarios":
                        self.cargar_tabla_usuarios()
                    elif self.vista_actual == "puertas":
                        self.cargar_tabla_puertas()
                    dlg.destroy()
                else:
                    messagebox.showerror("Error", "No se pudo agregar el área. Puede que ya exista o hubo un error en la BD.", parent=dlg)
            else:
                messagebox.showwarning("Aviso", "El nombre no puede estar vacío.", parent=dlg)
                
        def on_cancelar():
            dlg.destroy()
            
        btn_guardar = tk.Button(frame_btn, text="Guardar", font=("Poppins", 10, "bold"), bg="#033966", fg="#FFFFFF", bd=0, activebackground="#0A8504", activeforeground="#FFFFFF", command=on_guardar)
        btn_guardar.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=6)
        
        btn_cancelar = tk.Button(frame_btn, text="Cancelar", font=("Poppins", 10, "bold"), bg="#E0E0E0", fg="#333333", bd=0, activebackground="#CCCCCC", activeforeground="#333333", command=on_cancelar)
        btn_cancelar.pack(side=tk.LEFT, padx=10, ipadx=15, ipady=6)
        
        dlg.bind("<Return>", on_guardar)
        dlg.bind("<Escape>", lambda e: on_cancelar())

    def conectar_serial(self):
        if getattr(self, 'pausar_serial', False):
            self.after(5000, self.conectar_serial)
            return
            
        if self.serial_conn and self.serial_conn.is_open:
            return
        try:
            import serial.tools.list_ports
            puerto_encontrado = PUERTO
            for p in serial.tools.list_ports.comports():
                if "CH340" in p.description or "CP210" in p.description:
                    puerto_encontrado = p.device
                    break
                    
            self.serial_conn = serial.Serial(puerto_encontrado, BAUDRATE, timeout=1)
            self.lbl_estado_serial.config(text="🟢 Lector en línea", fg="#0A8504")
            self.hilo_serial = threading.Thread(target=self.leer_serial, daemon=True)
            self.hilo_serial.start()
        except:
            self.lbl_estado_serial.config(text="🔴 Lector fuera de línea", fg="#9C0303")
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
        
        if self.running:
            if self.serial_conn:
                try: self.serial_conn.close()
                except: pass
                self.serial_conn = None
            self.lbl_estado_serial.config(text="🔴 Lector fuera de línea", fg="#9C0303")
            self.after(5000, self.conectar_serial)

    def sincronizar_esp32_inmediato(self):
        pass


    def mostrar_vista_visor(self, area_filtrar="General"):
        self.vista_actual = "visor"
        for widget in self.frame_main.winfo_children():
            if widget not in (self.frame_top, self.frame_top_sep):
                widget.destroy()

        self.lbl_titulo.config(text=f"VISOR DE ACCESOS - {area_filtrar.upper()}")

        card_stats = tk.Frame(self.frame_main, bg="#FFFFFF", bd=0, highlightbackground="#E0E0E0", highlightthickness=1)
        card_stats.pack(fill=tk.X, padx=25, pady=(15, 10))
        
        self.lbl_stats_visor = tk.Label(card_stats, text="Resumen Global: Calculando...", bg="#FFFFFF", fg="#6c757d", font=("Segoe UI", 11, "bold"))
        self.lbl_stats_visor.pack(side=tk.LEFT, padx=20, pady=15)

        card_logs = tk.Frame(self.frame_main, bg="#FFFFFF", bd=0, highlightbackground="#E0E0E0", highlightthickness=1)
        card_logs.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))

        col_logs = ("uid", "nombre", "area", "motivo", "entrada", "salida")
        self.tree_visor = ttk.Treeview(card_logs, columns=col_logs, show="headings", selectmode="none")
        self.tree_visor.heading("uid", text="UID")
        self.tree_visor.heading("nombre", text="Nombre")
        self.tree_visor.heading("area", text="Área")
        self.tree_visor.heading("motivo", text="Motivo")
        self.tree_visor.heading("entrada", text="Entrada")
        self.tree_visor.heading("salida", text="Salida")

        self.tree_visor.column("uid", width=100, anchor=tk.CENTER)
        self.tree_visor.column("nombre", width=180, anchor=tk.W)
        self.tree_visor.column("area", width=120, anchor=tk.CENTER)
        self.tree_visor.column("motivo", width=250, anchor=tk.W)
        self.tree_visor.column("entrada", width=100, anchor=tk.CENTER)
        self.tree_visor.column("salida", width=100, anchor=tk.CENTER)

        self.tree_visor.tag_configure("red", foreground="#9C0303")
        self.tree_visor.tag_configure("green", foreground="#0A8504")
        self.tree_visor.tag_configure("gray", foreground="#808080")

        scroll_y = ttk.Scrollbar(card_logs, orient=tk.VERTICAL, command=self.tree_visor.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_visor.configure(yscrollcommand=scroll_y.set)
        self.tree_visor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.area_visor_actual = area_filtrar
        self.last_visor_log_id = 0
        self.processed_logs_visor = set()
        self.permitidos_visor = 0
        self.denegados_visor = 0

        self.actualizar_logs_visor()

    def actualizar_logs_visor(self):
        if getattr(self, 'vista_actual', None) != "visor": return

        def fetch_task():
            import database, usuarios, permisos
            from config import AREAS
            conn = database.conectar_db()
            if not conn:
                self.after(2000, self.actualizar_logs_visor)
                return
            
            try:
                cur = conn.cursor()
                query = "SELECT id, uid, area, fecha, fecha_salida, tipo FROM registros_acceso ORDER BY id DESC LIMIT 100"
                cur.execute(query)
                nuevos_logs = cur.fetchall()
                nuevos_logs.reverse()

                nuevos_render = []

                for log in nuevos_logs:
                    log_id, uid, area, fecha, fecha_salida, tipo = log
                    
                    area_legible = AREAS.get(str(area), str(area))
                    
                    if self.area_visor_actual != "General" and self.area_visor_actual != area_legible:
                        continue

                    is_new = log_id not in self.processed_logs_visor
                    self.processed_logs_visor.add(log_id)

                    fecha_str = str(fecha) if fecha else ""
                    fs_str = str(fecha_salida) if fecha_salida else ""
                    ts_ent = fecha_str[11:19] if len(fecha_str) >= 19 else "--:--:--"
                    ts_sal = fs_str[11:19] if len(fs_str) >= 19 else "--:--:--"

                    row = usuarios.buscar_usuario(uid)

                    if not row:
                        if is_new: self.denegados_visor += 1
                        data = {"iid": str(log_id), "vals": (uid, "Desconocido", area_legible, "Tarjeta no registrada", ts_ent, ts_sal), "color": "red"}
                    else:
                        uid_db, nombre, areas_raw, activa = row
                        if not activa:
                            if is_new: self.denegados_visor += 1
                            data = {"iid": str(log_id), "vals": (uid, nombre, area_legible, "Tarjeta inactiva / deshabilitada", ts_ent, ts_sal), "color": "red"}
                        else:
                            area_id = None
                            for k, v in AREAS.items():
                                if v == area_legible:
                                    area_id = str(k)
                                    break
                            
                            lista_permisos = areas_raw.split(",") if areas_raw else []
                            
                            if area_id and area_id not in lista_permisos:
                                if is_new: self.denegados_visor += 1
                                data = {"iid": str(log_id), "vals": (uid, nombre, area_legible, "Usuario sin permisos para esta área", ts_ent, ts_sal), "color": "red"}
                            else:
                                if is_new: self.permitidos_visor += 1
                                data = {"iid": str(log_id), "vals": (uid, nombre, area_legible, "-", ts_ent, ts_sal), "color": "green"}
                    
                    nuevos_render.append(data)

                self.after(0, lambda: self.render_logs_visor(nuevos_render))
            except Exception as e:
                print(f"Error actualizando visor: {e}")
                self.after(2000, self.actualizar_logs_visor)
            finally:
                conn.close()

        threading.Thread(target=fetch_task, daemon=True).start()

    def render_logs_visor(self, render_data):
        if getattr(self, 'vista_actual', None) != "visor": return
        
        for data in render_data:
            iid = data["iid"]
            vals = data["vals"]
            color = data["color"]

            if self.tree_visor.exists(iid):
                self.tree_visor.item(iid, values=vals, tags=(color,))
            else:
                self.tree_visor.insert("", 0, iid=iid, values=vals, tags=(color,))

        self.lbl_stats_visor.config(text=f"Resumen {self.area_visor_actual}:  Permitidos: {self.permitidos_visor}  |  Denegados: {self.denegados_visor}")
        
        self.after(2000, self.actualizar_logs_visor)

    def mostrar_vista_flashear_esp32(self):
        # Dialogo para flashear ESP32
        import serial.tools.list_ports
        import subprocess
        import threading
        
        top = tk.Toplevel(self)
        top.title("Activar puerta")
        top.geometry("500x320")
        top.configure(bg="#F4F6F9")
        top.transient(self)
        top.grab_set()
        try:
            import os
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Imagenes", "G.ico")
            if os.path.exists(icon_path):
                top.iconbitmap(icon_path)
        except: pass

        lbl_titulo = tk.Label(top, text="Activar puerta", font=("Segoe UI", 14, "bold"), bg="#F4F6F9", fg="#1A1A1A")
        lbl_titulo.pack(pady=(25, 10))
        
        frame_controls = tk.Frame(top, bg="#F4F6F9")
        frame_controls.pack(pady=10)
        
        tk.Label(frame_controls, text="Puerto COM:", font=("Segoe UI", 10, "bold"), bg="#F4F6F9", fg="#333333").pack(side=tk.LEFT, padx=5)
        
        puertos = [port.device for port in serial.tools.list_ports.comports()]
        if not puertos: puertos = ["COM1"]
        
        var_puerto = tk.StringVar(value=puertos[0])
        cb_puertos = ttk.Combobox(frame_controls, textvariable=var_puerto, values=puertos, state="readonly", width=12)
        cb_puertos.pack(side=tk.LEFT, padx=5)
        
        btn_refresh = tk.Button(frame_controls, text="Actualizar", command=lambda: cb_puertos.config(values=[p.device for p in serial.tools.list_ports.comports()]), bg="#007BFF", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=3)
        btn_refresh.pack(side=tk.LEFT, padx=5)
        
        lbl_status = tk.Label(top, text="Listo para activar...", font=("Segoe UI", 11), bg="#F4F6F9", fg="#6c757d")
        lbl_status.pack(pady=(30, 5))
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(top, variable=progress_var, maximum=100, length=350, mode="determinate")
        progress_bar.pack(pady=5)
        
        def ejecutar_flash():
            puerto = var_puerto.get()
            if not puerto:
                messagebox.showerror("Error", "Seleccione un puerto COM")
                return
            
            btn_flash.config(state=tk.DISABLED)
            lbl_status.config(text=f"Liberando puerto...", fg="#007BFF")
            progress_bar.config(mode="indeterminate")
            progress_bar.start(15)
            
            # Pausar la lectura serial global para liberar el puerto COM
            self.pausar_serial = True
            if hasattr(self, 'serial_conn') and self.serial_conn:
                try:
                    self.serial_conn.close()
                except: pass
                self.serial_conn = None
            
            def thread_task():
                import os
                import sys
                import io
                import re
                
                # Para funcionar correctamente tanto en script Python como en .exe de PyInstaller
                if getattr(sys, 'frozen', False):
                    base_path = os.path.dirname(sys.executable)
                else:
                    base_path = os.path.dirname(os.path.abspath(__file__))
                    
                firmware_dir = os.path.join(base_path, "firmware")
                bootloader = os.path.join(firmware_dir, "bootloader.bin")
                partition = os.path.join(firmware_dir, "partition-table.bin")
                app_bin = os.path.join(firmware_dir, "csproject.bin")
                
                if not (os.path.exists(bootloader) and os.path.exists(partition) and os.path.exists(app_bin)):
                    top.after(0, lambda: lbl_status.config(text="Error: Faltan archivos .bin", fg="#9C0303"))
                    top.after(0, lambda: btn_flash.config(state=tk.NORMAL))
                    return
                
                top.after(0, lambda: lbl_status.config(text="Conectando con el lector..."))
                
                class FlashMonitor(io.StringIO):
                    def __init__(self, lbl, p_var, root, p_bar):
                        super().__init__()
                        self.lbl = lbl
                        self.p_var = p_var
                        self.root = root
                        self.p_bar = p_bar
                        self.full_log = ""
                        self.line_buf = ""
                    def write(self, string):
                        self.full_log += string
                        self.line_buf += string
                        
                        if '\r' in self.line_buf or '\n' in self.line_buf:
                            match = re.search(r"\((\d+)\s*%\)", self.line_buf)
                            if match:
                                val = int(match.group(1))
                                self.root.after(0, lambda v=val: self.p_var.set(v))
                                
                            if "Erasing flash" in self.line_buf:
                                self.root.after(0, lambda: self.lbl.config(text="Borrando memoria interna..."))
                            elif "Writing at" in self.line_buf:
                                self.root.after(0, lambda: self.lbl.config(text="Instalando sistema RFID..."))
                                def stop_anim():
                                    if str(self.p_bar.cget("mode")) == "indeterminate":
                                        self.p_bar.stop()
                                        self.p_bar.config(mode="determinate")
                                self.root.after(0, stop_anim)
                            elif "Verifying" in self.line_buf:
                                self.root.after(0, lambda: self.lbl.config(text="Verificando instalación..."))
                                self.root.after(0, lambda: self.p_var.set(100))
                            elif "Hard resetting" in self.line_buf:
                                self.root.after(0, lambda: self.lbl.config(text="Reiniciando lector..."))
                                self.root.after(0, lambda: self.p_var.set(100))
                                
                            parts = self.line_buf.replace('\r', '\n').split('\n')
                            self.line_buf = parts[-1]
                            
                        return len(string)
                    def flush(self):
                        pass

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                redirector = FlashMonitor(lbl_status, progress_var, top, progress_bar)
                sys.stdout = redirector
                sys.stderr = redirector
                
                try:
                    import esptool  # type: ignore
                    cmd = [
                        "--port", puerto,
                        "--baud", "460800",
                        "--before", "default_reset",
                        "--after", "hard_reset",
                        "--chip", "esp32",
                        "write_flash",
                        "--flash_mode", "dio",
                        "--flash_size", "2MB",
                        "--flash_freq", "40m",
                        "0x1000", bootloader,
                        "0x8000", partition,
                        "0x10000", app_bin
                    ]
                    esptool.main(cmd)
                    
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    top.after(0, lambda: lbl_status.config(text="¡Lector Activado Exitosamente!", fg="#28A745"))
                    self.after(500, lambda: self.mostrar_registro_puerta_post_flash(top, redirector.full_log))
                    
                except SystemExit as e:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    top.after(0, lambda: progress_bar.stop())
                    if e.code == 0 or e.code is None:
                        top.after(0, lambda: lbl_status.config(text="¡Lector Activado Exitosamente!", fg="#28A745"))
                        self.after(500, lambda: self.mostrar_registro_puerta_post_flash(top, redirector.full_log))
                    else:
                        top.after(0, lambda: lbl_status.config(text=f"Error de activación (Código {e.code})", fg="#9C0303"))
                        messagebox.showerror("Error", "Ocurrió un problema al activar el lector.", parent=top)
                except Exception as e:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    top.after(0, lambda: progress_bar.stop())
                    top.after(0, lambda: lbl_status.config(text=f"Fallo de ejecución", fg="#9C0303"))
                    messagebox.showerror("Error", f"Error inesperado:\n{e}", parent=top)
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    btn_flash.config(state=tk.NORMAL)
                    self.pausar_serial = False
                    
            threading.Thread(target=thread_task, daemon=True).start()
            
        btn_flash = tk.Button(top, text="Activar puerta", bg="#28A745", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=20, pady=10, command=ejecutar_flash)
        btn_flash.pack(pady=(0, 20))

    def mostrar_registro_puerta_post_flash(self, top_flasheo, console_text):
        import re
        from config import AREAS
        
        # Buscar MAC en el log de esptool
        mac_match = re.search(r"MAC:\s*(([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})", console_text)
        mac_detectada = mac_match.group(1).upper() if mac_match else ""
        
        # Cerrar el modal de flasheo
        try: top_flasheo.destroy()
        except: pass
        
        if not mac_detectada:
            messagebox.showwarning("Advertencia", "Flasheo exitoso pero no se pudo detectar la dirección MAC en los logs.\nDeberás registrar la puerta manualmente desde el menú 'Puertas -> Agregar'.")
            return
            
        # Modal de registro
        dlg = tk.Toplevel(self)
        dlg.title("Completar Activación")
        dlg.geometry("450x450")
        dlg.configure(bg="#F4F6F9")
        dlg.transient(self)
        dlg.grab_set()
        
        tk.Label(dlg, text="Lector Activado Exitosamente", font=("Segoe UI", 14, "bold"), bg="#F4F6F9", fg="#007BFF").pack(pady=(20, 5))
        tk.Label(dlg, text=f"MAC Detectada: {mac_detectada}", font=("Segoe UI", 10, "bold"), bg="#F4F6F9", fg="#28A745").pack(pady=(0, 20))
        
        f_campos = tk.Frame(dlg, bg="#F4F6F9")
        f_campos.pack(fill=tk.BOTH, expand=True, padx=40)
        
        tk.Label(f_campos, text="Nombre para esta puerta:", bg="#F4F6F9", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 2))
        e_nombre = ttk.Entry(f_campos, font=("Segoe UI", 10))
        e_nombre.pack(fill=tk.X)
        
        f_area_radios = tk.Frame(f_campos, bg="#F4F6F9")
        f_area_radios.pack(fill=tk.X, pady=(15, 5))
        
        var_modo_area = tk.StringVar(value="existente")
        def on_modo_area_change():
            if var_modo_area.get() == "existente":
                e_nueva_area.pack_forget()
                cb_area.pack(fill=tk.X)
            else:
                cb_area.pack_forget()
                e_nueva_area.pack(fill=tk.X)
                e_nueva_area.focus()
                
        rb_existente = tk.Radiobutton(f_area_radios, text="Seleccionar área existente", variable=var_modo_area, value="existente", bg="#F4F6F9", font=("Segoe UI", 9, "bold"), command=on_modo_area_change)
        rb_existente.pack(side=tk.LEFT, padx=(0, 10))
        
        rb_nueva = tk.Radiobutton(f_area_radios, text="Nueva Área", variable=var_modo_area, value="nueva", bg="#F4F6F9", font=("Segoe UI", 9, "bold"), fg="#007BFF", command=on_modo_area_change)
        rb_nueva.pack(side=tk.LEFT)
        
        f_area_input = tk.Frame(f_campos, bg="#F4F6F9")
        f_area_input.pack(fill=tk.X)
        
        var_area = tk.StringVar()
        cb_area = ttk.Combobox(f_area_input, textvariable=var_area, state="readonly", font=("Segoe UI", 10))
        cb_area.pack(fill=tk.X)
        
        var_nueva_area = tk.StringVar()
        e_nueva_area = ttk.Entry(f_area_input, textvariable=var_nueva_area, font=("Segoe UI", 10))
        
        def actualizar_opciones_area():
            import config
            opciones = [f"{k} - {v}" for k, v in config.AREAS.items()]
            cb_area.config(values=opciones)
            
            curr = var_area.get()
            if curr not in opciones:
                if opciones:
                    var_area.set(opciones[-1])
                    
        actualizar_opciones_area()
        dlg.bind("<FocusIn>", lambda e: actualizar_opciones_area())
        
        tk.Label(f_campos, text="Tipo de puerta:", bg="#F4F6F9", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15, 2))
        var_tipo = tk.StringVar(value="Entrada")
        cb_tipo = ttk.Combobox(f_campos, textvariable=var_tipo, values=["Entrada", "Salida", "Ambos"], state="readonly", font=("Segoe UI", 10))
        cb_tipo.pack(fill=tk.X)
        
        def guardar_puerta():
            nombre = e_nombre.get().strip()
            if not nombre:
                messagebox.showerror("Error", "Debes ingresar un nombre para la puerta", parent=dlg)
                return
                
            if var_modo_area.get() == "nueva":
                nombre_nueva = var_nueva_area.get().strip()
                if not nombre_nueva:
                    messagebox.showerror("Error", "Debes ingresar un nombre para la nueva área", parent=dlg)
                    return
                    
                from areas_manager import crear_nueva_area
                if not crear_nueva_area(nombre_nueva):
                    messagebox.showerror("Error", "No se pudo agregar la nueva área. Puede que ya exista.", parent=dlg)
                    return
                    
                import config
                area_id = None
                for k, v in config.AREAS.items():
                    if v == nombre_nueva:
                        area_id = str(k)
                        break
                        
                if not area_id:
                    messagebox.showerror("Error", "Error obteniendo el ID de la nueva área.", parent=dlg)
                    return
            else:
                area_str = var_area.get()
                area_id = area_str.split(" - ")[0] if " - " in area_str else ""
            
            tipo = var_tipo.get()
            
            import puertas
            ok = puertas.registrar_puerta(mac_detectada, nombre, area_id, tipo)
            if ok:
                messagebox.showinfo("Éxito", f"La puerta '{nombre}' se registró correctamente en el sistema.", parent=dlg)
                dlg.destroy()
                if self.vista_actual == "puertas":
                    self.mostrar_vista_puertas() # Recargar la vista si estamos ahí
            else:
                messagebox.showerror("Error", "Hubo un error al guardar la puerta en la base de datos.", parent=dlg)
                
        f_btns = tk.Frame(dlg, bg="#F4F6F9")
        f_btns.pack(pady=25)
        
        tk.Button(f_btns, text="Guardar y Finalizar", bg="#007BFF", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=8, command=guardar_puerta).pack(side=tk.LEFT, padx=10)
        tk.Button(f_btns, text="Cancelar", bg="#6c757d", fg="white", font=("Segoe UI", 10), bd=0, padx=15, pady=8, command=dlg.destroy).pack(side=tk.LEFT, padx=10)


    def mostrar_vista_formatear_esp32(self):
        import serial.tools.list_ports
        import threading
        
        top = tk.Toplevel(self)
        top.title("Desactivar puerta")
        top.geometry("500x320")
        top.configure(bg="#F4F6F9")
        top.transient(self)
        top.grab_set()
        try:
            import os
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Imagenes", "G.ico")
            if os.path.exists(icon_path):
                top.iconbitmap(icon_path)
        except: pass

        lbl_titulo = tk.Label(top, text="Desactivar puerta", font=("Segoe UI", 14, "bold"), bg="#F4F6F9", fg="#9C0303")
        lbl_titulo.pack(pady=(25, 10))
        
        frame_controls = tk.Frame(top, bg="#F4F6F9")
        frame_controls.pack(pady=10)
        
        tk.Label(frame_controls, text="Puerto COM:", font=("Segoe UI", 10, "bold"), bg="#F4F6F9", fg="#333333").pack(side=tk.LEFT, padx=5)
        
        puertos = [port.device for port in serial.tools.list_ports.comports()]
        if not puertos: puertos = ["COM1"]
        
        var_puerto = tk.StringVar(value=puertos[0])
        cb_puertos = ttk.Combobox(frame_controls, textvariable=var_puerto, values=puertos, state="readonly", width=12)
        cb_puertos.pack(side=tk.LEFT, padx=5)
        
        btn_refresh = tk.Button(frame_controls, text="Actualizar", command=lambda: cb_puertos.config(values=[p.device for p in serial.tools.list_ports.comports()]), bg="#007BFF", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=3)
        btn_refresh.pack(side=tk.LEFT, padx=5)
        
        lbl_status = tk.Label(top, text="Listo para formatear...", font=("Segoe UI", 11), bg="#F4F6F9", fg="#6c757d")
        lbl_status.pack(pady=(30, 5))
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(top, variable=progress_var, maximum=100, length=350, mode="determinate")
        progress_bar.pack(pady=5)
        
        def ejecutar_formateo():
            puerto = var_puerto.get()
            if not puerto:
                from tkinter import messagebox
                messagebox.showerror("Error", "Seleccione un puerto COM", parent=top)
                return
            
            btn_format.config(state=tk.DISABLED)
            lbl_status.config(text=f"Liberando puerto...", fg="#007BFF")
            progress_bar.config(mode="indeterminate")
            progress_bar.start(15)
            
            self.pausar_serial = True
            if hasattr(self, 'serial_conn') and self.serial_conn:
                try:
                    self.serial_conn.close()
                except: pass
                self.serial_conn = None
            
            def thread_task():
                import sys
                import io
                import re
                from tkinter import messagebox
                import puertas
                
                top.after(0, lambda: lbl_status.config(text="Conectando y borrando memoria..."))
                
                class FlashMonitor(io.StringIO):
                    def __init__(self, lbl, p_var, root, p_bar):
                        super().__init__()
                        self.lbl = lbl
                        self.p_var = p_var
                        self.root = root
                        self.p_bar = p_bar
                        self.full_log = ""
                        self.line_buf = ""
                    def write(self, string):
                        self.full_log += string
                        self.line_buf += string
                        if '\r' in self.line_buf or '\n' in self.line_buf:
                            if "Erasing" in self.line_buf:
                                self.root.after(0, lambda: self.lbl.config(text="Borrando chip, espera..."))
                            parts = self.line_buf.replace('\r', '\n').split('\n')
                            self.line_buf = parts[-1]
                        return len(string)
                    def flush(self): pass

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                redirector = FlashMonitor(lbl_status, progress_var, top, progress_bar)
                sys.stdout = redirector
                sys.stderr = redirector
                
                try:
                    import esptool  # type: ignore
                    cmd = ["--port", puerto, "--baud", "460800", "erase_flash"]
                    esptool.main(cmd)
                    
                    # Si llega aquí sin SystemExit, significa que fue exitoso
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    top.after(0, lambda: progress_bar.stop())
                    top.after(0, lambda: progress_bar.config(mode="determinate"))
                    top.after(0, lambda: progress_var.set(100))
                    
                    mac_match = re.search(r"MAC:\s*([0-9a-fA-F:]+)", redirector.full_log)
                    if mac_match:
                        mac_erased = mac_match.group(1).upper()
                        puertas.eliminar_puerta(mac_erased)
                        top.after(0, lambda: lbl_status.config(text=f"Formateado! MAC: {mac_erased}", fg="#28A745"))
                        if self.vista_actual == "puertas":
                            top.after(0, self.mostrar_vista_puertas)
                            
                        def on_success():
                            messagebox.showinfo("Lector Desactivado", f"El lector ha sido formateado exitosamente.\\n\\nLa puerta con MAC {mac_erased} fue eliminada del sistema.", parent=top)
                            top.destroy()
                        top.after(500, on_success)
                    else:
                        top.after(0, lambda: lbl_status.config(text="Formateado! (MAC no leída)", fg="#28A745"))
                        def on_success_no_mac():
                            messagebox.showwarning("Lector Desactivado", "El lector ha sido formateado exitosamente, pero no se detectó su dirección MAC en los logs para eliminarlo automáticamente de la base de datos.", parent=top)
                            top.destroy()
                        top.after(500, on_success_no_mac)
                        
                except SystemExit as e:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    top.after(0, lambda: progress_bar.stop())
                    if e.code == 0 or e.code is None:
                        top.after(0, lambda: progress_bar.config(mode="determinate"))
                        top.after(0, lambda: progress_var.set(100))
                        
                        mac_match = re.search(r"MAC:\s*([0-9a-fA-F:]+)", redirector.full_log)
                        if mac_match:
                            mac_erased = mac_match.group(1).upper()
                            puertas.eliminar_puerta(mac_erased)
                            top.after(0, lambda: lbl_status.config(text=f"Formateado! MAC: {mac_erased}", fg="#28A745"))
                            if self.vista_actual == "puertas":
                                top.after(0, self.mostrar_vista_puertas)
                                
                            def on_success2():
                                messagebox.showinfo("Lector Desactivado", f"El lector ha sido formateado exitosamente.\\n\\nLa puerta con MAC {mac_erased} fue eliminada del sistema.", parent=top)
                                top.destroy()
                            top.after(500, on_success2)
                        else:
                            top.after(0, lambda: lbl_status.config(text="Formateado! (MAC no leída)", fg="#28A745"))
                            def on_success_no_mac2():
                                messagebox.showwarning("Lector Desactivado", "El lector ha sido formateado exitosamente, pero no se detectó su dirección MAC en los logs para eliminarlo automáticamente de la base de datos.", parent=top)
                                top.destroy()
                            top.after(500, on_success_no_mac2)
                except Exception as e:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    top.after(0, lambda: progress_bar.stop())
                    top.after(0, lambda: lbl_status.config(text=f"Fallo de formateo", fg="#9C0303"))
                finally:
                    self.pausar_serial = False
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    top.after(0, lambda: btn_format.config(state=tk.NORMAL))
                    
            import threading
            threading.Thread(target=thread_task, daemon=True).start()
            
        btn_format = tk.Button(top, text="Desactivar puerta", bg="#9C0303", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=20, pady=10, command=ejecutar_formateo)
        btn_format.pack(pady=(0, 20))

    def destroy(self):


        self.running = False
        if self.serial_conn and self.serial_conn.is_open: 
            try: self.serial_conn.close()
            except: pass
        super().destroy()
