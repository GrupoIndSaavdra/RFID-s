import tkinter as tk
from PIL import Image, ImageTk
import os, sys


def get_base_path():
    return (
        os.path.dirname(sys.executable)
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.abspath(__file__))
    )


_icon_cache = {}


def get_icon(n, s=48):
    if (n, s) in _icon_cache:
        return _icon_cache[(n, s)]
    try:
        img = ImageTk.PhotoImage(
            Image.open(os.path.join(get_base_path(), "Imagenes", n)).resize(
                (s, s), Image.Resampling.LANCZOS
            )
        )
        _icon_cache[(n, s)] = img
        return img
    except:
        return None


class CustomAlert(tk.Toplevel):
    def __init__(self, p, t, m, a_t="info"):
        super().__init__(p or tk._default_root)
        self.result, self.alert_type = None, a_t
        self.overrideredirect(True)
        self.configure(
            bg="#FFFFFF", highlightbackground="#CCCCCC", highlightthickness=1
        )
        self.geometry(
            f"450x220+{(self.winfo_screenwidth()//2)-225}+{(self.winfo_screenheight()//2)-110}"
        )

        cfg = {
            "error": ("#DC3545", "#c82333", "Eliminar.png"),
            "warning": ("#FFC107", "#e0a800", "Advertencia.png"),
        }
        bc, bh, ic = cfg.get(
            a_t, ("#007BFF", "#0056b3", "Aceptar.png" if a_t == "info" else "Aviso.png")
        )

        hdr = tk.Frame(self, bg="#FFFFFF", height=30)
        hdr.pack(fill=tk.X)
        lbl_t = tk.Label(
            hdr, text=t, bg="#FFFFFF", fg="#1A1A1A", font=("Segoe UI", 10, "bold")
        )
        lbl_t.pack(side=tk.LEFT, padx=15, pady=5)

        self.s_x, self.s_y = 0, 0

        def s_m(e):
            self.s_x, self.s_y = e.x, e.y

        def m_w(e):
            self.geometry(
                f"+{self.winfo_x()-self.s_x+e.x}+{self.winfo_y()-self.s_y+e.y}"
            )

        for w in (hdr, lbl_t):
            w.bind("<Button-1>", s_m)
            w.bind("<B1-Motion>", m_w)

        bdy = tk.Frame(self, bg="#FFFFFF")
        bdy.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        img = get_icon(ic, 64)
        if img:
            self.img_ref = img
            tk.Label(bdy, image=img, bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 20))
        tk.Message(
            tk.Frame(bdy, bg="#FFFFFF").pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            or bdy,
            text=m,
            bg="#FFFFFF",
            fg="#333333",
            font=("Segoe UI", 11),
            width=280,
        ).pack(anchor="w", pady=(10, 0))

        ftr = tk.Frame(self, bg="#F8F9FA", height=60)
        ftr.pack(fill=tk.X, side=tk.BOTTOM)

        def mk_b(txt, cmd, c):
            b = tk.Button(
                ftr,
                text=txt,
                bg=c,
                fg="white",
                font=("Segoe UI", 11, "bold"),
                bd=0,
                padx=30,
                pady=10,
                cursor="hand2",
                command=cmd,
            )
            b.bind(
                "<Enter>",
                lambda e, bt=b, cl=c: bt.config(bg=bh if cl == bc else "#5a6268"),
            )
            b.bind("<Leave>", lambda e, bt=b, cl=c: bt.config(bg=cl))
            return b

        if a_t in ("info", "error", "warning"):
            mk_b("Aceptar", self.ok, bc).pack(side=tk.RIGHT, padx=20, pady=15)
        elif a_t == "question":
            mk_b("No", self.no, "#6c757d").pack(side=tk.RIGHT, padx=(5, 20), pady=15)
            mk_b("Sí", self.yes, bc).pack(side=tk.RIGHT, padx=(0, 5), pady=15)
        elif a_t == "question_cancel":
            mk_b("Cancelar", self.cancel, "#6c757d").pack(
                side=tk.RIGHT, padx=(5, 20), pady=15
            )
            mk_b("No", self.no, "#DC3545").pack(side=tk.RIGHT, padx=(5, 5), pady=15)
            mk_b("Sí", self.yes, bc).pack(side=tk.RIGHT, padx=(0, 5), pady=15)

        def b_c(e):
            if not (
                self.winfo_rootx()
                <= e.x_root
                <= self.winfo_rootx() + self.winfo_width()
                and self.winfo_rooty()
                <= e.y_root
                <= self.winfo_rooty() + self.winfo_height()
            ):
                if a_t in ("info", "error", "warning"):
                    self.ok()
                else:
                    self.cancel()

        self.bind("<Button-1>", b_c)

        self.transient(p)
        self.grab_set()
        self.update_idletasks()
        self.lift()
        self.attributes("-topmost", True)
        self.wait_window(self)

    def ok(self):
        self.result = "ok"
        self.grab_release()
        self.destroy()

    def yes(self):
        self.result = True
        self.grab_release()
        self.destroy()

    def no(self):
        self.result = False
        self.grab_release()
        self.destroy()

    def cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


def showinfo(t, m, **k):
    return CustomAlert(k.get("parent"), t, m, "info").result


def showerror(t, m, **k):
    return CustomAlert(k.get("parent"), t, m, "error").result


def showwarning(t, m, **k):
    return CustomAlert(k.get("parent"), t, m, "warning").result


def askyesno(t, m, **k):
    return CustomAlert(k.get("parent"), t, m, "question").result


def askyesnocancel(t, m, **k):
    return CustomAlert(k.get("parent"), t, m, "question_cancel").result
