# config.py
# Variables globales y configuraciones

# ── Configuración Serial (Lector USB Administrador) ──────────
# Puerto USB donde está conectado el ESP32 de "lector_registro.c"
PUERTO   = "COM4"
BAUDRATE = 115200

# ── Configuracion MySQL (XAMPP) ──────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
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
    "10": "Sala de Juntas"
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
    "10": "sala_de_juntas"
}
