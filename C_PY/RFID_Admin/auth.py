from logger import log_error
# auth.py
import hashlib
from database import conectar_db

def login(username, password):
    if not (conn := conectar_db()): return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT rol FROM admin_users WHERE username = %s AND password_hash = %s", (username, hashlib.sha256(password.encode()).hexdigest()))
        return res[0] if (res := cur.fetchone()) else None
    except Exception as e: log_error(f"Error en login: {e}"); return None
    finally: conn.close()
