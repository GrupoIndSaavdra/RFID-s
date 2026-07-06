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
                         font=("Segoe UI", "9", "normal"))
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
        self.title("Sistema RFID - Panel de Administración")
        self.geometry("950x700")
        
        # Tema Claro Corporativo Industrial Saavedra
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except: pass
            
        style.configure("TFrame", background="#FFFFFF")
        style.configure("Sidebar.TFrame", background="#033966")
        style.configure("TLabel", background="#FFFFFF", foreground="#000000", font=("Segoe UI", 11))
        style.configure("Sidebar.TLabel", background="#033966", foreground="#FFFFFF", font=("Segoe UI", 12, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#033966", background="#F0F0F0")
        
        style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#033966", foreground="#FFFFFF", padding=6)
        style.map("TButton", background=[("active", "#0A8504")])
        
        style.configure("Menu.TButton", font=("Segoe UI", 11, "bold"), background="#033966", foreground="#FFFFFF", borderwidth=0)
        style.map("Menu.TButton", background=[("active", "#0A8504")])
        
        style.configure("SubMenu.TButton", font=("Segoe UI", 10), background="#022240", foreground="#DDDDDD", borderwidth=0)
        style.map("SubMenu.TButton", background=[("active", "#0A8504")], foreground=[("active", "#FFFFFF")])
        
        style.configure("Treeview", background="#FFFFFF", foreground="#000000", rowheight=40, fieldbackground="#FFFFFF", borderwidth=1)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#404040", foreground="#FFFFFF")
        style.map("Treeview", background=[("selected", "#033966")], foreground=[("selected", "#FFFFFF")])

        self.configure(bg="#F0F0F0")
        self.running = True
        self.serial_conn = None
        self.uid_escaneado_reciente = None
        self.menu_visible = True
        self.submenu_usuarios_visible = False
        self.submenu_puertas_visible = False
        
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
            "buscar": os.path.join(base_dir, "Imagenes", "Buscar.png")
        }
        self.iconos = {}
        
        self.crear_interfaz_principal()
        self.conectar_serial()
        self.mantener_frame_acciones()

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
        font = tkfont.Font(family="Segoe UI", size=10)
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
                btn_edit = tk.Button(f, image=self.cargar_icono("write", 30), bg="#FFFFFF", bd=0, activebackground="#F0F0F0", cursor="hand2")
                btn_edit.pack(side=tk.LEFT, expand=True, pady=2)
                ToolTip(btn_edit, "Editar Usuario")
                
                btn_del = tk.Button(f, image=self.cargar_icono("alarm", 30), bg="#FFFFFF", bd=0, activebackground="#F0F0F0", cursor="hand2")
                btn_del.pack(side=tk.LEFT, expand=True, pady=2)
                ToolTip(btn_del, "Eliminar Usuario")

                def on_enter_btn(e): e.widget['background'] = '#F0F0F0'
                def on_leave_btn(e): e.widget['background'] = '#FFFFFF'
                btn_edit.bind("<Enter>", on_enter_btn)
                btn_edit.bind("<Leave>", on_leave_btn)
                btn_del.bind("<Enter>", on_enter_btn)
                btn_del.bind("<Leave>", on_leave_btn)
                
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
                btn_edit = tk.Button(f, image=self.cargar_icono("write", 30), bg="#FFFFFF", bd=0, activebackground="#F0F0F0", cursor="hand2")
                btn_edit.pack(side=tk.LEFT, expand=True, pady=2)
                ToolTip(btn_edit, "Editar Puerta")
                
                btn_del = tk.Button(f, image=self.cargar_icono("alarm", 30), bg="#FFFFFF", bd=0, activebackground="#F0F0F0", cursor="hand2")
                btn_del.pack(side=tk.LEFT, expand=True, pady=2)
                ToolTip(btn_del, "Eliminar Puerta")

                def on_enter_btn(e): e.widget['background'] = '#F0F0F0'
                def on_leave_btn(e): e.widget['background'] = '#FFFFFF'
                btn_edit.bind("<Enter>", on_enter_btn)
                btn_edit.bind("<Leave>", on_leave_btn)
                btn_del.bind("<Enter>", on_enter_btn)
                btn_del.bind("<Leave>", on_leave_btn)
                
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

        # 3. Ocultar todos los frames que existen
        if hasattr(self, 'pool_frames_u'):
            for f in self.pool_frames_u: 
                if f.winfo_exists():
                    f.place_forget()
                    if hasattr(f, 'last_place'): delattr(f, 'last_place')
        if hasattr(self, 'pool_frames_p'):
            for f in self.pool_frames_p: 
                if f.winfo_exists():
                    f.place_forget()
                    if hasattr(f, 'last_place'): delattr(f, 'last_place')
        
        # 4. Mostrar solo en celdas visibles
        try:
            if self.vista_actual == "usuarios" and hasattr(self, 'tree_usuarios') and hasattr(self, 'pool_frames_u') and self.tree_usuarios.winfo_exists():
                idx = 0
                for item in self.tree_usuarios.get_children():
                    bbox = self.tree_usuarios.bbox(item, "acciones")
                    if bbox and idx < len(self.pool_frames_u):
                        x, y, w, h = bbox
                        f = self.pool_frames_u[idx]
                        if f.winfo_exists():
                            f.item_id = item
                            if getattr(f, 'last_place', None) != (x, y, w, h):
                                f.place(x=x, y=y, width=w, height=h)
                                f.last_place = (x, y, w, h)
                            idx += 1
                        
            elif self.vista_actual == "puertas" and hasattr(self, 'tree_puertas') and hasattr(self, 'pool_frames_p') and self.tree_puertas.winfo_exists():
                idx = 0
                for item in self.tree_puertas.get_children():
                    bbox = self.tree_puertas.bbox(item, "acciones")
                    if bbox and idx < len(self.pool_frames_p):
                        x, y, w, h = bbox
                        f = self.pool_frames_p[idx]
                        if f.winfo_exists():
                            f.item_id = item
                            if getattr(f, 'last_place', None) != (x, y, w, h):
                                f.place(x=x, y=y, width=w, height=h)
                                f.last_place = (x, y, w, h)
                            idx += 1
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
        # Top Bar
        frame_top = tk.Frame(self, bg="#F0F0F0", height=50)
        frame_top.pack(fill=tk.X, side=tk.TOP)
        frame_top.pack_propagate(False)
        
        ico_menu = self.cargar_icono("menu", 28)
        btn_hamburguesa = tk.Button(frame_top, image=ico_menu if ico_menu else None, text="☰" if not ico_menu else "", font=("Segoe UI", 18), bg="#F0F0F0", fg="#033966", bd=0, activebackground="#E0E0E0", command=self.toggle_menu)
        btn_hamburguesa.pack(side=tk.LEFT, padx=10, pady=5)
        
        ico_logo = self.cargar_logo("logo", 35)
        if ico_logo:
            tk.Label(frame_top, image=ico_logo, bg="#F0F0F0").pack(side=tk.LEFT, padx=(10, 5))
        
        # Titulo superior
        self.lbl_titulo = tk.Label(frame_top, text="INICIO", bg="#F0F0F0", fg="#033966", font=("Segoe UI", 16, "bold"))
        self.lbl_titulo.pack(side=tk.LEFT, padx=20)
        
        self.lbl_estado_serial = tk.Label(frame_top, text="USB Lector: Buscando...", fg="#404040", bg="#F0F0F0", font=("Segoe UI", 10, "bold"))
        self.lbl_estado_serial.pack(side=tk.RIGHT, padx=20)
        
        # Body Frame (Sidebar + Main Content)
        frame_body = tk.Frame(self, bg="#FFFFFF")
        frame_body.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar
        self.frame_sidebar = tk.Frame(frame_body, bg="#033966", width=0)
        self.frame_sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.frame_sidebar.pack_propagate(False)
        self.menu_visible = False
        
        self.construir_sidebar()
        
        self.bind_all("<Motion>", self._check_sidebar_close)
        
        # Main Content
        self.frame_main = tk.Frame(frame_body, bg="#FFFFFF")
        self.frame_main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.vista_actual = None
        self.mostrar_vista_bienvenida() # Vista por defecto

    def construir_sidebar(self):
        for widget in self.frame_sidebar.winfo_children():
            widget.destroy()
            
        ttk.Label(self.frame_sidebar, text="Menú", style="Sidebar.TLabel").pack(pady=20)
        
        # Botón principal Usuarios
        self.btn_main_usuarios = ttk.Button(self.frame_sidebar, text="👥 Usuarios", style="Menu.TButton", command=self.toggle_submenu_usuarios)
        self.btn_main_usuarios.pack(fill=tk.X, padx=10, pady=5)
        
        # Contenedor del submenú de usuarios (con altura animable)
        self.frame_sub_usuarios = tk.Frame(self.frame_sidebar, bg="#033966", height=0)
        # Se oculta inicialmente
        self.frame_sub_usuarios.pack_propagate(False)
        
        ico_accept = self.cargar_icono("accept", 18)
        ico_write = self.cargar_icono("write", 18)
        ico_alarm = self.cargar_icono("alarm", 18)
        
        ttk.Button(self.frame_sub_usuarios, text=" Registrar", image=ico_accept, compound=tk.LEFT, style="SubMenu.TButton", command=self.mostrar_vista_formulario_usuario).pack(fill=tk.X, pady=2)

        # Botón principal Puertas
        self.btn_main_puertas = ttk.Button(self.frame_sidebar, text="🚪 Puertas", style="Menu.TButton", command=self.toggle_submenu_puertas)
        self.btn_main_puertas.pack(fill=tk.X, padx=10, pady=5)
        
        # Contenedor del submenú de puertas
        self.frame_sub_puertas = tk.Frame(self.frame_sidebar, bg="#033966", height=0)
        # Se oculta inicialmente
        self.frame_sub_puertas.pack_propagate(False)
        
        ttk.Button(self.frame_sub_puertas, text=" Agregar", image=ico_accept, compound=tk.LEFT, style="SubMenu.TButton", command=self.mostrar_vista_formulario_puerta).pack(fill=tk.X, pady=2)
            
        ttk.Button(self.frame_sidebar, text=" Agregar Área", image=ico_accept, compound=tk.LEFT, style="Menu.TButton", command=self.agregar_area_principal).pack(fill=tk.X, padx=10, pady=20)

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
            self.animate_height(self.frame_sub_usuarios, 0, target_h, 20)
            if getattr(self, 'submenu_puertas_visible', False):
                self.submenu_puertas_visible = False
                self.animate_height(self.frame_sub_puertas, target_h, 0, -20, on_complete=lambda: self.frame_sub_puertas.pack_forget())
        else:
            self.animate_height(self.frame_sub_usuarios, target_h, 0, -20, on_complete=lambda: self.frame_sub_usuarios.pack_forget())
            
    def toggle_submenu_puertas(self):
        if self.vista_actual != "puertas":
            self.mostrar_vista_puertas()
            
        self.submenu_puertas_visible = not getattr(self, 'submenu_puertas_visible', False)
        
        target_h = 40
        if self.submenu_puertas_visible:
            self.frame_sub_puertas.pack(fill=tk.X, padx=10, after=self.btn_main_puertas)
            self.animate_height(self.frame_sub_puertas, 0, target_h, 20)
            if getattr(self, 'submenu_usuarios_visible', False):
                self.submenu_usuarios_visible = False
                self.animate_height(self.frame_sub_usuarios, target_h, 0, -20, on_complete=lambda: self.frame_sub_usuarios.pack_forget())
        else:
            self.animate_height(self.frame_sub_puertas, target_h, 0, -20, on_complete=lambda: self.frame_sub_puertas.pack_forget())

    def toggle_menu(self):
        if not hasattr(self, 'animating_menu'):
            self.animating_menu = False
        if self.animating_menu:
            return
            
        self.animating_menu = True
        
        def animate(current_width, target_width, step):
            if current_width != target_width:
                current_width += step
                if (step > 0 and current_width > target_width) or (step < 0 and current_width < target_width):
                    current_width = target_width
                self.frame_sidebar.config(width=current_width)
                self.after(5, animate, current_width, target_width, step)
            else:
                self.animating_menu = False
                if target_width == 0:
                    self.menu_visible = False
                else:
                    self.menu_visible = True

        if self.menu_visible:
            animate(200, 0, -50)
        else:
            animate(0, 200, 50)

    def _check_sidebar_close(self, event):
        if not self.menu_visible: return
        x = self.frame_sidebar.winfo_rootx()
        if event.x_root > 200:
            self.toggle_menu()

    def limpiar_vista(self):
        for widget in self.frame_main.winfo_children():
            widget.destroy()
            
        img_fondo = self.cargar_imagen_original("fondo_usuarios")
        if img_fondo:
            lbl_fondo = tk.Label(self.frame_main, image=img_fondo, bg="#F0F0F0")
            lbl_fondo.place(x=0, y=0, relwidth=1, relheight=1)
            lbl_fondo.lower()

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
            lbl_titulo = tk.Label(frame_bienvenida, text="Bienvenido al Panel de Administración RFID", font=("Segoe UI", 24, "bold"), fg="#033966", bg="#FFFFFF")
            lbl_titulo.pack(pady=(200, 20))
            lbl_subtitulo = tk.Label(frame_bienvenida, text="Seleccione una opción del menú lateral izquierdo para comenzar.", font=("Segoe UI", 14), fg="#404040", bg="#FFFFFF")
            lbl_subtitulo.pack(pady=10)

    # ========================== VISTA USUARIOS ==========================
    def mostrar_vista_usuarios(self):
        self.limpiar_vista()
        self.vista_actual = "usuarios"
        self.lbl_titulo.config(text="USUARIOS")
        
        # Barra de búsqueda y filtrado
        frame_busqueda = tk.Frame(self.frame_main, bg="#FFFFFF")
        frame_busqueda.pack(fill=tk.X, pady=10, padx=20)
        
        ico_buscar = self.cargar_icono("buscar", 16)
        tk.Label(frame_busqueda, text=" Buscar:", image=ico_buscar if ico_buscar else None, compound=tk.LEFT, bg="#FFFFFF", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        
        self.var_busqueda = tk.StringVar()
        self.var_busqueda.trace("w", lambda name, index, mode: self.cargar_tabla_usuarios())
        ent_busqueda = ttk.Entry(frame_busqueda, textvariable=self.var_busqueda, font=("Segoe UI", 10), width=30)
        ent_busqueda.pack(side=tk.LEFT, padx=5)
        
        tk.Label(frame_busqueda, text="Filtrar por Área:", bg="#FFFFFF", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(20, 5))
        
        a_list = ["Todas"] + [f"{k} - {v}" for k,v in AREAS.items()]
        self.var_area_filtro = tk.StringVar(value="Todas")
        
        btn_filtro = tk.Button(frame_busqueda, text="Todas ▼", bg="#033966", fg="#FFFFFF", font=("Segoe UI", 10, "bold"), bd=0, activebackground="#0A8504", activeforeground="#FFFFFF")
        btn_filtro.pack(side=tk.LEFT, padx=5, ipady=3, ipadx=10)
        
        ico_hourglass = self.cargar_icono("hourglass", 24)
        ttk.Button(frame_busqueda, text=" Recargar", image=ico_hourglass, compound=tk.LEFT, command=self.cargar_tabla_usuarios).pack(side=tk.RIGHT, padx=5)

        frame_filtro_container = tk.Frame(self.frame_main, bg="#FFFFFF")
        frame_filtro_container.pack(fill=tk.X, padx=20)
        
        frame_filtro = tk.Frame(frame_filtro_container, bg="#F0F0F0", height=0)
        frame_filtro.pack_propagate(False)
        
        target_h_f = len(a_list) * 28 + 10
        btn_filtro.is_open = False
        
        def toggle_filtro():
            if btn_filtro.is_open:
                btn_filtro.is_open = False
                self.animate_height(frame_filtro, target_h_f, 0, -20, on_complete=lambda: frame_filtro.pack_forget())
            else:
                btn_filtro.is_open = True
                # Lo ponemos cerca de la barra
                frame_filtro.pack(fill=tk.X, padx=(420, 150)) 
                self.animate_height(frame_filtro, 0, target_h_f, 20)
                
        btn_filtro.config(command=toggle_filtro)
        
        def select_filtro(val):
            self.var_area_filtro.set(val)
            btn_filtro.config(text=f"{val.split(' - ')[0]} ▼")
            toggle_filtro()
            self.cargar_tabla_usuarios()
            
        for val in a_list:
            tk.Button(frame_filtro, text=val, bg="#F0F0F0", fg="#000000", bd=0, anchor="w", font=("Segoe UI", 10), command=lambda v=val: select_filtro(v)).pack(fill=tk.X, padx=10, pady=2)

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

        scrollbar = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree_usuarios.yview)
        self.tree_usuarios.configure(yscroll=scrollbar.set)
        
        self.tree_usuarios.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        


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
        tk.Label(frame_header, text=titulo_texto, font=("Segoe UI", 16, "bold"), bg="#FFFFFF", fg="#033966").pack(side=tk.LEFT, padx=20)

        top = tk.Frame(self.frame_main, bg="#FFFFFF")
        top.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        tk.Label(top, text="UID de la tarjeta:", bg="#FFFFFF", fg="#000000", font=("Segoe UI", 10)).pack(anchor="w", padx=30)
        
        frame_uid = tk.Frame(top, bg="#FFFFFF")
        frame_uid.pack(fill=tk.X, padx=30, pady=5)
        
        ent_uid = tk.Entry(frame_uid, font=("Segoe UI", 12), bg="#FFFFFF", fg="#000000", insertbackground="#000000", highlightbackground="#404040", highlightthickness=1, relief=tk.SOLID)
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
            tk.Label(top, text="💡 Pasa la tarjeta por el lector USB para auto-completar", bg="#FFFFFF", fg="#404040", font=("Segoe UI", 8)).pack(anchor="w", padx=30)

        tk.Label(top, text="Nombre del Empleado:", bg="#FFFFFF", fg="#000000", font=("Segoe UI", 10)).pack(anchor="w", padx=30, pady=(15,0))
        ent_nombre = tk.Entry(top, font=("Segoe UI", 12), bg="#FFFFFF", fg="#000000", insertbackground="#000000", highlightbackground="#404040", highlightthickness=1, relief=tk.SOLID)
        ent_nombre.pack(fill=tk.X, padx=30, pady=5, ipady=5)
        if nombre_editar: ent_nombre.insert(0, nombre_editar)

        tk.Label(top, text="Permisos de Áreas:", bg="#FFFFFF", fg="#000000", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=30, pady=(20, 5))
        
        btn_areas = tk.Button(top, text="Desplegar Áreas ▼", bg="#033966", fg="#FFFFFF", font=("Segoe UI", 10, "bold"), bd=0, activebackground="#0A8504", activeforeground="#FFFFFF")
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
            tk.Checkbutton(frame_areas, text=v, variable=var, bg="#F0F0F0", fg="#000000", selectcolor="#FFFFFF", activebackground="#F0F0F0", activeforeground="#000000", font=("Segoe UI", 10)).pack(anchor="w", pady=2, padx=10)

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
        if row: self.mostrar_vista_formulario_usuario(uid_editar=uid, nombre_editar=nombre, areas_editar=row[2])

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
        menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 10))
        ico_write = self.cargar_icono("write", 16)
        ico_alarm = self.cargar_icono("alarm", 16)
        menu.ico_write = ico_write
        menu.ico_alarm = ico_alarm
        menu.add_command(label=" Editar Usuario", image=ico_write, compound=tk.LEFT, command=self.editar_usuario_seleccionado)
        menu.add_command(label=" Eliminar Usuario", image=ico_alarm, compound=tk.LEFT, command=self.eliminar_usuario_seleccionado)
        menu.post(x, y)


    # ========================== VISTA PUERTAS ==========================
    def mostrar_vista_puertas(self):
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
        self.tree_puertas.column("tipo", width=250, anchor="center")
        self.tree_puertas.column("acciones", width=120, anchor="center")
        
        self.tree_puertas.tag_configure("hover", background="#0A8504", foreground="#FFFFFF")
        
        scrollbar = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree_puertas.yview)
        self.tree_puertas.configure(yscroll=scrollbar.set)
        self.tree_puertas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        


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
        tk.Label(frame_header, text=titulo_texto, font=("Segoe UI", 16, "bold"), bg="#FFFFFF", fg="#033966").pack(side=tk.LEFT, padx=20)

        top = tk.Frame(self.frame_main, bg="#FFFFFF")
        top.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tk.Label(top, text="MAC Address:", bg="#FFFFFF", fg="#000000", font=("Segoe UI", 10)).pack(anchor="w", padx=40)
        ent_mac = tk.Entry(top, font=("Segoe UI", 12), bg="#FFFFFF", fg="#000000", highlightthickness=1, relief=tk.SOLID)
        ent_mac.pack(fill=tk.X, padx=40, pady=5, ipady=5)
        if mac_editar:
            ent_mac.insert(0, mac_editar)
            
        tk.Label(top, text="Nombre de Puerta:", bg="#FFFFFF", fg="#000000", font=("Segoe UI", 10)).pack(anchor="w", padx=40, pady=(10, 0))
        ent_nombre = tk.Entry(top, font=("Segoe UI", 12), bg="#FFFFFF", fg="#000000", highlightthickness=1, relief=tk.SOLID)
        ent_nombre.pack(fill=tk.X, padx=40, pady=5, ipady=5)
        if nombre_editar: ent_nombre.insert(0, nombre_editar)

        tk.Label(top, text="Área:", bg="#FFFFFF", fg="#000000", font=("Segoe UI", 10)).pack(anchor="w", padx=40, pady=(10, 0))
        
        a_list = [f"{k} - {v}" for k,v in AREAS.items()]
        val_inicial = "Seleccionar Área"
        if area_editar:
            for val in a_list:
                if area_editar in val:
                    val_inicial = val
                    break
        elif a_list:
            val_inicial = a_list[0]
            
        var_area_sel = tk.StringVar(value=val_inicial)
        
        btn_area_puerta = tk.Button(top, text=f"{val_inicial} ▼", bg="#033966", fg="#FFFFFF", font=("Segoe UI", 10, "bold"), bd=0, activebackground="#0A8504", activeforeground="#FFFFFF")
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
            btn_opt = tk.Button(frame_area_puerta, text=val, bg="#F0F0F0", fg="#000000", bd=0, anchor="w", font=("Segoe UI", 10), command=lambda v=val: select_area(v))
            btn_opt.pack(fill=tk.X, padx=10, pady=2)

        tk.Label(top, text="Tipo de Acceso:", bg="#FFFFFF", fg="#000000", font=("Segoe UI", 10)).pack(anchor="w", padx=40, pady=(10, 0))
        
        val_inicial_tipo = tipo_editar if tipo_editar in ["Entrada", "Salida"] else "Entrada"
        var_tipo_sel = tk.StringVar(value=val_inicial_tipo)
        
        btn_tipo = tk.Button(top, text=f"{val_inicial_tipo} ▼", bg="#033966", fg="#FFFFFF", font=("Segoe UI", 10, "bold"), bd=0, activebackground="#0A8504", activeforeground="#FFFFFF")
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
            tk.Button(frame_tipo, text=val, bg="#F0F0F0", fg="#000000", bd=0, anchor="w", font=("Segoe UI", 10), command=lambda v=val: select_tipo(v)).pack(fill=tk.X, padx=10, pady=2)

        def guardar_puerta():
            mac = ent_mac.get().strip().upper()
            nombre = ent_nombre.get().strip()
            area_sel = var_area_sel.get()
            tipo_sel = var_tipo_sel.get()
            if not mac or not nombre or area_sel == "Seleccionar Área" or not tipo_sel:
                return messagebox.showerror("Error", "Todos los campos son obligatorios")
            area_id = area_sel.split(" - ")[0]
            
            if mac_editar and mac_editar != mac:
                puertas.eliminar_puerta(mac_editar)

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
        menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 10))
        ico_write = self.cargar_icono("write", 16)
        ico_alarm = self.cargar_icono("alarm", 16)
        menu.ico_write = ico_write
        menu.ico_alarm = ico_alarm
        menu.add_command(label=" Editar Puerta", image=ico_write, compound=tk.LEFT, command=self.editar_puerta_seleccionada)
        menu.add_command(label=" Eliminar Puerta", image=ico_alarm, compound=tk.LEFT, command=self.eliminar_puerta_seleccionada)
        menu.post(x, y)

    # ========================== COMUNES ==========================
    def agregar_area_principal(self):
        from tkinter import simpledialog
        from areas_manager import crear_nueva_area
        nombre = simpledialog.askstring("Nueva Área", "Ingresa el nombre de la nueva área:", parent=self)
        if nombre:
            if crear_nueva_area(nombre):
                messagebox.showinfo("Éxito", f"Área '{nombre}' agregada correctamente.", parent=self)
                # Refrescar vista actual si es necesario
                if self.vista_actual == "usuarios":
                    self.cargar_tabla_usuarios()
                elif self.vista_actual == "puertas":
                    self.cargar_tabla_puertas()
            else:
                messagebox.showerror("Error", "No se pudo agregar el área. Puede que ya exista o hubo un error en la BD.", parent=self)

    def conectar_serial(self):
        if self.serial_conn and self.serial_conn.is_open:
            return
        try:
            self.serial_conn = serial.Serial(PUERTO, BAUDRATE, timeout=1)
            self.lbl_estado_serial.config(text=f"🟢 USB Lector Conectado ({PUERTO})", fg="#0A8504")
            self.hilo_serial = threading.Thread(target=self.leer_serial, daemon=True)
            self.hilo_serial.start()
        except:
            self.lbl_estado_serial.config(text="🔴 USB Lector Desconectado", fg="#9C0303")
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
            self.lbl_estado_serial.config(text="🔴 USB Lector Desconectado", fg="#9C0303")
            self.after(5000, self.conectar_serial)

    def sincronizar_esp32_inmediato(self):
        pass

    def destroy(self):
        self.running = False
        if self.serial_conn and self.serial_conn.is_open: 
            try: self.serial_conn.close()
            except: pass
        super().destroy()
