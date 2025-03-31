# src/__main__.py (VERIFICACIÓN RESTAURADA, DEBUG ELIMINADO)
# --- Importaciones ---
from .database import SessionLocal, engine, Base
from . import models
from . import crud
from sqlalchemy.orm import Session
from datetime import datetime
import pandas as pd
import traceback
import getpass
import sys
import os
from decimal import Decimal, ROUND_HALF_UP

# --- Variable global ---
current_logged_in_user: models.User | None = None

# --- Función para limpiar pantalla ---
def clear_screen():
    """Limpia la pantalla de la terminal (multiplataforma)."""
    if sys.platform.startswith('win'): os.system('cls')
    else: os.system('clear')

# --- Funciones UI ---
def register_new_user(db: Session):
    """Registra un nuevo usuario."""
    print("\n--- Registrar Nuevo Usuario ---")
    while True:
        username = input("Nombre de usuario: ").strip()
        if not username: print("El nombre de usuario no puede estar vacío."); continue
        existing_user = crud.get_user_by_username(db, username=username)
        if existing_user: print(f"Error: El nombre de usuario '{username}' ya existe."); continue
        break
    while True:
        email = input("Email: ").strip()
        if not email or "@" not in email or "." not in email: print("Introduce un email válido."); continue
        existing_email = crud.get_user_by_email(db, email=email)
        if existing_email: print(f"Error: El email '{email}' ya está registrado."); continue
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
        input("Presiona Enter para continuar...")
    except Exception as e:
        print(f"\nOcurrió un error inesperado al crear usuario: {e}")
        input("Presiona Enter para continuar...")

def login_user(db: Session):
    """Maneja el inicio de sesión del usuario."""
    global current_logged_in_user
    print("\n--- Iniciar Sesión ---")
    if current_logged_in_user:
        print(f"Ya has iniciado sesión como '{current_logged_in_user.username}'.")
        input("Presiona Enter para continuar...")
        return
    username = input("Nombre de usuario: ")
    password = getpass.getpass("Contraseña: ")
    user = crud.get_user_by_username(db, username=username)
    if user and crud.verify_password(password, user.hashed_password):
        current_logged_in_user = user
        print(f"\n¡Bienvenido, {user.username}!")
    else:
        print("\nError: Nombre de usuario o contraseña incorrectos.")
        current_logged_in_user = None
    input("Presiona Enter para continuar...")

def logout_user():
    """Maneja el cierre de sesión."""
    global current_logged_in_user
    if current_logged_in_user:
        print(f"\nCerrando sesión de '{current_logged_in_user.username}'.")
        current_logged_in_user = None
    else:
        print("\nNo has iniciado sesión.")
    input("Presiona Enter para continuar...")

def add_new_asset(db: Session):
    """Función para añadir un nuevo activo (requiere login)."""
    global current_logged_in_user
    if not current_logged_in_user: print("\nError: Debes iniciar sesión."); input("Presiona Enter..."); return
    print("\n--- Añadir Nuevo Activo ---")
    while True:
        symbol = input("Símbolo del activo (ej. AAPL, BTC-USD): ").strip().upper()
        if not symbol: print("El símbolo no puede estar vacío."); continue
        existing_asset = crud.get_asset_by_symbol(db, symbol=symbol, owner_id=current_logged_in_user.id)
        if existing_asset: print(f"Advertencia: Ya tienes registrado '{symbol}'."); input("Presiona Enter..."); return
        break
    while True:
        name = input("Nombre del activo (ej. Apple Inc.): ").strip()
        if name:
            break
        else:
            print("El nombre del activo no puede estar vacío.")
    print("\nTipos de Activo Disponibles:")
    asset_types = list(models.AssetType)
    for i, asset_type in enumerate(asset_types): print(f"{i + 1}. {asset_type.name}")
    while True:
        try:
            choice = int(input(f"Selecciona el tipo (1-{len(asset_types)}): "))
            if 1 <= choice <= len(asset_types): selected_type = asset_types[choice - 1]; break
            else: print("Opción inválida.")
        except ValueError: print("Entrada inválida.")
    try:
        new_asset = crud.create_asset(db=db, owner_id=current_logged_in_user.id, symbol=symbol, name=name, asset_type=selected_type)
        print(f"\n¡Activo '{new_asset.symbol}' añadido!")
    except ValueError as ve: print(f"\nError: {ve}")
    except Exception as e: print(f"\nError inesperado: {e}")
    input("Presiona Enter...")

def add_new_transaction(db: Session):
    """Función para registrar una nueva transacción (requiere login)."""
    global current_logged_in_user
    if not current_logged_in_user: print("\nError: Debes iniciar sesión."); input("Presiona Enter..."); return
    print("\n--- Registrar Nueva Transacción ---")
    available_assets = db.query(models.Asset).filter(models.Asset.owner_id == current_logged_in_user.id).order_by(models.Asset.symbol).all()
    if not available_assets: print("\nError: No tienes activos registrados."); input("Presiona Enter..."); return
    print("\nActivos Disponibles:"); [print(f"{i + 1}. {a.symbol}") for i, a in enumerate(available_assets)]
    while True:
        try: choice = int(input(f"Selecciona activo (1-{len(available_assets)}): ")); selected_asset = available_assets[choice - 1]; break
        except (ValueError, IndexError): print("Selección inválida.")
    print("\nTipos de Transacción:"); transaction_types = list(models.TransactionType); [print(f"{i + 1}. {t.name}") for i, t in enumerate(transaction_types)]
    while True:
        try: choice = int(input(f"Selecciona tipo (1-{len(transaction_types)}): ")); selected_transaction_type = transaction_types[choice - 1]; break
        except (ValueError, IndexError): print("Selección inválida.")
    while True:
        try: quantity_str = input("Cantidad: ").strip(); quantity = float(quantity_str); break
        except ValueError: print("Cantidad inválida. Usa '.' como decimal.") # Añadir pista
    while True:
        try: price_str = input("Precio por unidad: ").strip(); price_per_unit = float(price_str); break
        except ValueError: print("Precio inválido. Usa '.' como decimal.") # Añadir pista
    while True:
        date_str = input("Fecha (YYYY-MM-DD HH:MM:SS) [Enter para ahora]: ").strip()
        if not date_str: transaction_date = datetime.now(); print(f"Usando: {transaction_date:%Y-%m-%d %H:%M:%S}"); break
        try: transaction_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S'); break
        except ValueError:
            try: transaction_date = datetime.strptime(date_str, '%Y-%m-%d'); print(f"Usando: {transaction_date:%Y-%m-%d} 00:00:00"); break
            except ValueError: print("Formato inválido. Usa YYYY-MM-DD o YYYY-MM-DD HH:MM:SS.")
    while True:
        fees_str = input("Comisiones [Enter para 0]: ").strip(); fees = 0.0
        if not fees_str: break
        try: fees = float(fees_str); break
        except ValueError: print("Comisión inválida. Usa '.' como decimal.") # Añadir pista
    notes = input("Notas (opcional): ").strip()
    try:
        new_transaction = crud.create_transaction(db=db, owner_id=current_logged_in_user.id, asset_id=selected_asset.id, transaction_type=selected_transaction_type, quantity=quantity, price_per_unit=price_per_unit, transaction_date=transaction_date, fees=fees, notes=notes)
        # Mostrar con formato Decimal desde el objeto devuelto
        print(f"\n¡Transacción ({new_transaction.transaction_type.name} {new_transaction.quantity:.8f} {selected_asset.symbol} @ {new_transaction.price_per_unit:.4f}) registrada!")
    except ValueError as ve: print(f"\nError: {ve}")
    except Exception as e: print(f"\nError inesperado: {e}")
    input("Presiona Enter...")

def show_portfolio(db: Session):
    """Muestra el portafolio detallado con P&L."""
    global current_logged_in_user
    if not current_logged_in_user: print("\nError: Debes iniciar sesión."); input("Presiona Enter..."); return
    print("\n--- Ver Portafolio Detallado ---")
    try:
        portfolio_details = crud.get_portfolio_performance(db, user_id=current_logged_in_user.id)
        if not portfolio_details: print("\nNo tienes posiciones abiertas."); input("Presiona Enter..."); return
        portfolio_data = []; total_portfolio_market_value = Decimal(0); total_portfolio_cost_basis = Decimal(0)
        print(f"\n--- Resumen del Portafolio para {current_logged_in_user.username} ---")
        sorted_symbols = sorted(portfolio_details.keys())
        for symbol in sorted_symbols:
            data = portfolio_details[symbol]; asset = data["asset"]; quantity = data["quantity"]; avg_cost = data["average_cost_basis"]; total_cost = data["total_cost_basis"]; current_price = data["current_price"]; market_value = data["market_value"]; unrealized_pnl = data["unrealized_pnl"]; unrealized_pnl_percent = data["unrealized_pnl_percent"]
            if market_value is not None: total_portfolio_market_value += market_value
            if total_cost is not None: total_portfolio_cost_basis += total_cost
            quantity_str = f"{quantity.quantize(Decimal('0.00000001'), ROUND_HALF_UP):,f}".rstrip('0').rstrip('.')
            avg_cost_str = f"{avg_cost.quantize(Decimal('0.0001'), ROUND_HALF_UP):,f}" if avg_cost is not None else "N/A"
            total_cost_str = f"{total_cost.quantize(Decimal('0.01'), ROUND_HALF_UP):,f}" if total_cost is not None else "N/A"
            current_price_str = f"{current_price.quantize(Decimal('0.0001'), ROUND_HALF_UP):,f}" if current_price is not None else "N/A"
            market_value_str = f"{market_value.quantize(Decimal('0.01'), ROUND_HALF_UP):,f}" if market_value is not None else "N/A"
            unrealized_pnl_str = f"{unrealized_pnl.quantize(Decimal('0.01'), ROUND_HALF_UP):,f}" if unrealized_pnl is not None else "N/A"
            unrealized_pnl_percent_str = f"{unrealized_pnl_percent.quantize(Decimal('0.01'), ROUND_HALF_UP):,f}%" if unrealized_pnl_percent is not None else "N/A"
            portfolio_data.append({"Símbolo": symbol, "Cantidad": quantity_str, "Coste Medio": avg_cost_str, "Coste Total": total_cost_str, "Precio Act.": current_price_str, "Valor Mercado": market_value_str, "P&L No Real.": unrealized_pnl_str, "% P&L": unrealized_pnl_percent_str})
        if portfolio_data:
            portfolio_df = pd.DataFrame(portfolio_data); pd.set_option('display.max_rows', None); pd.set_option('display.max_columns', None); pd.set_option('display.width', 1000); pd.set_option('display.colheader_justify', 'center')
            print(portfolio_df.to_string(index=False))
            total_unrealized_pnl = total_portfolio_market_value - total_portfolio_cost_basis; total_unrealized_pnl_percent = Decimal(0)
            if total_portfolio_cost_basis > crud.ZERO_TOLERANCE: total_unrealized_pnl_percent = (total_unrealized_pnl / total_portfolio_cost_basis) * Decimal(100)
            print("-" * len(portfolio_df.columns) * 15) # Ajustar separador si es necesario
            print("\n--- Totales del Portafolio ---")
            print(f"Coste Total Base        : {total_portfolio_cost_basis.quantize(Decimal('0.01'), ROUND_HALF_UP):>20,f}")
            print(f"Valor de Mercado Total  : {total_portfolio_market_value.quantize(Decimal('0.01'), ROUND_HALF_UP):>20,f}")
            print(f"P&L No Realizado Total  : {total_unrealized_pnl.quantize(Decimal('0.01'), ROUND_HALF_UP):>20,f}")
            print(f"% P&L No Realizado Total: {total_unrealized_pnl_percent.quantize(Decimal('0.01'), ROUND_HALF_UP):>19,f}%")
        else: print("\nNo se pudieron obtener detalles del portafolio.")
    except Exception as e: print(f"\nError al mostrar portafolio: {e}"); traceback.print_exc()
    input("\nPresiona Enter para continuar...")

def view_transactions(db: Session):
    """Muestra todas las transacciones del usuario."""
    global current_logged_in_user
    if not current_logged_in_user: print("\nError: Debes iniciar sesión."); input("Presiona Enter..."); return
    print("\n--- Ver Historial de Transacciones ---")
    transactions = crud.get_transactions_by_user(db, user_id=current_logged_in_user.id, limit=1000)
    if not transactions: print("\nNo tienes transacciones registradas."); input("Presiona Enter..."); return
    transaction_data = []
    asset_ids = list(set(t.asset_id for t in transactions))
    assets = db.query(models.Asset).filter(models.Asset.id.in_(asset_ids)).all()
    asset_map = {a.id: a.symbol for a in assets}
    print(f"\n--- Transacciones para {current_logged_in_user.username} ---")
    # Ordenar transacciones por fecha descendente para la visualización
    transactions.sort(key=lambda t: t.transaction_date, reverse=True)
    for t in transactions:
        symbol = asset_map.get(t.asset_id, "Desconocido")
        quantity_str = f"{t.quantity.quantize(Decimal('0.00000001'), ROUND_HALF_UP):,f}".rstrip('0').rstrip('.')
        price_str = f"{t.price_per_unit.quantize(Decimal('0.0001'), ROUND_HALF_UP):,f}"
        fees_str = f"{t.fees.quantize(Decimal('0.01'), ROUND_HALF_UP):,f}" if t.fees is not None else "0.00"
        total_val = (t.quantity * t.price_per_unit).quantize(Decimal('0.01'), ROUND_HALF_UP)
        total_val_str = f"{total_val:,f}"
        transaction_data.append({
            "ID": t.id,
            "Fecha": t.transaction_date.strftime('%Y-%m-%d %H:%M'),
            "Tipo": t.transaction_type.name,
            "Símbolo": symbol,
            "Cantidad": quantity_str,
            "Precio Unit.": price_str,
            "Comisiones": fees_str,
            "Valor Total": total_val_str,
            "Notas": t.notes if t.notes else ""
        })
    if transaction_data:
        trans_df = pd.DataFrame(transaction_data)
        pd.set_option('display.max_rows', None); pd.set_option('display.max_columns', None); pd.set_option('display.width', 120); pd.set_option('display.colheader_justify', 'center')
        print(trans_df.to_string(index=False))
    else: print("\nNo se pudieron mostrar las transacciones.")
    input("\nPresiona Enter para continuar...")

# --- Flujo Principal ---
if __name__ == "__main__":
    # --- Verificación Inicial de Base de Datos (RESTAURADA) ---
    try:
        connection = engine.connect()
        connection.close()
        print("[*] Conexión inicial a la base de datos exitosa.")
    except Exception as e:
        print(f"[!!!] Error CRÍTICO al conectar a la base de datos: {e}")
        print(f"URL: {crud.DATABASE_URL}") # Mostrar URL usada
        print("Verifica la ruta y ejecuta 'alembic upgrade head' si es necesario."); sys.exit(1)

    # Crear sesión principal para la aplicación
    db = SessionLocal()
    try:
        while True:
            clear_screen()
            print("\n--- Portfolio Tracker ---"); print("-" * 25)
            if current_logged_in_user:
                print(f"(Sesión iniciada: {current_logged_in_user.username})")
                print("\n--- Menú Principal ---")
                print("1. Añadir Nuevo Activo")
                print("2. Registrar Nueva Transacción")
                print("3. Ver Portafolio Detallado")
                print("4. Ver Historial de Transacciones")
                print("5. Cerrar Sesión (Logout)")
                print("6. Salir del Programa")
                choice_range = (1, 6)
            else:
                print("\n--- Menú Principal ---")
                print("1. Registrar Nuevo Usuario")
                print("2. Iniciar Sesión (Login)")
                print("3. Salir del Programa")
                choice_range = (1, 3)

            choice = input(f"Elige una opción ({choice_range[0]}-{choice_range[1]}): ")

            if current_logged_in_user:
                if choice == '1': add_new_asset(db)
                elif choice == '2': add_new_transaction(db)
                elif choice == '3': show_portfolio(db)
                elif choice == '4': view_transactions(db)
                elif choice == '5': logout_user()
                elif choice == '6': print("\nSaliendo..."); break
                else: print("\nOpción no válida."); input("Presiona Enter...")
            else:
                if choice == '1': register_new_user(db)
                elif choice == '2': login_user(db)
                elif choice == '3': print("\nSaliendo..."); break
                else: print("\nOpción no válida."); input("Presiona Enter...")
    # --- Manejo de errores generales y cierre de sesión ---
    except KeyboardInterrupt: # Capturar Ctrl+C
        print("\n\nInterrupción por teclado detectada. Saliendo...")
    except Exception as main_e: # Capturar cualquier otro error inesperado en el bucle principal
        print("\n[!!!] Ocurrió un error inesperado en la aplicación:")
        traceback.print_exc() # Imprimir el traceback completo
        input("Presiona Enter para intentar continuar o salir...") # Pausa para ver el error
    finally:
        print("[*] Cerrando conexión principal a la base de datos.")
        db.close()