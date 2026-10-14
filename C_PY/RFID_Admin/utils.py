import os
import sys


def get_base_path() -> str:
    """
    Returns the base application path, handling both frozen (PyInstaller)
    and standard script execution environments. (Read-only path)
    """
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_data_path() -> str:
    r"""
    Returns a writable directory path for application data (logs, config).
    Uses %APPDATA%\RFID_Admin on Windows or the base path if not frozen.
    """
    if getattr(sys, "frozen", False):
        appdata = os.getenv("APPDATA")
        if appdata:
            path = os.path.join(appdata, "RFID_Admin")
            os.makedirs(path, exist_ok=True)
            return path
    return get_base_path()

def get_image_path(filename: str = "") -> str:
    """
    Finds the absolute path of an image/asset reliably across:
    1. PyInstaller _MEIPASS (onefile bundle)
    2. Next to the executable ({app}\\Imagenes)
    3. Source tree (development mode)
    """
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "Imagenes", filename))
        candidates.append(os.path.join(sys._MEIPASS, filename))
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), "Imagenes", filename))
        candidates.append(os.path.join(os.path.dirname(sys.executable), filename))

    base_src = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(base_src, "Imagenes", filename))
    candidates.append(os.path.join(base_src, filename))

    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0] if candidates else filename

