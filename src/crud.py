# src/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func
import bcrypt
from . import models # RELATIVA
from datetime import datetime
from collections import defaultdict
import math
import yfinance as yf
import pandas as pd
import traceback # Añadido para posible depuración más detallada

# --- Funciones para User ---

def get_user_by_email(db: Session, email: str):
    """Busca un usuario por su email."""
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    """Busca un usuario por su nombre de usuario."""
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, username: str, email: str, password: str):
    """Crea un nuevo usuario con contraseña hasheada."""
    hashed_password_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashed_password_str = hashed_password_bytes.decode('utf-8') # Guardar como string
    db_user = models.User(username=username, email=email, hashed_password=hashed_password_str)
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        print(f"Error al crear usuario en DB: {e}")
        raise # Re-lanzar la excepción para que la capa superior la maneje

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña plana coincide con un hash guardado."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        # Esto puede ocurrir si el hash guardado no es un hash bcrypt válido
        print(f"Advertencia: Se encontró un hash de contraseña inválido en la base de datos.")
        return False


# --- Funciones para Asset ---

def get_asset_by_symbol(db: Session, symbol: str, owner_id: int):
    """Busca un activo por su símbolo y propietario."""
    # Normalizar símbolo a mayúsculas para consistencia
    return db.query(models.Asset)\
             .filter(models.Asset.symbol == symbol.upper(), models.Asset.owner_id == owner_id)\
             .first()

def create_asset(db: Session, owner_id: int, symbol: str, name: str, asset_type: models.AssetType):
    """Crea un nuevo activo para un usuario."""
    symbol_upper = symbol.upper() # Guardar siempre en mayúsculas
    # Verificar si ya existe para este usuario
    existing_asset = get_asset_by_symbol(db, symbol=symbol_upper, owner_id=owner_id)
    if existing_asset:
        # Podríamos lanzar un error o simplemente devolver el existente
        # Por ahora, lanzaremos un error para evitar duplicados accidentales
        raise ValueError(f"El activo con símbolo '{symbol_upper}' ya existe para este usuario.")

    db_asset = models.Asset(symbol=symbol_upper, name=name, asset_type=asset_type, owner_id=owner_id)
    try:
        db.add(db_asset)
        db.commit()
        db.refresh(db_asset)
        return db_asset
    except Exception as e:
        db.rollback()
        print(f"Error al crear activo en DB: {e}")
        raise


# --- Funciones para Transaction ---

def create_transaction(db: Session, owner_id: int, asset_id: int,
                       transaction_type: models.TransactionType, quantity: float, price_per_unit: float,
                       transaction_date: datetime, fees: float = 0.0, notes: str = None):
    """Crea una nueva transacción."""
    # Validaciones básicas
    if quantity <= 0:
        raise ValueError("La cantidad de la transacción debe ser positiva.")
    if price_per_unit < 0:
        raise ValueError("El precio por unidad no puede ser negativo.")
    if fees < 0:
        raise ValueError("Las comisiones no pueden ser negativas.")

    # Asegurarse de que el activo pertenece al usuario (medida de seguridad)
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id, models.Asset.owner_id == owner_id).first()
    if not asset:
        raise ValueError(f"Activo con ID {asset_id} no encontrado o no pertenece al usuario {owner_id}.")

    db_transaction = models.Transaction(
        owner_id=owner_id,
        asset_id=asset_id,
        transaction_type=transaction_type,
        quantity=quantity, # SQLAlchemy manejará la conversión a Numeric
        price_per_unit=price_per_unit,
        transaction_date=transaction_date,
        fees=fees,
        notes=notes
    )
    try:
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        return db_transaction
    except Exception as e:
        db.rollback()
        print(f"Error al crear transacción en DB: {e}")
        raise

def get_transactions_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Obtiene las transacciones de un usuario, paginadas."""
    return db.query(models.Transaction)\
             .filter(models.Transaction.owner_id == user_id)\
             .order_by(models.Transaction.transaction_date.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()

def get_transactions_by_asset(db: Session, asset_id: int, user_id: int, skip: int = 0, limit: int = 100):
    """Obtiene las transacciones de un activo específico para un usuario, paginadas."""
    # Añadido filtro por user_id por seguridad/lógica
    return db.query(models.Transaction)\
             .filter(models.Transaction.asset_id == asset_id, models.Transaction.owner_id == user_id)\
             .order_by(models.Transaction.transaction_date.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()


# --- Funciones de Lógica de Portafolio ---

def get_user_positions(db: Session, user_id: int) -> dict[models.Asset, float]:
    """
    Calcula las posiciones actuales (cantidad neta) de cada activo para un usuario.
    Retorna un diccionario mapeando objeto Asset a cantidad (float).
    """
    # print(f"\n--- Calculando posiciones para User ID: {user_id} ---") # Descomentar si necesitas depurar
    transactions = db.query(models.Transaction)\
                     .filter(models.Transaction.owner_id == user_id)\
                     .order_by(models.Transaction.asset_id, models.Transaction.transaction_date)\
                     .all() # Carga todas las transacciones del usuario

    # Usamos defaultdict para simplificar la acumulación
    # La clave será asset_id, el valor la cantidad neta (como float inicialmente)
    positions_by_asset_id = defaultdict(float)

    for t in transactions:
        # Convertir la cantidad de Numeric/Decimal a float para este cálculo simple
        # ¡PRECAUCIÓN! Para cálculos financieros más complejos (coste base, P&L),
        # es MUY recomendable usar el tipo Decimal. Aquí solo calculamos cantidad neta.
        quantity = float(t.quantity)

        if t.transaction_type == models.TransactionType.BUY:
            positions_by_asset_id[t.asset_id] += quantity
        elif t.transaction_type == models.TransactionType.SELL:
            positions_by_asset_id[t.asset_id] -= quantity
        # Podríamos añadir otros tipos como DIVIDEND, SPLIT, etc. en el futuro

    # Ahora, filtramos las posiciones con cantidad cercana a cero y obtenemos los objetos Asset
    final_positions = {}
    asset_ids_with_holdings = [
        asset_id for asset_id, quantity in positions_by_asset_id.items()
        if not math.isclose(quantity, 0, abs_tol=1e-9) # Usar tolerancia para comparar floats
    ]

    if asset_ids_with_holdings:
        # Hacemos una sola consulta para obtener todos los Assets necesarios
        assets = db.query(models.Asset).filter(models.Asset.id.in_(asset_ids_with_holdings)).all()
        # Creamos un mapa de asset_id -> Asset para fácil acceso
        asset_map = {asset.id: asset for asset in assets}

        # Construimos el diccionario final {Asset: cantidad}
        for asset_id in asset_ids_with_holdings:
            asset = asset_map.get(asset_id)
            if asset: # Asegurarnos de que el asset se encontró
                final_positions[asset] = positions_by_asset_id[asset_id]

    # print(f"Posiciones calculadas: {len(final_positions)} activos con holdings.") # Descomentar si necesitas depurar
    return final_positions


# --- Funciones de Datos de Mercado ---

def get_current_prices(symbols: list[str]) -> dict[str, float]:
    """
    Obtiene el precio actual para una lista de símbolos usando yfinance.
    Retorna un diccionario {symbol: price}.
    Maneja errores de forma básica e informa si no se obtienen precios.
    """
    if not symbols:
        print("[!] No se proporcionaron símbolos para obtener precios.")
        return {}

    print(f"\n--- Obteniendo precios actuales para: {', '.join(symbols)} ---")
    prices = {}
    try:
        # Usar tickers para obtener info más detallada y manejar mejor errores individuales
        tickers = yf.Tickers(symbols)
        # Acceder al historial reciente (1 día es suficiente para el último precio)
        # Usamos history() que suele ser más robusto que download() para precios recientes
        hist = tickers.history(period="1d", progress=False)

        if hist.empty:
            print("[!] yfinance no devolvió datos de historial.")
            return {}

        # El precio que nos interesa suele ser 'Close' o 'Adj Close'
        # 'Adj Close' (Adjusted Close) es generalmente preferible si existe
        price_col = 'Close' # Usar 'Close' como fallback
        if 'Adj Close' in hist.columns:
             # Verificar si 'Adj Close' tiene datos no nulos recientes
             if hist['Adj Close'].notna().any():
                 price_col = 'Adj Close'

        # Extraer el último precio válido para cada símbolo
        # El DataFrame puede tener un MultiIndex (Price Type, Symbol) o solo Symbol si es un solo ticker
        if isinstance(hist.columns, pd.MultiIndex):
            # Caso MultiIndex: ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'], [Symbol1, Symbol2,...]
            if price_col in hist.columns.levels[0]:
                # Seleccionar la columna de precios y luego el último índice (fecha más reciente)
                last_prices_series = hist[price_col].iloc[-1]
                # Convertir a diccionario, filtrando NaNs
                prices = {symbol: float(price) for symbol, price in last_prices_series.items() if pd.notna(price)}
            else:
                 print(f"[!] Advertencia: No se encontró la columna de precios '{price_col}' en el MultiIndex.")
        elif len(symbols) == 1 and not hist.empty:
             # Caso un solo símbolo: Columnas son ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
             if price_col in hist.columns:
                 last_price = hist[price_col].iloc[-1]
                 if pd.notna(last_price):
                     prices[symbols[0]] = float(last_price)
                 else:
                     print(f"[!] No se encontró precio válido ('{price_col}') para {symbols[0]}.")
             else:
                 print(f"[!] Advertencia: No se encontró la columna de precios '{price_col}' para {symbols[0]}.")
        else:
             # Podría ser otro formato inesperado o un DataFrame vacío después de filtrar
             print("[!] Formato de datos de yfinance inesperado o vacío después del procesamiento.")


    except Exception as e:
        print(f"[!!!] Error crítico obteniendo precios de yfinance: {e}")
        # Podrías querer registrar el traceback completo en un archivo de log
        # traceback.print_exc()

    # Filtrar cualquier NaN que pudiera quedar (aunque el código anterior intenta evitarlo)
    valid_prices = {symbol: price for symbol, price in prices.items() if not math.isnan(price)}

    if not valid_prices:
        print("[!] No se pudieron obtener precios válidos para ningún símbolo solicitado.")
    else:
        print(f"[*] Precios obtenidos válidamente para {len(valid_prices)} de {len(symbols)} símbolos.")
        # Opcional: Imprimir qué símbolos fallaron
        failed_symbols = set(symbols) - set(valid_prices.keys())
        if failed_symbols:
            print(f"[!] No se obtuvo precio para: {', '.join(failed_symbols)}")


    # --- ¡CORRECCIÓN CRÍTICA! ---
    # Asegurarse de devolver el diccionario correcto.
    return valid_prices