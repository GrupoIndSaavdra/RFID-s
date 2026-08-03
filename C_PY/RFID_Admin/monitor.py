import serial
import serial.tools.list_ports
import sys
import time

def main():
    print("Buscando puertos COM disponibles...")
    puertos = [port.device for port in serial.tools.list_ports.comports()]
    
    if not puertos:
        print("No se encontró ningún dispositivo conectado.")
        return
        
    print("Puertos disponibles:")
    for i, p in enumerate(puertos):
        print(f"[{i}] {p}")
        
    try:
        idx = int(input(f"Selecciona el puerto (0-{len(puertos)-1}): "))
        puerto = puertos[idx]
    except (ValueError, IndexError):
        print("Selección inválida. Usando el primer puerto:", puertos[0])
        puerto = puertos[0]
        
    baudrate = 115200
    print(f"\nConectando a {puerto} a {baudrate} baudios...")
    print("Presiona Ctrl+C para salir.\n")
    print("-" * 50)
    
    try:
        # Timeout en None para esperar hasta que haya datos
        ser = serial.Serial(puerto, baudrate, timeout=1)
        
        while True:
            if ser.in_waiting > 0:
                try:
                    # Leemos la línea y la decodificamos
                    linea = ser.readline().decode('utf-8', errors='replace').strip()
                    if linea:
                        print(linea)
                except Exception as e:
                    print(f"[Error leyendo datos: {e}]")
            else:
                time.sleep(0.01)
                
    except serial.SerialException as e:
        print(f"Error al abrir el puerto: {e}")
        print("Asegúrate de que la interfaz gráfica no esté usando el puerto al mismo tiempo.")
    except KeyboardInterrupt:
        print("\nSaliendo del monitor serial...")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
