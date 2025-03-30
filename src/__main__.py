# src/__main__.py
# --- Importaciones Relativas ---
from .database import SessionLocal, engine
from . import models
from . import crud
from sqlalchemy.orm import Session
from datetime import datetime

# --- Funciones de Interfaz de Usuario ---
def register_new_user(db: Session):
    print("\n--- Registrar Nuevo Usuario ---")
    username = input("Nombre de usuario: ")
    email = input("Email: ")
    password = input("Contraseña: ")
    password_confirm = input("Confirmar contraseña: ")
    if password != password_confirm: print("Error: Las contraseñas no coinciden."); return
    existing_user = crud.get_user_by_username(db, username=username)
    if existing_user: print(f"Error: El nombre de usuario '{username}' ya existe."); return
    existing_email = crud.get_user_by_email(db, email=email)
    if existing_email: print(f"Error: El email '{email}' ya está registrado."); return
    try:
        new_user = crud.create_user(db=db, username=username, email=email, password=password)
        print(f"¡Usuario '{new_user.username}' creado exitosamente con ID: {new_user.id}!")
    except Exception as e: print(f"Ocurrió un error al crear usuario: {e}"); db.rollback()

def add_new_asset(db: Session):
    print("\n--- Añadir Nuevo Activo ---")
    # ASUMIMOS UN SOLO USUARIO POR AHORA (ID=1) - ¡Mejorar esto con login!
    USER_ID_TEMP = 1
    user = db.query(models.User).filter(models.User.id == USER_ID_TEMP).first()
    if not user: print(f"Error: Usuario con ID {USER_ID_TEMP} no encontrado. Registra un usuario primero."); return

    symbol = input("Símbolo del activo (ej. AAPL, BTC-USD): ").upper()
    name = input("Nombre del activo (ej. Apple Inc., Bitcoin): ")
    print("Tipos de Activo Disponibles:")
    asset_types = list(models.AssetType)
    for i, asset_type in enumerate(asset_types): print(f"{i + 1}. {asset_type.name}")
    while True:
        try:
            choice = int(input(f"Selecciona el número del tipo de activo (1-{len(asset_types)}): "))
            if 1 <= choice <= len(asset_types): selected_type = asset_types[choice - 1]; break
            else: print("Opción inválida.")
        except ValueError: print("Entrada inválida. Introduce un número.")

    # Verificar si ya existe PARA ESTE USUARIO
    existing_asset = crud.get_asset_by_symbol(db, symbol=symbol, owner_id=USER_ID_TEMP)
    if existing_asset: print(f"Advertencia: Ya tienes registrado el activo '{symbol}'."); return

    try:
        new_asset = crud.create_asset(db=db, owner_id=USER_ID_TEMP, symbol=symbol, name=name, asset_type=selected_type)
        print(f"¡Activo '{new_asset.symbol}' ({new_asset.name}) añadido exitosamente con ID: {new_asset.id}!")
    except Exception as e: print(f"Ocurrió un error al añadir activo: {e}"); db.rollback()

def add_new_transaction(db: Session):
    print("\n--- Registrar Nueva Transacción ---")
    USER_ID_TEMP = 1 # ASUNCIÓN TEMPORAL
    user = db.query(models.User).filter(models.User.id == USER_ID_TEMP).first()
    if not user: print(f"Error: Usuario con ID {USER_ID_TEMP} no encontrado."); return
    available_assets = db.query(models.Asset).filter(models.Asset.owner_id == USER_ID_TEMP).all()
    if not available_assets: print("Error: No hay activos registrados para este usuario."); return
    print("Activos Disponibles:")
    for i, asset in enumerate(available_assets): print(f"{i + 1}. {asset.symbol} ({asset.name})")
    while True:
        try:
            choice = int(input(f"Selecciona el número del activo (1-{len(available_assets)}): "))
            if 1 <= choice <= len(available_assets): selected_asset = available_assets[choice - 1]; break
            else: print("Opción inválida.")
        except ValueError: print("Entrada inválida.")
    print("Tipos de Transacción:")
    transaction_types = list(models.TransactionType)
    for i, t_type in enumerate(transaction_types): print(f"{i + 1}. {t_type.name}")
    while True:
        try:
            choice = int(input(f"Selecciona el tipo de transacción (1-{len(transaction_types)}): "))
            if 1 <= choice <= len(transaction_types): selected_transaction_type = transaction_types[choice - 1]; break
            else: print("Opción inválida.")
        except ValueError: print("Entrada inválida.")
    while True:
        try:
            quantity_str = input("Cantidad: "); quantity = float(quantity_str)
            if quantity <= 0: raise ValueError("Cantidad debe ser positiva.")
            break
        except ValueError as e: print(f"Entrada inválida para cantidad: {e}")
    while True:
        try:
            price_str = input("Precio por unidad: "); price_per_unit = float(price_str)
            if price_per_unit < 0: raise ValueError("Precio no puede ser negativo.") # Permitir 0?
            break
        except ValueError as e: print(f"Entrada inválida para precio: {e}")
    while True:
        date_str = input("Fecha de transacción (YYYY-MM-DD HH:MM:SS) o dejar vacío para ahora: ")
        if not date_str: transaction_date = datetime.now(); break
        try: transaction_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S'); break
        except ValueError: print("Formato de fecha inválido.")
    fees_str = input("Comisiones (opcional, ej. 0.5): "); fees = float(fees_str) if fees_str else 0.0
    notes = input("Notas (opcional): ")
    try:
        new_transaction = crud.create_transaction(
            db=db, owner_id=USER_ID_TEMP, asset_id=selected_asset.id,
            transaction_type=selected_transaction_type, quantity=quantity,
            price_per_unit=price_per_unit, transaction_date=transaction_date,
            fees=fees, notes=notes)
        print(f"¡Transacción registrada exitosamente con ID: {new_transaction.id}!")
    except Exception as e: print(f"Ocurrió un error al registrar transacción: {e}"); db.rollback()

# --- Flujo Principal ---
if __name__ == "__main__":
    # print("Creando tablas si no existen...") # Comentado, usar Alembic
    # models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        while True:
            print("\n--- Menú Principal ---")
            print("1. Registrar Nuevo Usuario")
            print("2. Añadir Nuevo Activo")
            print("3. Registrar Nueva Transacción")
            print("4. Salir")
            choice = input("Elige una opción: ")

            if choice == '1': register_new_user(db)
            elif choice == '2': add_new_asset(db)
            elif choice == '3': add_new_transaction(db)
            elif choice == '4': print("Saliendo..."); break
            else: print("Opción no válida.")
    finally:
        print("Cerrando conexión a la base de datos.")
        db.close()