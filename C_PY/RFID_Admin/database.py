# database.py
# Módulo de conexión a la base de datos

import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG

def conectar_db():
    """Establece la conexión con la base de datos MySQL usando los datos de config.py"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"Error al conectar con la base de datos: {e}")
        return None
