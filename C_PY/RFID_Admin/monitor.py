from logger import log_error
import serial, serial.tools.list_ports, time


def main():
    if not (pts := [p.device for p in serial.tools.list_ports.comports()]):
        print("No se encontró ningún dispositivo conectado.")
        return
    for i, p in enumerate(pts):
        print(f"[{i}] {p}")
    try:
        p = pts[int(input(f"Selecciona el puerto (0-{len(pts)-1}): "))]
    except:
        print(f"Selección inválida. Usando: {pts[0]}")
        p = pts[0]

    print(
        f"\nConectando a {p} a 115200 baudios...\nPresiona Ctrl+C para salir.\n"
        + "-" * 50
    )
    try:
        ser = serial.Serial(p, 115200, timeout=1)
        while True:
            if ser.in_waiting > 0:
                try:
                    (
                        print(l)
                        if (
                            l := ser.readline()
                            .decode("utf-8", errors="replace")
                            .strip()
                        )
                        else None
                    )
                except Exception as e:
                    print(f"[Error leyendo datos: {e}]")
            else:
                time.sleep(0.01)
    except serial.SerialException as e:
        log_error(
            f"Error al abrir el puerto: {e}\nAsegúrate de que la interfaz gráfica no lo esté usando."
        )
    except KeyboardInterrupt:
        print("\nSaliendo del monitor serial...")
    finally:
        if "ser" in locals() and ser.is_open:
            ser.close()


if __name__ == "__main__":
    main()
