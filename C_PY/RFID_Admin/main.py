# main.py
# Punto de entrada de la aplicación de Administración RFID

from gui import AdminGUI

if __name__ == "__main__":
    print("Iniciando Panel de Administración RFID...")
    app = AdminGUI()
    app.mainloop()
