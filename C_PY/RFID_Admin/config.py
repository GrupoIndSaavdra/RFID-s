# config.py
# Variables globales y configuraciones

import os
import sys

if getattr(sys, 'frozen', False):
    app_path = os.path.dirname(sys.executable)
else:
    app_path = os.path.dirname(os.path.abspath(__file__))

config_file = os.path.join(app_path, "ajustes_puerto.txt")

if not os.path.exists(config_file):
    with open(config_file, "w", encoding="utf-8") as f:
        f.write("COM4")
    PUERTO = "COM4"
else:
    with open(config_file, "r", encoding="utf-8") as f:
        PUERTO = f.read().strip()
        if not PUERTO:
            PUERTO = "COM4"

BAUDRATE = 115200

# ── Configuracion MySQL (XAMPP) ──────────────────────────────
DB_CONFIG = {
    "host":     "192.168.0.10",
    "user":     "root",
    "password": "",
    "database": "rfid_db"
}

# ── Areas disponibles ────────────────────────────────────────
AREAS = {
    "1": "Baños",
    "2": "Programación-Software",
    "3": "Calidad",
    "4": "Almacén",
    "5": "RH",
    "6": "Mantenimiento",
    "7": "Comedor",
    "8": "Gerencia",
    "9": "Producción",
    "10": "Sala de Juntas",
    "11": "Auditorio"
}


# ── Tablas correspondientes a las áreas ──────────────────────
AREAS_TABLAS = {
    "1": "banos",
    "2": "programacion_software",
    "3": "calidad",
    "4": "almacen",
    "5": "rh",
    "6": "mantenimiento",
    "7": "comedor",
    "8": "oficina_de_gerencia",
    "9": "oficina_de_produccion",
    "10": "sala_de_juntas",
    "11": "auditorio"
}

