# config.py
import os, sys

app_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
import serial.tools.list_ports

def get_rfid_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if "USB" in p.description or "CH340" in p.description or "Arduino" in p.description or "Serial" in p.description:
            return p.device
    return ports[0].device if ports else "COM4"

PUERTO = get_rfid_port()

BAUDRATE = 115200

env_path = os.path.join(app_path, ".env")
env_vars = {}
if not os.path.exists(env_path):
    with open(env_path, "w", encoding="utf-8") as f: f.write("DB_HOST=localhost\nDB_USER=root\nDB_PASS=\nDB_NAME=rfid_db\n")
try:
    with open(env_path, "r", encoding="utf-8") as f:
        for l in f:
            if l.strip() and not l.startswith("#") and "=" in l:
                k, v = l.strip().split("=", 1)
                env_vars[k.strip()] = v.strip()
except: pass

DB_CONFIG = {"host": env_vars.get("DB_HOST", "localhost"), "user": env_vars.get("DB_USER", "root"), "password": env_vars.get("DB_PASS", ""), "database": env_vars.get("DB_NAME", "rfid_db")}

AREAS = {}
AREAS_TABLAS = {}
