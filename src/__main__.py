# src/__main__.py
# --- Importaciones ---
# Mantener importaciones necesarias para funciones que podrían
# ser llamadas o para la verificación inicial.
from .database import SessionLocal, engine, Base # Base podría no ser necesaria aquí
from . import models
from . import crud
from sqlalchemy.orm import Session
from datetime import datetime
import pandas as pd
import traceback
import getpass
import sys # Necesario para sys.exit y sys.platform
import os
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, DivisionByZero
import logging # Necesario para logging

# <<< NUEVO >>> Importar la función para correr la GUI
from .gui import run_gui

# --- Configuración de Logging (Opcional pero recomendado) ---
# Puedes configurar el logging básico aquí si quieres capturar logs
# antes de que la GUI o el CRUD lo hagan.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Funciones de la Consola (Se mantienen pero no se usan directamente) ---
# Es útil mantenerlas por si necesitas volver a probar algo rápidamente
# desde la consola o para referencia.

current_logged_in_user: models.User | None = None # Variable global (ya no se usa en el flujo principal)

def clear_screen():
    if sys.platform.startswith('win'): os.system('cls')
    else: os.system('clear')

def register_new_user(db: Session):
    print("\n--- Registrar Nuevo Usuario (Consola) ---")
    # ... (código de la función register_new_user como estaba antes) ...
    while True:
        username = input("Nombre de usuario: ").strip()
        if not username: print("El nombre de usuario no puede estar vacío."); continue
        break
    while True:
        email = input("Email: ").strip()
        if not email or "@" not in email or "." not in email: print("Introduce un email válido."); continue
        break
    while True:
        password = getpass.getpass("Contraseña: ")
        if not password: print("La contraseña no puede estar vacía."); continue
        password_confirm = getpass.getpass("Confirmar contraseña: ")
        if password != password_confirm: print("Error: Las contraseñas no coinciden."); continue
        break
    try:
        new_user = crud.create_user(db=db, username=username, email=email, password=password)
        print(f"\n¡Usuario '{new_user.username}' creado exitosamente!")
    except ValueError as ve:
        print(f"\nError al crear usuario: {ve}")
    except Exception as e:
        print(f"\nOcurrió un error inesperado al crear usuario: {e}")
        logging.error("Error inesperado en register_new_user (consola)", exc_info=True)
    input("Presiona Enter para continuar...")


def login_user(db: Session):
    global current_logged_in_user
    print("\n--- Iniciar Sesión (Consola) ---")
    # ... (código de la función login_user como estaba antes) ...
    if current_logged_in_user:
        print(f"Ya has iniciado sesión como '{current_logged_in_user.username}'.")
        input("Presiona Enter para continuar...")
        return
    username = input("Nombre de usuario: ").strip()
    password = getpass.getpass("Contraseña: ")
    user = crud.get_user_by_username(db, username=username)
    if user and crud.verify_password(password, user.hashed_password):
        current_logged_in_user = user
        print(f"\n¡Bienvenido, {user.username}!")
    else:
        print("\nError: Nombre de usuario o contraseña incorrectos.")
        current_logged_in_user = None
    input("Presiona Enter para continuar...")

# ... (Puedes mantener aquí las otras funciones de consola:
# logout_user, add_new_asset, add_new_transaction, show_portfolio,
# _display_transactions_for_selection, view_transactions,
# edit_transaction, delete_transaction_ui
# ... si quieres conservarlas como referencia o para pruebas futuras) ...
# Por brevedad, las omito aquí, pero no hace daño dejarlas.


# --- Flujo Principal ---
if __name__ == "__main__":
    # --- Verificación Inicial de Base de Datos ---
    # Intenta conectar para verificar que la BD es accesible
    try:
        connection = engine.connect()
        connection.close()
        logging.info("Conexión inicial a la base de datos exitosa.")
    except Exception as e:
        # Mostrar error y salir si la BD no es accesible
        logging.critical(f"Error CRÍTICO al conectar a la base de datos: {e}", exc_info=True)
        print(f"[!!!] Error CRÍTICO al conectar a la base de datos: {e}")
        # Acceder a DATABASE_URL desde crud donde está definido
        # (Asegúrate de que crud.py define DATABASE_URL globalmente o impórtalo)
        try:
            # Intenta obtener la URL de crud.py para el mensaje de error
            db_url_for_error = crud.DATABASE_URL
        except AttributeError:
            # Fallback si no se puede importar o encontrar
            db_url_for_error = "No se pudo determinar la URL (verificar database.py/crud.py)"
        print(f"URL configurada: {db_url_for_error}")
        print("Verifica la ruta del archivo de base de datos y los permisos.")
        print("Asegúrate de haber ejecutado 'alembic upgrade head' correctamente.")
        input("Presiona Enter para salir...") # Pausa para que el usuario vea el error
        sys.exit(1) # Salir con código de error

    # --- Lanzar la Interfaz Gráfica ---
    print("[*] Iniciando la interfaz gráfica...")
    # Llama a la función que está definida en src/gui.py
    try:
        run_gui()
    except ImportError as ie:
         # Capturar error si falta alguna dependencia de la GUI (CustomTkinter, CTkMessagebox)
         logging.critical(f"Error de importación al iniciar la GUI: {ie}", exc_info=True)
         print(f"[!!!] Error de importación: {ie}")
         print("Asegúrate de haber instalado todas las dependencias de la GUI:")
         print("pip install customtkinter CTkMessagebox")
         input("Presiona Enter para salir...")
         sys.exit(1)
    except Exception as gui_e:
         # Capturar cualquier otro error inesperado durante la ejecución de la GUI
         logging.critical(f"Error inesperado durante la ejecución de la GUI: {gui_e}", exc_info=True)
         print(f"[!!!] Ocurrió un error inesperado en la GUI: {gui_e}")
         traceback.print_exc() # Imprimir traceback detallado
         input("Presiona Enter para salir...")
         sys.exit(1)


    # El código anterior del bucle while de la consola ya no se ejecuta aquí.
    # Toda la lógica interactiva ahora reside en la clase PortfolioApp en gui.py
    print("[*] La aplicación GUI ha terminado.")
    logging.info("Aplicación GUI cerrada limpiamente.")
    sys.exit(0) # Salir indicando éxito