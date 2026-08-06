import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk
import sys

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_icon(name, size=48):
    path = os.path.join(get_base_path(), "Imagenes", name)
    try:
        img = Image.open(path)
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except:
        return None

class CustomAlert(tk.Toplevel):
    def __init__(self, parent, title, message, alert_type="info"):
        if not parent:
            parent = tk._default_root
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.alert_type = alert_type
        
        # Ocultar la barra de título nativa para un look más moderno
        self.overrideredirect(True)
        self.configure(bg="#FFFFFF", highlightbackground="#CCCCCC", highlightthickness=1)
        self.geometry("450x220")
        
        # Centrar en la pantalla
        self.update_idletasks()
        width = 450
        height = 220
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # Variables visuales según tipo
        bg_color = "#FFFFFF"
        fg_color = "#333333"
        btn_color = "#007BFF"
        btn_hover = "#0056b3"
        icon_file = "Aceptar.png"
        
        if alert_type == "error":
            btn_color = "#DC3545"
            btn_hover = "#c82333"
            icon_file = "Eliminar.png"
        elif alert_type == "warning":
            btn_color = "#FFC107"
            btn_hover = "#e0a800"
            icon_file = "Advertencia.png"
        elif alert_type in ("question", "question_cancel"):
            btn_color = "#007BFF"
            btn_hover = "#0056b3"
            icon_file = "Aviso.png"
            
        self.icon_img = get_icon(icon_file, 64)
        
        # Header (Barra superior para poder moverla)
        header = tk.Frame(self, bg=bg_color, height=30)
        header.pack(fill=tk.X)
        
        self.start_x = 0
        self.start_y = 0
        def start_move(event):
            self.start_x = event.x
            self.start_y = event.y
        def move_window(event):
            x = self.winfo_x() - self.start_x + event.x
            y = self.winfo_y() - self.start_y + event.y
            self.geometry(f'+{x}+{y}')
            
        header.bind("<Button-1>", start_move)
        header.bind("<B1-Motion>", move_window)
        
        lbl_title = tk.Label(header, text=title, bg=bg_color, fg="#1A1A1A", font=("Segoe UI", 10, "bold"))
        lbl_title.pack(side=tk.LEFT, padx=15, pady=5)
        
        lbl_title.bind("<Button-1>", start_move)
        lbl_title.bind("<B1-Motion>", move_window)
        
        # Body
        body = tk.Frame(self, bg=bg_color)
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        if self.icon_img:
            lbl_icon = tk.Label(body, image=self.icon_img, bg=bg_color)
            lbl_icon.pack(side=tk.LEFT, padx=(0, 20))
            
        # Message text
        msg_frame = tk.Frame(body, bg=bg_color)
        msg_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        lbl_msg = tk.Message(msg_frame, text=message, bg=bg_color, fg=fg_color, font=("Segoe UI", 11), width=280)
        lbl_msg.pack(anchor="w", pady=(10, 0))
        
        # Footer
        footer = tk.Frame(self, bg="#F8F9FA", height=60)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Botones más grandes
        def create_btn(text, cmd, color, bg_c="white"):
            btn = tk.Button(footer, text=text, bg=color, fg=bg_c, font=("Segoe UI", 11, "bold"), bd=0, padx=30, pady=10, cursor="hand2", command=cmd)
            btn.bind("<Enter>", lambda e, b=btn, c=color: b.config(bg=btn_hover if c == btn_color else "#5a6268"))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c))
            return btn
            
        if alert_type == "info" or alert_type == "error" or alert_type == "warning":
            btn_ok = create_btn("Aceptar", self.ok, btn_color)
            btn_ok.pack(side=tk.RIGHT, padx=20, pady=15)
        elif alert_type == "question":
            btn_no = create_btn("No", self.no, "#6c757d")
            btn_no.pack(side=tk.RIGHT, padx=(5, 20), pady=15)
            btn_yes = create_btn("Sí", self.yes, btn_color)
            btn_yes.pack(side=tk.RIGHT, padx=(0, 5), pady=15)
        elif alert_type == "question_cancel":
            btn_cancel = create_btn("Cancelar", self.cancel, "#6c757d")
            btn_cancel.pack(side=tk.RIGHT, padx=(5, 20), pady=15)
            btn_no = create_btn("No", self.no, "#DC3545")
            btn_no.pack(side=tk.RIGHT, padx=(5, 5), pady=15)
            btn_yes = create_btn("Sí", self.yes, btn_color)
            btn_yes.pack(side=tk.RIGHT, padx=(0, 5), pady=15)
            
        # Efecto de brillar en rojo si hacen clic afuera
        def on_click_anywhere(event):
            x, y = event.x_root, event.y_root
            x0, y0 = self.winfo_rootx(), self.winfo_rooty()
            w, h = self.winfo_width(), self.winfo_height()
            
            if x < x0 or x > x0 + w or y < y0 or y > y0 + h:
                self.configure(highlightbackground="red", highlightthickness=2)
                header.configure(bg="#ffcccc")
                self.bell()
                self.after(150, lambda: self.configure(highlightbackground="#CCCCCC", highlightthickness=1))
                self.after(150, lambda: header.configure(bg=bg_color))
                self.focus_force()
                
        self.bind("<Button-1>", on_click_anywhere)
            
        self.transient(parent)
        self.grab_set()
        
        self.update_idletasks()
        self.lift()
        self.attributes("-topmost", True)
        self.wait_window(self)
        
    def ok(self):
        self.result = "ok"
        self.destroy()
    def yes(self):
        self.result = True
        self.destroy()
    def no(self):
        self.result = False
        self.destroy()
    def cancel(self):
        self.result = None
        self.destroy()

def _get_parent(kwargs):
    return kwargs.get("parent", None)

def showinfo(title, message, **kwargs):
    app = CustomAlert(_get_parent(kwargs), title, message, "info")
    return app.result

def showerror(title, message, **kwargs):
    app = CustomAlert(_get_parent(kwargs), title, message, "error")
    return app.result

def showwarning(title, message, **kwargs):
    app = CustomAlert(_get_parent(kwargs), title, message, "warning")
    return app.result

def askyesno(title, message, **kwargs):
    app = CustomAlert(_get_parent(kwargs), title, message, "question")
    return app.result

def askyesnocancel(title, message, **kwargs):
    app = CustomAlert(_get_parent(kwargs), title, message, "question_cancel")
    return app.result
