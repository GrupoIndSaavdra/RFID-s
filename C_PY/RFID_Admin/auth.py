import hashlib
from typing import Optional
from database import conectar_db
from logger import log_error, log_info, log_warning


def login(username: str, password: str) -> Optional[str]:
    """
    Attempts to authenticate a user by checking the username and password against the database.

    Args:
        username (str): The username attempting to log in.
        password (str): The plain-text password for the user.

    Returns:
        Optional[str]: The user's role (e.g., 'admin', 'operador') if successful, None otherwise.
    """
    conn = conectar_db()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        query = "SELECT rol FROM admin_users WHERE username = %s AND password_hash = %s"
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cur.execute(query, (username, hashed_password))
        res = cur.fetchone()

        if res:
            role = res[0]
            log_info(f"User '{username}' logged in successfully with role '{role}'.")
            return role
        else:
            log_warning(f"Failed login attempt for user '{username}'.")
            return None
    except Exception as e:
        log_error(f"Error during login process: {e}")
        return None
    finally:
        if conn:
            conn.close()
