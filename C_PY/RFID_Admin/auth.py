# auth.py
# Módulo de autenticación para el sistema de administración

import hashlib
from database import conectar_db

def login(username, password):
    """
    Verifica las credenciales del usuario.
    Retorna el rol ('ingeniero' o 'operador') si es exitoso, o None si falla.
    """
    conn = conectar_db()
    if not conn: return None
    
    try:
        cur = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cur.execute("SELECT rol FROM admin_users WHERE username = %s AND password_hash = %s", (username, password_hash))
        result = cur.fetchone()
        
        if result:
            return result[0]
        return None
    except Exception as e:
        print(f"Error en login: {e}")
        return None
    finally:
        conn.close()
