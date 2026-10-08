import os
import sys


def get_base_path() -> str:
    """
    Returns the base application path, handling both frozen (PyInstaller)
    and standard script execution environments. (Read-only path)
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_data_path() -> str:
    """
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
