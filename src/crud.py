# src/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, inspect
import bcrypt
from . import models # RELATIVA
from datetime import datetime
from collections import defaultdict
import math
import yfinance as yf
import pandas as pd
import traceback # Añadido para posible depuración más detallada
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation # Importar Decimal y excepciones

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
        # Asegurarse que el hash es un string antes de codificarlo
        if isinstance(hashed_password, str):
            hashed_password_bytes = hashed_password.encode('utf-8')
        else:
             # Si no es string (quizás None o algo inesperado), la verificación falla
             print(f"Advertencia: Hash de contraseña inválido encontrado (tipo: {type(hashed_password)}).")
             return False
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_bytes)
    except ValueError as e:
        # Esto puede ocurrir si el hash guardado no es un hash bcrypt válido
        print(f"Advertencia: Error al verificar contraseña (posible hash inválido): {e}")
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
    try:
        # Convertir a Decimal aquí para validación y almacenamiento preciso
        dec_quantity = Decimal(str(quantity))
        dec_price = Decimal(str(price_per_unit))
        dec_fees = Decimal(str(fees)) if fees is not None else Decimal(0)
    except InvalidOperation as e:
        raise ValueError(f"Valor numérico inválido proporcionado: {e}")

    if dec_quantity <= Decimal(0):
        raise ValueError("La cantidad de la transacción debe ser positiva.")
    if dec_price < Decimal(0):
        raise ValueError("El precio por unidad no puede ser negativo.")
    if dec_fees < Decimal(0):
        raise ValueError("Las comisiones no pueden ser negativas.")

    # Asegurarse de que el activo pertenece al usuario (medida de seguridad)
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id, models.Asset.owner_id == owner_id).first()
    if not asset:
        raise ValueError(f"Activo con ID {asset_id} no encontrado o no pertenece al usuario {owner_id}.")

    db_transaction = models.Transaction(
        owner_id=owner_id,
        asset_id=asset_id,
        transaction_type=transaction_type,
        # Guardar como Decimal (SQLAlchemy maneja la conversión a Numeric)
        quantity=dec_quantity,
        price_per_unit=dec_price,
        transaction_date=transaction_date,
        fees=dec_fees,
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

# Constante para comparaciones con cero usando Decimal
ZERO_TOLERANCE = Decimal('1e-9')

def get_portfolio_performance(db: Session, user_id: int) -> dict:
    """
    Calcula las posiciones, coste base ponderado, valor de mercado y P&L para un usuario.
    Utiliza Decimal para todos los cálculos financieros.

    Retorna un diccionario:
    {
        asset_symbol: {
            "asset": models.Asset,
            "quantity": Decimal,
            "average_cost_basis": Decimal | None, # Coste medio por unidad
            "total_cost_basis": Decimal | None,   # Coste total de la posición actual
            "current_price": Decimal | None,      # Precio actual por unidad
            "market_value": Decimal | None,       # Valor de mercado total de la posición
            "unrealized_pnl": Decimal | None,     # Ganancia/Pérdida no realizada
            "unrealized_pnl_percent": Decimal | None # % P&L no realizado
        },
        ...
    }
    """
    print(f"\n--- Calculando rendimiento del portafolio para User ID: {user_id} ---")

    # Obtener todas las transacciones del usuario, ordenadas por activo y fecha
    # Unir con Asset para tener la info del activo disponible
    transactions = db.query(models.Transaction)\
                     .filter(models.Transaction.owner_id == user_id)\
                     .join(models.Asset)\
                     .order_by(models.Transaction.asset_id, models.Transaction.transaction_date)\
                     .all()

    if not transactions:
        print("[*] No se encontraron transacciones para este usuario.")
        return {}

    # Diccionarios para rastrear el estado por asset_id
    # Usamos Decimal para todos los cálculos
    positions = defaultdict(lambda: {"quantity": Decimal(0), "total_cost": Decimal(0), "asset": None})
    # Para P&L realizado (aunque no lo mostremos aún, es bueno calcularlo)
    # realized_pnl_details = defaultdict(lambda: {"total_proceeds": Decimal(0), "cost_of_sold_assets": Decimal(0)})
    asset_avg_cost = {} # {asset_id: current_avg_cost_per_unit}

    print(f"[*] Procesando {len(transactions)} transacciones...")

    for t in transactions:
        asset_id = t.asset_id
        # Asegurarse de que los datos de la DB (Numeric) se traten como Decimal
        # Si ya son Decimal (depende del driver DBAPI), la conversión no hace daño.
        try:
            quantity = Decimal(t.quantity) if t.quantity is not None else Decimal(0)
            price = Decimal(t.price_per_unit) if t.price_per_unit is not None else Decimal(0)
            fees = Decimal(t.fees) if t.fees is not None else Decimal(0)
        except (TypeError, InvalidOperation) as e:
             print(f"[!] Advertencia: Datos inválidos en transacción ID {t.id}. Saltando. Error: {e}")
             continue # Saltar esta transacción si los datos son inválidos

        transaction_value = quantity * price
        current_pos = positions[asset_id]

        # Guardar el objeto Asset la primera vez que lo vemos
        if current_pos["asset"] is None:
            # Verificar si el objeto Asset está cargado (puede no estarlo si la sesión expiró)
            insp = inspect(t)
            if 'asset' not in insp.unloaded:
                current_pos["asset"] = t.asset
            else:
                # Si no está cargado, recargarlo (esto es menos eficiente)
                print(f"[!] Recargando Asset ID {asset_id}...")
                current_pos["asset"] = db.query(models.Asset).get(asset_id)
                if current_pos["asset"] is None:
                     print(f"[!!!] Error crítico: No se pudo encontrar Asset ID {asset_id} asociado a transacción {t.id}.")
                     continue # Saltar si no podemos obtener el Asset

        if t.transaction_type == models.TransactionType.BUY:
            # Coste total de esta compra (incluyendo comisiones)
            cost_of_this_buy = transaction_value + fees

            # Actualizar cantidad total y coste total acumulado
            new_total_quantity = current_pos["quantity"] + quantity
            new_total_cost = current_pos["total_cost"] + cost_of_this_buy

            # Recalcular coste medio ponderado por unidad
            if new_total_quantity > ZERO_TOLERANCE:
                asset_avg_cost[asset_id] = new_total_cost / new_total_quantity
            else:
                # Si la cantidad es cero o negativa (raro en compra, pero por si acaso)
                asset_avg_cost[asset_id] = Decimal(0)
                new_total_cost = Decimal(0) # Resetear coste si cantidad es cero

            # Actualizar la posición
            current_pos["quantity"] = new_total_quantity
            current_pos["total_cost"] = new_total_cost

        elif t.transaction_type == models.TransactionType.SELL:
            # Coste de los activos vendidos (usando el coste medio ANTES de esta venta)
            avg_cost_at_sale = asset_avg_cost.get(asset_id, Decimal(0))
            cost_of_assets_sold = quantity * avg_cost_at_sale

            # Ingresos netos de esta venta (descontando comisiones)
            proceeds_of_this_sale = transaction_value - fees

            # Calcular P&L Realizado para esta venta (opcional por ahora)
            # realized_pnl = proceeds_of_this_sale - cost_of_assets_sold
            # realized_pnl_details[asset_id]["total_proceeds"] += proceeds_of_this_sale
            # realized_pnl_details[asset_id]["cost_of_sold_assets"] += cost_of_assets_sold

            # Actualizar cantidad total
            new_total_quantity = current_pos["quantity"] - quantity

            # Actualizar coste total acumulado: reducir el coste proporcionalmente
            # El coste total restante es la nueva cantidad por el coste medio (que no cambia en una venta)
            if new_total_quantity > ZERO_TOLERANCE:
                 new_total_cost = new_total_quantity * avg_cost_at_sale
            else:
                # Si la cantidad llega a cero o menos, el coste total es cero
                new_total_quantity = Decimal(0) # Asegurar que no sea negativo
                new_total_cost = Decimal(0)
                asset_avg_cost[asset_id] = Decimal(0) # Resetear coste medio si se vende todo

            # Actualizar la posición
            current_pos["quantity"] = new_total_quantity
            current_pos["total_cost"] = new_total_cost

    # --- Fin del bucle de transacciones ---

    # Filtrar posiciones cerradas y preparar resultado final
    final_portfolio = {}
    symbols_to_fetch = []
    print("[*] Construyendo resumen del portafolio...")
    for asset_id, data in positions.items():
        quantity = data["quantity"]
        asset = data["asset"]

        # Si no pudimos cargar el asset por alguna razón, lo saltamos
        if asset is None:
            print(f"[!] Advertencia: No se pudo determinar el activo para asset_id {asset_id}. Saltando.")
            continue

        # Considerar solo posiciones con cantidad positiva significativa
        if quantity > ZERO_TOLERANCE:
            symbols_to_fetch.append(asset.symbol)
            avg_cost = asset_avg_cost.get(asset_id)
            # El coste total de la posición actual es cantidad * coste medio
            total_cost = quantity * avg_cost if avg_cost is not None else None

            final_portfolio[asset.symbol] = {
                "asset": asset,
                "quantity": quantity,
                "average_cost_basis": avg_cost,
                "total_cost_basis": total_cost,
                "current_price": None, # Se llenará después
                "market_value": None,
                "unrealized_pnl": None,
                "unrealized_pnl_percent": None
            }
        # else: # Opcional: Informar sobre posiciones cerradas
        #     print(f"[*] Posición cerrada para {asset.symbol} (Cantidad: {quantity})")


    if not final_portfolio:
        print("[*] No hay posiciones abiertas en el portafolio.")
        return {}

    # Obtener precios actuales para los símbolos de las posiciones abiertas
    current_prices_float = get_current_prices(symbols_to_fetch) # Devuelve dict[str, float]

    # Convertir precios a Decimal y calcular valores finales
    print("[*] Calculando valores de mercado y P&L...")
    total_portfolio_market_value = Decimal(0)
    total_portfolio_cost_basis = Decimal(0)

    for symbol, data in final_portfolio.items():
        current_price_float = current_prices_float.get(symbol)

        if current_price_float is not None:
            try:
                current_price = Decimal(str(current_price_float)) # Convertir float a Decimal
                market_value = data["quantity"] * current_price

                data["current_price"] = current_price # Guardar como Decimal
                data["market_value"] = market_value
                total_portfolio_market_value += market_value

                if data["total_cost_basis"] is not None:
                    unrealized_pnl = market_value - data["total_cost_basis"]
                    data["unrealized_pnl"] = unrealized_pnl
                    total_portfolio_cost_basis += data["total_cost_basis"] # Sumar solo si tenemos coste

                    # Calcular porcentaje P&L solo si el coste base es positivo
                    if data["total_cost_basis"] > ZERO_TOLERANCE:
                        # Convertir a Decimal para la división
                        pnl_percent = (unrealized_pnl / data["total_cost_basis"]) * Decimal(100)
                        data["unrealized_pnl_percent"] = pnl_percent
                    else:
                        # Si el coste es cero o negativo, el % P&L no está definido o es infinito
                        data["unrealized_pnl_percent"] = None # O podrías poner Decimal('inf') o 0
                # else: # Si no hay coste base, no podemos calcular P&L
                     # print(f"[*] No se pudo calcular P&L para {symbol} (sin coste base)")

            except (InvalidOperation, TypeError) as e:
                print(f"[!] Error al procesar precio para {symbol}: {e}. Valor: {current_price_float}")
                # Dejar los campos relacionados con el precio como None
                data["current_price"] = None
                data["market_value"] = None
                data["unrealized_pnl"] = None
                data["unrealized_pnl_percent"] = None
        else:
            print(f"[!] No se obtuvo precio actual para {symbol}. No se puede calcular valor de mercado ni P&L.")
            # Los valores ya son None por defecto

    print(f"[*] Cálculo de rendimiento completado. {len(final_portfolio)} posiciones abiertas procesadas.")

    # Podrías añadir totales al diccionario devuelto si los necesitas fuera
    # final_portfolio["_totals"] = {
    #     "total_market_value": total_portfolio_market_value,
    #     "total_cost_basis": total_portfolio_cost_basis,
    #     "total_unrealized_pnl": total_portfolio_market_value - total_portfolio_cost_basis if total_portfolio_cost_basis > ZERO_TOLERANCE else Decimal(0)
    # }

    return final_portfolio


# --- Funciones de Datos de Mercado (sin cambios respecto a la versión anterior) ---

def get_current_prices(symbols: list[str]) -> dict[str, float]:
    """
    Obtiene el precio actual para una lista de símbolos usando yfinance.
    Retorna un diccionario {symbol: price}.
    Maneja errores de forma básica e informa si no se obtienen precios.
    """
    if not symbols:
        print("[!] No se proporcionaron símbolos para obtener precios.")
        return {}

    # Eliminar duplicados por si acaso
    unique_symbols = sorted(list(set(symbols)))
    symbols_str = " ".join(unique_symbols) # yfinance prefiere símbolos separados por espacio

    print(f"\n--- Obteniendo precios actuales para: {', '.join(unique_symbols)} ---")
    prices = {}
    try:
        # Usar tickers para obtener info más detallada y manejar mejor errores individuales
        tickers = yf.Tickers(symbols_str)

        # Acceder a la información rápida de los tickers, que suele incluir el precio actual
        # Esto puede ser más rápido que descargar historial para muchos tickers
        ticker_info = {}
        unprocessed_symbols = []
        for symbol in unique_symbols:
            try:
                 # Acceder al ticker individualmente puede ser más robusto
                 t = tickers.tickers.get(symbol)
                 if t:
                     info = t.fast_info
                     # Buscar el precio en 'last_price' o 'previous_close'
                     price = info.get('last_price', info.get('previous_close'))
                     if price is not None:
                         ticker_info[symbol] = float(price)
                     else:
                         print(f"[?] No se encontró 'last_price' o 'previous_close' para {symbol} en fast_info. Se intentará con historial.")
                         unprocessed_symbols.append(symbol)
                 else:
                     print(f"[!] No se pudo obtener objeto Ticker para {symbol}.")
                     unprocessed_symbols.append(symbol)

            except Exception as e_ticker:
                 print(f"[!] Error obteniendo fast_info para {symbol}: {e_ticker}. Se intentará con historial.")
                 unprocessed_symbols.append(symbol)


        # Intentar obtener historial para los símbolos que fallaron con fast_info
        if unprocessed_symbols:
             print(f"--- Intentando obtener historial para {len(unprocessed_symbols)} símbolos restantes...")
             hist = yf.download(unprocessed_symbols, period="1d", progress=False)
             if not hist.empty:
                 price_col = 'Close'
                 if 'Adj Close' in hist.columns and hist['Adj Close'].notna().any():
                     price_col = 'Adj Close'

                 if isinstance(hist.columns, pd.MultiIndex):
                     if price_col in hist.columns.levels[0]:
                         last_prices_series = hist[price_col].iloc[-1]
                         for symbol, price in last_prices_series.items():
                             if pd.notna(price):
                                 ticker_info[symbol] = float(price) # Añadir al diccionario principal
                     else:
                         print(f"[!] Advertencia: No se encontró '{price_col}' en MultiIndex del historial.")
                 else: # DataFrame simple (probablemente un solo símbolo restante)
                     if price_col in hist.columns:
                         last_price = hist[price_col].iloc[-1]
                         if pd.notna(last_price):
                              # El símbolo es el único en unprocessed_symbols
                              if len(unprocessed_symbols) == 1:
                                   ticker_info[unprocessed_symbols[0]] = float(last_price)
                         else:
                              print(f"[!] Precio de historial ('{price_col}') es NaN para {unprocessed_symbols}.")
                     else:
                          print(f"[!] Advertencia: No se encontró '{price_col}' en columnas del historial.")
             else:
                 print("[!] yfinance no devolvió datos de historial para símbolos restantes.")

        prices = ticker_info # Usar los precios obtenidos de fast_info y/o historial

    except Exception as e:
        print(f"[!!!] Error crítico durante la obtención de precios de yfinance: {e}")
        traceback.print_exc() # Imprimir traceback completo para depuración

    # Filtrar cualquier NaN o None que pudiera quedar
    valid_prices = {symbol: price for symbol, price in prices.items() if price is not None and not math.isnan(price)}

    if not valid_prices:
        print("[!] No se pudieron obtener precios válidos para ningún símbolo solicitado.")
    else:
        print(f"[*] Precios obtenidos válidamente para {len(valid_prices)} de {len(unique_symbols)} símbolos.")
        failed_symbols = set(unique_symbols) - set(valid_prices.keys())
        if failed_symbols:
            print(f"[!] No se obtuvo precio para: {', '.join(sorted(list(failed_symbols)))}")

    return valid_prices