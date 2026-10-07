# main.py
# Punto de entrada de la aplicación de Administración RFID

import tkinter as tk
import threading
import time
import math


def show_splash():
    splash = tk.Tk()
    splash.overrideredirect(True)

    w, h, size = splash.winfo_screenwidth(), splash.winfo_screenheight(), 300
    splash.geometry(f"{size}x{size}+{(w-size)//2}+{(h-size)//2}")
    splash.configure(bg="#033966")

    tk.Label(
        splash,
        text="Iniciando RFID Admin...",
        fg="white",
        bg="#033966",
        font=("Segoe UI", 16, "bold"),
    ).pack(pady=(60, 20))
    canvas = tk.Canvas(
        splash, width=100, height=100, bg="#033966", highlightthickness=0
    )
    canvas.pack()

    arc = canvas.create_arc(
        10, 10, 90, 90, start=0, extent=120, outline="#FF9800", width=8, style=tk.ARC
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
