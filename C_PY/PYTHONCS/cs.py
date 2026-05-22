# ============================================================
# Sistema de Control RFID — ESP32 + MySQL (XAMPP)
# ============================================================
# Pines ESP32 (referencia):
#   MISO=19  MOSI=23  CLK=18  CS=5  RST=22
#   SPI_HOST=SPI2_HOST | UART=UART_NUM_0
#   BUF_SIZE=128       | MAX_TARJETAS=50
# ============================================================

import sys
# Forzar UTF-8 en consola Windows sin romper input()
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import json
import threading
import serial
import mysql.connector
from mysql.connector import Error

# ── Configuracion Serial ─────────────────────────────────────
PUERTO   = "COM5"
BAUDRATE = 115200

# ── Configuracion MySQL (XAMPP) ──────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",           # XAMPP por default no tiene password
    "database": "rfid_db"
}

# ── Areas disponibles ────────────────────────────────────────
AREAS = {
    "1": "Banos",
    "2": "Programacion",
    "3": "Calidad",
    "4": "Almacen",
    "5": "RH",
    "6": "Mantenimiento"
}


# ══════════════════════════════════════════════════════════════
#  BASE DE DATOS MySQL
# ══════════════════════════════════════════════════════════════

def conectar_db():
    """Retorna una conexion activa a MySQL o None si falla."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"  [DB ERROR] No se pudo conectar a MySQL: {e}")
        return None


def db_registrar_tarjeta(uid: str, nombre: str, areas: str) -> bool:
    """
    Inserta o actualiza la tarjeta en la BD.
    'areas' es una cadena de numeros separados por coma: "1,3,5"
    """
    conn = conectar_db()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tarjetas (uid, nombre, areas)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE nombre=%s, areas=%s, activa=1
        """, (uid, nombre, areas, nombre, areas))
        conn.commit()
        print(f"  [DB] Tarjeta {uid} guardada en MySQL.")
        return True
    except Error as e:
        print(f"  [DB ERROR] {e}")
        return False
    finally:
        conn.close()


def db_buscar_tarjeta(uid: str):
    """
    Busca una tarjeta por UID.
    Retorna (uid, nombre, areas, activa) o None si no existe.
    """
    conn = conectar_db()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT uid, nombre, areas, activa FROM tarjetas WHERE uid=%s",
            (uid,)
        )
        return cur.fetchone()
    except Error as e:
        print(f"  [DB ERROR] {e}")
        return None
    finally:
        conn.close()


def db_listar_tarjetas() -> list:
    """
    Retorna todas las tarjetas de la BD:
    [(uid, nombre, areas, fecha_registro, activa), ...]
    """
    conn = conectar_db()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT uid, nombre, areas, fecha_registro, activa "
            "FROM tarjetas ORDER BY nombre"
        )
        return cur.fetchall()
    except Error as e:
        print(f"  [DB ERROR] {e}")
        return []
    finally:
        conn.close()


def db_obtener_uids_activos() -> list:
    """Retorna la lista de UIDs de tarjetas activas."""
    conn = conectar_db()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT uid FROM tarjetas WHERE activa=1")
        return [row[0] for row in cur.fetchall()]
    except Error as e:
        print(f"  [DB ERROR] {e}")
        return []
    finally:
        conn.close()


def db_eliminar_tarjeta(uid: str) -> bool:
    """Elimina la tarjeta FISICAMENTE de la BD (DELETE real)."""
    conn = conectar_db()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM tarjetas WHERE uid=%s", (uid,))
        conn.commit()
        print(f"  [DB] Tarjeta {uid} eliminada de MySQL.")
        return True
    except Error as e:
        print(f"  [DB ERROR] {e}")
        return False
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  HELPERS: areas
# ══════════════════════════════════════════════════════════════

def areas_a_nombres(areas_raw: str) -> str:
    """Convierte "1,3,5" → "Banos, Calidad, RH" """
    partes = [a.strip() for a in areas_raw.split(",") if a.strip()]
    return ", ".join(AREAS.get(p, p) for p in partes)


# ══════════════════════════════════════════════════════════════
#  COMUNICACION CON EL ESP32
# ══════════════════════════════════════════════════════════════

def enviar_lista_esp32(ser: serial.Serial):
    """Envía la lista de UIDs activos de la BD al ESP32."""
    uids = db_obtener_uids_activos()
    payload = json.dumps(uids, separators=(',', ':')) + "\n"
    ser.write(payload.encode())
    print(f"  [ESP32 <<] Lista enviada ({len(uids)} tarjeta(s)): {payload.strip()}")


def enviar_comando(ser: serial.Serial, cmd: str):
    """Envía un comando de texto al ESP32 (ADD / DEL / LIST)."""
    ser.write((cmd + "\n").encode())


def esperar_tarjeta_esp32(ser: serial.Serial, timeout: int = 30):
    """
    Bloquea hasta recibir un UID del ESP32 o agotar el timeout.
    Limpia el buffer serial primero para no leer tarjetas viejas.
    Retorna el UID (str) en mayusculas, o None si no llego.
    """
    # Vaciar cualquier dato acumulado en el buffer (tarjeta anterior)
    ser.reset_input_buffer()
    print(f"  Acerca la tarjeta al lector... ({timeout}s)")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            linea = ser.readline().decode(errors="ignore").strip()
            if not linea:
                continue
            data = json.loads(linea)
            if isinstance(data, dict) and "uid" in data:
                return data["uid"].upper()
        except (json.JSONDecodeError, serial.SerialException):
            pass
    return None


# ══════════════════════════════════════════════════════════════
#  HILO: RE-SINCRONIZACION CONTINUA AL ESP32
# ══════════════════════════════════════════════════════════════

def hilo_sync_periodico(ser: serial.Serial, intervalo: int = 60):
    """
    Cada `intervalo` segundos vuelve a enviar la lista de UIDs
    al ESP32 para que esté siempre actualizado aunque se reinicie.
    """
    while True:
        time.sleep(intervalo)
        try:
            enviar_lista_esp32(ser)
        except Exception:
            pass   # no interrumpir el hilo por errores transitorios


# ══════════════════════════════════════════════════════════════
#  OPCION 1 — Registrar tarjeta (leer + nombre + areas)
# ══════════════════════════════════════════════════════════════

def opcion1_registrar(ser: serial.Serial):
    print("\n" + "="*50)
    print("  OPCION 1 — REGISTRAR TARJETAS")
    print("  (escribe 'q' en cualquier campo para salir)")
    print("="*50)

    while True:   # loop para registrar multiples tarjetas sin salir al menu

        # 1. Esperar que llegue la tarjeta del ESP32
        print("\n  Retira cualquier tarjeta y acerca la NUEVA al lector...")
        uid = esperar_tarjeta_esp32(ser, timeout=30)
        if not uid:
            print("  Tiempo agotado. Volviendo al menu principal.")
            return
        print(f"\n  Tarjeta detectada: {uid}")

        # Verificar si ya existe
        existente = db_buscar_tarjeta(uid)
        if existente and existente[3]:
            print(f"  AVISO: Ya registrada a nombre de '{existente[1]}'.")
            resp = input("  Sobreescribir? (s/n): ").strip().lower()
            if resp == "q" or resp != "s":
                print("  Cancelado.")
            else:
                _registrar_datos(ser, uid)  # solo sobreescribir si confirma
        else:
            _registrar_datos(ser, uid)

        # Preguntar si quiere registrar otra
        otra = input("\n  Registrar otra tarjeta? (s/n): ").strip().lower()
        if otra != "s":
            print("  Volviendo al menu principal.")
            return


def _registrar_datos(ser: serial.Serial, uid: str):
    """Pide nombre + areas y guarda en BD. Separado para reutilizar."""
    # Nombre del propietario
    nombre = input("  Nombre del propietario (q=cancelar): ").strip()
    if not nombre or nombre.lower() == "q":
        print("  Cancelado.")
        return

    # Seleccion de areas
    print("\n  Areas disponibles:")
    for k, v in AREAS.items():
        print(f"    {k}) {v}")
    raw = input("  Numeros de area separados por coma (ej: 1,3,5): ").strip()
    if raw.lower() == "q":
        print("  Cancelado.")
        return

    nums = [x.strip() for x in raw.split(",") if x.strip() in AREAS]
    if not nums:
        print("  No se seleccionaron areas validas, cancelado.")
        return

    areas_str   = ",".join(nums)
    areas_human = ", ".join(AREAS[n] for n in nums)

    # Resumen y confirmacion
    print("\n  ---- Resumen ----")
    print(f"  UID    : {uid}")
    print(f"  Nombre : {nombre}")
    print(f"  Areas  : {areas_human}")
    conf = input("  Confirmar registro (s/n): ").strip().lower()
    if conf != "s":
        print("  Cancelado.")
        return

    # Guardar en MySQL y sincronizar ESP32
    ok = db_registrar_tarjeta(uid, nombre, areas_str)
    if ok:
        enviar_lista_esp32(ser)
        print("  Registro completado y ESP32 sincronizado.")


# ══════════════════════════════════════════════════════════════
#  OPCION 2 — Consulta de registros y eliminacion
# ══════════════════════════════════════════════════════════════

def opcion2_consulta(ser: serial.Serial):
    print("\n" + "="*50)
    print("  OPCION 2 — CONSULTA DE REGISTROS")
    print("="*50)

    tarjetas = db_listar_tarjetas()
    if not tarjetas:
        print("  No hay registros en la base de datos.")
        return

    # Encabezado con numero de fila para seleccionar facilmente
    print(f"\n  {'#':<4} {'UID':<12} {'Nombre':<22} {'Areas':<35} {'Estado':<10} {'Fecha'}")
    print(f"  {'-'*4} {'-'*12} {'-'*22} {'-'*35} {'-'*10} {'-'*16}")
    for i, (uid, nombre, areas_raw, fecha, activa) in enumerate(tarjetas, 1):
        estado     = "Activa" if activa else "Inactiva"
        areas_show = areas_a_nombres(areas_raw)
        fecha_str  = str(fecha)[:16] if fecha else "-"
        print(f"  {i:<4} {uid:<12} {nombre:<22} {areas_show:<35} {estado:<10} {fecha_str}")

    # Sub-menu
    print("\n  Opciones:")
    print("  d) Eliminar una tarjeta de BD y ESP32")
    print("  q) Volver al menu principal")
    sub = input("  Opcion: ").strip().lower()

    if sub == "d":
        sel = input("  Numero de fila o UID a eliminar: ").strip()

        # Determinar el UID: por numero de fila o directo
        uid_del = None
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < len(tarjetas):
                uid_del = tarjetas[idx][0]
            else:
                print(f"  Numero fuera de rango (1-{len(tarjetas)}).")
                return
        else:
            uid_del = sel.upper()

        # Verificar que existe en BD
        row = db_buscar_tarjeta(uid_del)
        if not row:
            print(f"  UID {uid_del} no encontrado en BD.")
            return

        # Confirmar eliminacion
        print(f"\n  Tarjeta a eliminar:")
        print(f"    UID    : {uid_del}")
        print(f"    Nombre : {row[1]}")
        print(f"    Areas  : {areas_a_nombres(row[2])}")
        conf = input("\n  Confirmar eliminacion de BD y ESP32? (s/n): ").strip().lower()

        if conf == "s":
            # 1. Eliminar fisicamente de MySQL
            db_eliminar_tarjeta(uid_del)
            # 2. Enviar lista actualizada al ESP32 (sin ese UID)
            enviar_lista_esp32(ser)
            print(f"  Tarjeta {uid_del} eliminada de BD y ESP32 actualizado.")
        else:
            print("  Cancelado, no se elimino nada.")


# ══════════════════════════════════════════════════════════════
#  OPCION 3 — Lista de tarjetas en ESP32
# ══════════════════════════════════════════════════════════════

def opcion3_lista_esp32(ser: serial.Serial):
    print("\n" + "="*50)
    print("  OPCION 3 — LISTA DE TARJETAS EN ESP32")
    print("="*50)

    enviar_comando(ser, "LIST")
    print("  Comando LIST enviado. Esperando respuesta...")

    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            linea = ser.readline().decode(errors="ignore").strip()
            if not linea:
                continue
            data = json.loads(linea)
            if isinstance(data, list):
                if not data:
                    print("  El ESP32 no tiene tarjetas en memoria RAM.")
                else:
                    print(f"\n  {len(data)} tarjeta(s) cargada(s) en ESP32:")
                    print(f"  {'UID':<12} Nombre en BD")
                    print(f"  {'-'*12} {'-'*25}")
                    for uid in data:
                        row = db_buscar_tarjeta(uid)
                        nombre = row[1] if row else "(sin registro en BD)"
                        print(f"  {uid:<12} {nombre}")
                return
        except (json.JSONDecodeError, serial.SerialException):
            pass
    print("  No se recibio respuesta del ESP32 en 5 segundos.")


# ══════════════════════════════════════════════════════════════
#  OPCION 4 — Lista de tarjetas en BD
# ══════════════════════════════════════════════════════════════

def opcion4_lista_bd():
    print("\n" + "="*50)
    print("  OPCION 4 — LISTA DE TARJETAS EN BASE DE DATOS")
    print("="*50)

    tarjetas = db_listar_tarjetas()
    activas  = [t for t in tarjetas if t[4]]

    if not activas:
        print("  No hay tarjetas activas en la base de datos.")
        return

    print(f"\n  Total activas: {len(activas)}")
    print(f"\n  {'UID':<12} {'Nombre':<22} {'Areas':<40} {'Fecha registro'}")
    print(f"  {'-'*12} {'-'*22} {'-'*40} {'-'*16}")
    for uid, nombre, areas_raw, fecha, _ in activas:
        areas_show = areas_a_nombres(areas_raw)
        fecha_str  = str(fecha)[:16] if fecha else "—"
        print(f"  {uid:<12} {nombre:<22} {areas_show:<40} {fecha_str}")


# ══════════════════════════════════════════════════════════════
#  OPCION 5 — Lectura continua (Acceso Permitido / Denegado)
# ══════════════════════════════════════════════════════════════

def opcion5_leer_continuo(ser: serial.Serial):
    print("\n" + "="*50)
    print("  OPCION 5 — LECTURA CONTINUA")
    print("  Presiona Ctrl+C para volver al menu")
    print("="*50)
    print("  Acerca una tarjeta al lector...\n")

    try:
        while True:
            linea = ser.readline().decode(errors="ignore").strip()
            if not linea:
                continue
            try:
                data = json.loads(linea)
                if isinstance(data, dict) and "uid" in data:
                    uid = data["uid"].upper()
                    row = db_buscar_tarjeta(uid)
                    ts  = time.strftime("%H:%M:%S")

                    if row and row[3]:   # existe y activa
                        areas_show = areas_a_nombres(row[2])
                        print(f"  [{ts}] ACCESO PERMITIDO  | {uid} — {row[1]} | {areas_show}")
                    else:
                        print(f"  [{ts}] ACCESO DENEGADO   | {uid} — Tarjeta no registrada o inactiva")
            except json.JSONDecodeError:
                # Mensajes de debug del ESP32
                if linea:
                    print(f"  [ESP32] {linea}")
    except KeyboardInterrupt:
        print("\n  Saliendo del modo lectura continua...")


# ══════════════════════════════════════════════════════════════
#  MENU PRINCIPAL
# ══════════════════════════════════════════════════════════════

def mostrar_menu():
    print("\n")
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║      SISTEMA DE CONTROL RFID — ESP32        ║")
    print("  ╠══════════════════════════════════════════════╣")
    print("  ║  1)  Registrar tarjeta (nombre + areas)     ║")
    print("  ║  2)  Consulta / Eliminacion de registros    ║")
    print("  ║  3)  Lista de tarjetas en ESP32             ║")
    print("  ║  4)  Lista de tarjetas en base de datos     ║")
    print("  ║  5)  Lectura continua (acceso/denegado)     ║")
    print("  ║  q)  Salir                                  ║")
    print("  ╚══════════════════════════════════════════════╝")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    # ── Verificar conexion a BD ──────────────────────────────
    print("Verificando conexion a MySQL (XAMPP)...")
    conn_test = conectar_db()
    if conn_test:
        conn_test.close()
        print("  MySQL: OK")
    else:
        print("  ADVERTENCIA: MySQL no disponible. Funciones de BD no estaran activas.")

    # ── Abrir puerto serial ──────────────────────────────────
    print(f"Abriendo puerto serial {PUERTO}...")
    try:
        ser = serial.Serial(PUERTO, BAUDRATE, timeout=0.5)
    except serial.SerialException as e:
        print(f"  ERROR: No se pudo abrir {PUERTO}: {e}")
        print("  Verifica que el ESP32 este conectado.")
        return

    time.sleep(2)   # esperar bootloader del ESP32
    print(f"  Serial: OK ({PUERTO} @ {BAUDRATE} baud)")

    # ── Sincronizacion inicial: BD → ESP32 ──────────────────
    print("Sincronizacion inicial BD → ESP32...")
    enviar_lista_esp32(ser)

    # ── Hilo de re-sincronizacion cada 60 segundos ───────────
    t_sync = threading.Thread(
        target=hilo_sync_periodico, args=(ser, 60), daemon=True
    )
    t_sync.start()
    print("  Hilo de sincronizacion periodica activo (cada 60s).")

    # ── Bucle del menu ───────────────────────────────────────
    while True:
        mostrar_menu()
        try:
            opcion = input("  Opcion: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            opcion = "q"

        if opcion == "1":
            opcion1_registrar(ser)
        elif opcion == "2":
            opcion2_consulta(ser)
        elif opcion == "3":
            opcion3_lista_esp32(ser)
        elif opcion == "4":
            opcion4_lista_bd()
        elif opcion == "5":
            opcion5_leer_continuo(ser)
        elif opcion == "q":
            print("  Cerrando conexion y saliendo...")
            ser.close()
            break
        else:
            print("  Opcion no valida. Ingresa 1-5 o q.")


if __name__ == "__main__":
    main()