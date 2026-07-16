# main.py
# Punto de entrada de la aplicación de Administración RFID

from gui import AdminGUI
import database

if __name__ == "__main__":
    print("Iniciando Panel de Administración RFID...")
    database.inicializar_db()
    app = AdminGUI()
    app.mainloop()
