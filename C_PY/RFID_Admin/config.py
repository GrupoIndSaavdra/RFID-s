import os
from typing import Dict
import serial.tools.list_ports
from utils import get_base_path


def get_rfid_port() -> str:
    """
    Scans available serial ports and returns the one likely connected to the RFID reader.
    Looks for keywords like 'USB', 'CH340', 'Arduino', or 'Serial' in the port description.

    Returns:
        str: The device port name (e.g., 'COM4' or '/dev/ttyUSB0').
    """
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = p.description or ""
        if any(keyword in desc for keyword in ["USB", "CH340", "Arduino", "Serial"]):
            return p.device
    return ports[0].device if ports else "COM4"


# Serial configuration
PUERTO: str = get_rfid_port()
BAUDRATE: int = 115200

# Environment variables setup
env_path = os.path.join(get_base_path(), ".env")
env_vars: Dict[str, str] = {}

if not os.path.exists(env_path):
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("DB_HOST=localhost\n")
        f.write("DB_USER=root\n")
        f.write("DB_PASS=\n")
        f.write("DB_NAME=rfid_db\n")

try:
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, value = stripped.split("=", 1)
                env_vars[key.strip()] = value.strip()
except Exception:
    pass

# Database configuration
DB_CONFIG: Dict[str, str] = {
    "host": env_vars.get("DB_HOST", "localhost"),
    "user": env_vars.get("DB_USER", "root"),
    "password": env_vars.get("DB_PASS", ""),
    "database": env_vars.get("DB_NAME", "rfid_db"),
}

# Global area configurations
AREAS: Dict[str, str] = {}
AREAS_TABLAS: Dict[str, str] = {}
