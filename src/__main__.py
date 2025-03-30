# src/__main__.py
# --- Importaciones Relativas ---
from .database import SessionLocal, engine
from . import models
from . import crud
from sqlalchemy.orm import Session
from datetime import datetime
import pandas as pd
import traceback
import getpass

# --- Variable global simple para mantener el usuario logueado ---
current_logged_in_user: models.User | None = None

# --- Funciones de Interfaz de Usuario ---
def register_new_user(db: Session):
    print("\n--- Registrar Nuevo Usuario ---")
    username = input("Nombre de usuario: ")
    email = input("Email: ")
    password = getpass.getpass("Contraseña: ")
    password_confirm = getpass.getpass("Confirmar contraseña: ")
    if password != password_confirm: print("Error: Las contraseñas no coinciden."); return
    existing_user = crud.get_user_by_username(db, username=username)
    if existing_user: print(f"Error: El nombre de usuario '{username}' ya existe."); return
    existing_email = crud.get_user_by_email(db, email=email)
    if existing_email: print(f"Error: El email '{email}' ya está registrado."); return
    try:
        new_user = crud.create_user(db=db, username=username, email=email, password=password)
        print(f"¡Usuario '{new_user.username}' creado exitosamente!")
    except Exception as e: print(f"Ocurrió un error al crear usuario: {e}"); db.rollback()

def login_user(db: Session):
    """Maneja el inicio de sesión del usuario."""
    global current_logged_in_user
    print("\n--- Iniciar Sesión ---")
    if current_logged_in_user: print(f"Ya has iniciado sesión como '{current_logged_in_user.username}'."); return
    username = input("Nombre de usuario: ")
    password = getpass.getpass("Contraseña: ")
    user = crud.get_user_by_username(db, username=username)
    if user and crud.verify_password(password, user.hashed_password):
        current_logged_in_user = user; print(f"¡Bienvenido, {user.username}!")
    else: print("Error: Nombre de usuario o contraseña incorrectos."); current_logged_in_user = None

def logout_user():
    """Maneja el cierre de sesión."""
    global current_logged_in_user
    if current_logged_in_user: print(f"Cerrando sesión de '{current_logged_in_user.username}'."); current_logged_in_user = None
    else: print("No has iniciado sesión.")

def add_new_asset(db: Session):
    """Función para añadir un nuevo activo (requiere login)."""
    global current_logged_in_user
    if not current_logged_in_user: print("Error: Debes iniciar sesión para añadir activos."); return
    print("\n--- Añadir Nuevo Activo ---")
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
    existing_asset = crud.get_asset_by_symbol(db, symbol=symbol, owner_id=current_logged_in_user.id)
    if existing_asset: print(f"Advertencia: Ya tienes registrado el activo '{symbol}'."); return
    try:
        new_asset = crud.create_asset(db=db, owner_id=current_logged_in_user.id, symbol=symbol, name=name, asset_type=selected_type)
        print(f"¡Activo '{new_asset.symbol}' ({new_asset.name}) añadido exitosamente!")
    except Exception as e: print(f"Ocurrió un error al añadir activo: {e}"); db.rollback()

def add_new_transaction(db: Session):
    """Función para registrar una nueva transacción (requiere login)."""
    global current_logged_in_user
    if not current_logged_in_user: print("Error: Debes iniciar sesión para registrar transacciones."); return
    print("\n--- Registrar Nueva Transacción ---")
    available_assets = db.query(models.Asset).filter(models.Asset.owner_id == current_logged_in_user.id).all()
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
            if price_per_unit < 0: raise ValueError("Precio no puede ser negativo.")
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
            db=db, owner_id=current_logged_in_user.id, asset_id=selected_asset.id,
            transaction_type=selected_transaction_type, quantity=quantity,
            price_per_unit=price_per_unit, transaction_date=transaction_date,
            fees=fees, notes=notes)
        print(f"¡Transacción registrada exitosamente!")
    except Exception as e: print(f"Ocurrió un error al registrar transacción: {e}"); db.rollback()

def show_portfolio(db: Session):
    """Calcula y muestra las posiciones actuales y su valoración (requiere login)."""
    global current_logged_in_user
    if not current_logged_in_user: print("Error: Debes iniciar sesión para ver el portafolio."); return
    print("\n--- Ver Portafolio ---")
    try:
        positions = crud.get_user_positions(db, user_id=current_logged_in_user.id)
        if not positions: print("No tienes posiciones abiertas."); return
        symbols = [asset.symbol for asset in positions.keys()]
        current_prices = crud.get_current_prices(symbols)
        portfolio_data = []
        total_portfolio_value = 0.0
        print(f"\n--- Resumen del Portafolio para {current_logged_in_user.username} ---")
        for asset, quantity in positions.items():
            current_price = current_prices.get(asset.symbol)
            market_value_num = None
            if current_price is not None:
                market_value_num = quantity * current_price
                total_portfolio_value += market_value_num
                market_value_str = f'{market_value_num:,.2f}'; current_price_str = f'{current_price:,.2f}'
            else:
                market_value_str = "N/A"; current_price_str = "N/A"
                print(f"Advertencia: No se pudo obtener el precio actual para {asset.symbol}")
            portfolio_data.append({"Símbolo": asset.symbol, "Nombre": asset.name, "Cantidad": quantity,
                                   "Precio Actual": current_price_str, "Valor Mercado": market_value_str})
        if portfolio_data:
            portfolio_df = pd.DataFrame(portfolio_data)
            portfolio_df['Cantidad'] = portfolio_df['Cantidad'].map('{:,.8f}'.format)
            print(portfolio_df.to_string(index=False))
            print("-" * 70)
            print(f"Valor Total Estimado del Portafolio: {total_portfolio_value:,.2f}")
        else: print("No se pudieron valorar las posiciones.")
    except Exception as e: print(f"Ocurrió un error al calcular el portafolio: {e}"); traceback.print_exc()


# --- Flujo Principal ---
if __name__ == "__main__":
    # La creación de tablas ahora debe hacerse con Alembic ANTES de ejecutar esto
    # print("Creando tablas si no existen (usando Base.metadata.create_all)...")
    # models.Base.metadata.create_all(bind=engine) # COMENTADO

    db = SessionLocal()
    try:
        while True:
            print("\n--- Menú Principal ---")
            if current_logged_in_user:
                print(f"(Sesión iniciada como: {current_logged_in_user.username})")
                print("1. Añadir Nuevo Activo")
                print("2. Registrar Nueva Transacción")
                print("3. Ver Portafolio")
                print("4. Cerrar Sesión (Logout)")
                print("5. Salir del Programa")
            else:
                print("1. Registrar Nuevo Usuario")
                print("2. Iniciar Sesión (Login)")
                print("3. Salir del Programa")

            choice = input("Elige una opción: ")

            if current_logged_in_user: # Menú si hay sesión iniciada
                if choice == '1': add_new_asset(db)
                elif choice == '2': add_new_transaction(db)
                elif choice == '3': show_portfolio(db)
                elif choice == '4': logout_user()
                elif choice == '5': print("Saliendo..."); break
                else: print("Opción no válida.")
            else: # Menú si NO hay sesión iniciada
                if choice == '1': register_new_user(db)
                elif choice == '2': login_user(db)
                elif choice == '3': print("Saliendo..."); break
                else: print("Opción no válida.")
    finally:
        print("Cerrando conexión a la base de datos.")
        db.close()