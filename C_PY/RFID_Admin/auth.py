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


def registrar_cuenta(username: str, password: str, rol: str) -> tuple[bool, str]:
    """
    Crea una nueva cuenta de acceso al sistema (Superadmin, Admin, User).
    Guarda tanto el hash SHA-256 para autenticación segura como password_view
    para consulta exclusiva del Superadmin.
    """
    username = username.strip()
    if not username:
        return False, "El nombre de usuario no puede estar vacío."
    if len(password) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres."
    if rol not in ["Superadmin", "Admin", "User", "ingeniero", "operador"]:
        return False, "Rol no válido."

    conn = conectar_db()
    if not conn:
        return False, "No se pudo conectar a la base de datos."

    try:
        cur = conn.cursor()
        hashed = hashlib.sha256(password.encode()).hexdigest()
        cur.execute(
            "INSERT INTO admin_users (username, password_hash, rol, password_view) VALUES (%s, %s, %s, %s)",
            (username, hashed, rol, password),
        )
        conn.commit()
        log_info(f"Cuenta '{username}' con rol '{rol}' creada exitosamente.")
        return True, "Cuenta creada exitosamente."
    except Exception as e:
        if "Duplicate entry" in str(e) or "1062" in str(e):
            return False, f"El usuario '{username}' ya existe."
        log_error(f"Error creando cuenta '{username}': {e}")
        return False, f"Error al guardar la cuenta: {e}"
    finally:
        conn.close()


def cambiar_password_cuenta(account_id: int, nueva_password: str) -> tuple[bool, str]:
    """
    Actualiza la contraseña de una cuenta en admin_users.
    """
    if len(nueva_password) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres."

    conn = conectar_db()
    if not conn:
        return False, "No se pudo conectar a la base de datos."

    try:
        cur = conn.cursor()
        hashed = hashlib.sha256(nueva_password.encode()).hexdigest()
        cur.execute(
            "UPDATE admin_users SET password_hash = %s, password_view = %s WHERE id = %s",
            (hashed, nueva_password, account_id),
        )
        conn.commit()
        log_info(f"Contraseña actualizada para la cuenta ID {account_id}.")
        return True, "Contraseña actualizada exitosamente."
    except Exception as e:
        log_error(f"Error actualizando contraseña para cuenta ID {account_id}: {e}")
        return False, f"Error al actualizar la contraseña: {e}"
    finally:
        conn.close()


def listar_cuentas(es_superadmin: bool = False) -> list[tuple[int, str, str, str]]:
    """
    Lista todas las cuentas del sistema con su ID, nombre de usuario, rol y contraseña.
    Por seguridad, la contraseña real en texto plano solo se retorna si es_superadmin es True.
    """
    conn = conectar_db()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, rol, COALESCE(password_view, '') FROM admin_users ORDER BY id ASC")
        rows = cur.fetchall()
        resultado = []
        for c_id, u_name, r_name, p_view in rows:
            if es_superadmin:
                pass_text = p_view if p_view else "(No registrada)"
            else:
                pass_text = "••••••••"
            resultado.append((c_id, u_name, r_name, pass_text))
        return resultado
    except Exception as e:
        log_error(f"Error listando cuentas: {e}")
        return []
    finally:
        conn.close()


def eliminar_cuenta(account_id: int) -> tuple[bool, str]:
    """
    Elimina una cuenta del sistema por su ID, protegiendo al último Superadmin.
    """
    conn = conectar_db()
    if not conn:
        return False, "No se pudo conectar a la base de datos."
    try:
        cur = conn.cursor()
        cur.execute("SELECT rol FROM admin_users WHERE id = %s", (account_id,))
        res = cur.fetchone()
        if not res:
            return False, "La cuenta no existe."
        rol_eliminar = res[0]
        if rol_eliminar in ["Superadmin", "ingeniero"]:
            cur.execute("SELECT COUNT(*) FROM admin_users WHERE rol IN ('Superadmin', 'ingeniero')")
            if cur.fetchone()[0] <= 1:
                return False, "No puedes eliminar al único Superadministrador del sistema."

        cur.execute("DELETE FROM admin_users WHERE id = %s", (account_id,))
        conn.commit()
        log_info(f"Cuenta con id {account_id} eliminada.")
        return True, "Cuenta eliminada exitosamente."
    except Exception as e:
        log_error(f"Error eliminando cuenta {account_id}: {e}")
        return False, f"Error al eliminar la cuenta: {e}"
    finally:
        conn.close()


