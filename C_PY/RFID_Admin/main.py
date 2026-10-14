# main.py
# Punto de entrada de la aplicación de Administración RFID

import os
import sys
import ctypes
import tkinter as tk
import threading
import time
import math
from PIL import Image, ImageTk

# Fix taskbar icon: Set Windows AppUserModelID before any Tkinter window is created
try:
    myappid = "csproject.rfid_admin.gui.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

from utils import get_image_path


def show_splash():
    splash = tk.Tk()
    splash.overrideredirect(True)

    # Set icon for splash and Windows taskbar
    ico_path = get_image_path("G.ico")
    png_path = get_image_path("G.png")
    if os.path.exists(ico_path):
        try:
            splash.iconbitmap(ico_path)
        except Exception:
            pass
    if os.path.exists(png_path):
        try:
            icon_img = ImageTk.PhotoImage(Image.open(png_path))
            splash.iconphoto(True, icon_img)
            splash._icon_img = icon_img
        except Exception:
            pass

    w, h = splash.winfo_screenwidth(), splash.winfo_screenheight()
    size_w, size_h = 260, 260
    splash.geometry(f"{size_w}x{size_h}+{(w-size_w)//2}+{(h-size_h)//2}")
    splash.configure(bg="#033966")

    # Mostrar Logo de la empresa en la pantalla de bienvenida
    logo_path = get_image_path("Logo.png")
    if not os.path.exists(logo_path):
        logo_path = png_path

    if os.path.exists(logo_path):
        try:
            pil_img = Image.open(logo_path)
            orig_w, orig_h = pil_img.size
            target_h = 46
            target_w = int(orig_w * (target_h / orig_h))
            if target_w > 190:
                target_w = 190
                target_h = int(orig_h * (target_w / orig_w))
            pil_img = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            splash_logo = ImageTk.PhotoImage(pil_img)
            lbl_logo = tk.Label(splash, image=splash_logo, bg="#033966")
            lbl_logo.image = splash_logo
            lbl_logo.pack(pady=(28, 8))
        except Exception:
            pass

    tk.Label(
        splash,
        text="Iniciando",
        fg="white",
        bg="#033966",
        font=("Segoe UI", 13, "bold"),
    ).pack(pady=(2, 10))
    canvas = tk.Canvas(
        splash, width=54, height=54, bg="#033966", highlightthickness=0
    )
    canvas.pack()

    arc = canvas.create_arc(
        6, 6, 48, 48, start=0, extent=120, outline="#FF9800", width=4, style=tk.ARC
    )

    def animate_spinner(angle=0):
        if not splash.winfo_exists():
            return
        canvas.itemconfig(arc, start=angle)
        splash.after(20, animate_spinner, (angle - 15) % 360)

    animate_spinner()

    def load_app():
        import database
        from logger import log_error

        try:
            database.inicializar_db()
        except Exception as e:
            log_error(f"Error DB inicial: {e}")
        time.sleep(1.5)  # Fake loading time to show off splash
        splash.after(0, launch_gui)

    def launch_gui():
        splash.destroy()
        from gui import AdminGUI

        app = AdminGUI()
        app.mainloop()

    threading.Thread(target=load_app, daemon=True).start()
    splash.mainloop()


if __name__ == "__main__":
    from logger import log_error

    try:
        show_splash()
    except Exception as e:
        log_error(f"Fatal crash: {e}")
