import serial
import time

try:
    ser = serial.Serial('COM5', 115200, timeout=1)
    print("Escuchando el ESP32 en COM5...")
    start_time = time.time()
    
    # Escuchar por 20 segundos
    while time.time() - start_time < 20:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(line)
except Exception as e:
    print(f"Error abriendo puerto: {e}")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
