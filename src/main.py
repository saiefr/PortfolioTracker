# src/main.py
from database import SessionLocal, engine
import models
import crud
from sqlalchemy.orm import Session # Importar Session para type hinting

# --- Funciones de Interfaz de Usuario ---

def register_new_user(db: Session): # Ahora recibe la sesión como argumento
    """Función para registrar un usuario."""
    print("\n--- Registrar Nuevo Usuario ---")
    username = input("Nombre de usuario: ")
    email = input("Email: ")
    password = input("Contraseña: ")
    password_confirm = input("Confirmar contraseña: ")

    if password != password_confirm:
        print("Error: Las contraseñas no coinciden.")
        return

    # Verificar si el usuario o email ya existen
    existing_user = crud.get_user_by_username(db, username=username)
    if existing_user:
        print(f"Error: El nombre de usuario '{username}' ya existe.")
        return
    existing_email = crud.get_user_by_email(db, email=email)
    if existing_email:
        print(f"Error: El email '{email}' ya está registrado.")
        return

    # Crear el usuario
    try:
        new_user = crud.create_user(db=db, username=username, email=email, password=password)
        print(f"¡Usuario '{new_user.username}' creado exitosamente con ID: {new_user.id}!")
    except Exception as e:
        print(f"Ocurrió un error al crear usuario: {e}")
        db.rollback() # Deshacer cambios si hubo error

def add_new_asset(db: Session): # Recibe la sesión
    """Función para añadir un nuevo activo."""
    print("\n--- Añadir Nuevo Activo ---")
    symbol = input("Símbolo del activo (ej. AAPL, BTC-USD): ").upper() # Convertir a mayúsculas
    name = input("Nombre del activo (ej. Apple Inc., Bitcoin): ")

    # Mostrar opciones de tipo de activo
    print("Tipos de Activo Disponibles:")
    asset_types = list(models.AssetType) # Obtener los enums
    for i, asset_type in enumerate(asset_types):
        print(f"{i + 1}. {asset_type.name}")

    while True:
        try:
            choice = int(input(f"Selecciona el número del tipo de activo (1-{len(asset_types)}): "))
            if 1 <= choice <= len(asset_types):
                selected_type = asset_types[choice - 1]
                break
            else:
                print("Opción inválida.")
        except ValueError:
            print("Entrada inválida. Por favor, introduce un número.")

    # Verificar si el símbolo ya existe (en esta versión simple)
    existing_asset = crud.get_asset_by_symbol(db, symbol=symbol)
    if existing_asset:
        print(f"Advertencia: Ya existe un activo con el símbolo '{symbol}' (ID: {existing_asset.id}). No se añadirá de nuevo.")
        # En una versión multiusuario, esto se verificaría por usuario.
        return

    # Crear el activo
    try:
        new_asset = crud.create_asset(db=db, symbol=symbol, name=name, asset_type=selected_type)
        print(f"¡Activo '{new_asset.symbol}' ({new_asset.name}) añadido exitosamente con ID: {new_asset.id}!")
    except Exception as e:
        print(f"Ocurrió un error al añadir activo: {e}")
        db.rollback()

# --- Flujo Principal ---
if __name__ == "__main__":
    # Obtener una sesión de base de datos que se usará para todas las operaciones
    db = SessionLocal()
    try:
        while True:
            print("\n--- Menú Principal ---")
            print("1. Registrar Nuevo Usuario")
            print("2. Añadir Nuevo Activo")
            print("3. Salir")
            choice = input("Elige una opción: ")

            if choice == '1':
                register_new_user(db) # Pasar la sesión
            elif choice == '2':
                add_new_asset(db) # Pasar la sesión
            elif choice == '3':
                print("Saliendo...")
                break
            else:
                print("Opción no válida. Inténtalo de nuevo.")
    finally:
        print("Cerrando conexión a la base de datos.")
        db.close() # Asegurarse de cerrar la sesión al final