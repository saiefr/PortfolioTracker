# src/crud.py
# --- Importaciones ---
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, case
from . import models
# Asegúrate de que passlib esté instalado en tu venv: pip install "passlib[bcrypt]"
from passlib.context import CryptContext
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
import yfinance as yf
import logging # Asegúrate de que logging esté importado
import os

# --- Configuración ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'portfolio.db')}"
# print(f"[*] Conectando a la base de datos: {DATABASE_URL}")

# getcontext().prec = 28

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ZERO_TOLERANCE = Decimal('1e-9')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Funciones de Utilidad ---
def verify_password(plain_password, hashed_password):
    # Asegúrate de que pwd_context esté definido antes de esta línea
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # Asegúrate de que pwd_context esté definido antes de esta línea
    return pwd_context.hash(password)

def get_current_price(symbol: str) -> Decimal | None:
    """
    Obtiene el precio de mercado actual para un símbolo usando yfinance.
    Intenta con fast_info y luego con history.
    Retorna Decimal o None si falla.
    """
    try:
        ticker = yf.Ticker(symbol)
        last_price = ticker.fast_info.get('last_price')
        if last_price is not None:
            try:
                price_dec = Decimal(str(last_price))
                logging.info(f"Precio actual (fast_info) para {symbol}: {price_dec}")
                return price_dec
            except InvalidOperation:
                logging.warning(f"Valor 'last_price' de fast_info no es un número válido para {symbol}: {last_price}")

        logging.warning(f"No se pudo obtener 'last_price' válido de fast_info para {symbol}. Intentando con history.")
        hist = ticker.history(period="1d")
        if not hist.empty and 'Close' in hist.columns:
            last_close_price = hist['Close'].iloc[-1]
            try:
                price_dec = Decimal(str(last_close_price))
                logging.info(f"Precio actual (history close) para {symbol}: {price_dec}")
                return price_dec
            except InvalidOperation:
                 logging.error(f"Valor 'Close' de history no es un número válido para {symbol}: {last_close_price}")
                 return None
        else:
            logging.warning(f"No se encontró precio actual para {symbol} usando yfinance (ni fast_info ni history).")
            return None

    except Exception as e:
        logging.error(f"Excepción al obtener precio para {symbol} con yfinance: {e}", exc_info=True)
        return None

# --- Funciones CRUD para User ---
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(func.lower(models.User.email) == func.lower(email)).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(func.lower(models.User.username) == func.lower(username)).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, username: str, email: str, password: str):
    # Verificar si usuario o email ya existen antes de crear
    if get_user_by_username(db, username):
        # Indentación correcta aquí (4 espacios o 1 tab)
        raise ValueError(f"El nombre de usuario '{username}' ya existe.")
    if get_user_by_email(db, email):
        # Indentación correcta aquí (4 espacios o 1 tab) - ¡VERIFICA ESTA LÍNEA (era ~142)!
        raise ValueError(f"El email '{email}' ya está registrado.")

    hashed_password = get_password_hash(password)
    db_user = models.User(username=username, email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logging.info(f"Usuario '{username}' creado exitosamente.")
    return db_user

# --- Funciones CRUD para Asset ---
# ¡VERIFICA QUE ESTA LÍNEA Y LAS SIGUIENTES NO TENGAN INDENTACIÓN INICIAL (era ~150)!
def get_asset(db: Session, asset_id: int, owner_id: int):
    return db.query(models.Asset).filter(models.Asset.id == asset_id, models.Asset.owner_id == owner_id).first()

def get_asset_by_symbol(db: Session, symbol: str, owner_id: int):
    return db.query(models.Asset).filter(func.upper(models.Asset.symbol) == func.upper(symbol.strip()), models.Asset.owner_id == owner_id).first()

def get_assets_by_user(db: Session, owner_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Asset).filter(models.Asset.owner_id == owner_id).order_by(models.Asset.symbol).offset(skip).limit(limit).all()

def create_asset(db: Session, owner_id: int, symbol: str, name: str, asset_type: models.AssetType):
    symbol_upper = symbol.strip().upper()
    if not symbol_upper:
        raise ValueError("El símbolo del activo no puede estar vacío.")
    existing_asset = get_asset_by_symbol(db, symbol=symbol_upper, owner_id=owner_id)
    if existing_asset:
        logging.warning(f"Intento de crear activo duplicado: Símbolo '{symbol_upper}' ya existe para el usuario ID {owner_id}.")
        raise ValueError(f"El activo con símbolo '{symbol_upper}' ya existe para este usuario.")
    db_asset = models.Asset(owner_id=owner_id, symbol=symbol_upper, name=name.strip(), asset_type=asset_type)
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    logging.info(f"Activo '{symbol_upper}' creado para el usuario ID {owner_id}.")
    return db_asset

# --- Funciones CRUD para Transaction ---
def get_transaction(db: Session, transaction_id: int, owner_id: int):
    return db.query(models.Transaction).join(models.Asset).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.owner_id == owner_id
    ).first()

def get_transactions_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Transaction)\
             .filter(models.Transaction.owner_id == user_id)\
             .order_by(desc(models.Transaction.transaction_date), desc(models.Transaction.id))\
             .offset(skip)\
             .limit(limit)\
             .all()

def get_transactions_by_asset(db: Session, asset_id: int, owner_id: int):
    return db.query(models.Transaction)\
             .filter(models.Transaction.asset_id == asset_id, models.Transaction.owner_id == owner_id)\
             .order_by(asc(models.Transaction.transaction_date), asc(models.Transaction.id))\
             .all()

def _validate_and_convert_transaction_data(quantity, price_per_unit, fees) -> tuple[Decimal, Decimal, Decimal]:
    """Función interna para validar y convertir datos numéricos de transacción."""
    try:
        quantity_dec = Decimal(str(quantity))
        price_per_unit_dec = Decimal(str(price_per_unit))
        fees_dec = Decimal(str(fees))

        if quantity_dec <= ZERO_TOLERANCE:
            raise ValueError("La cantidad debe ser un número positivo.")
        if price_per_unit_dec < 0:
            raise ValueError("El precio por unidad no puede ser negativo.")
        if fees_dec < 0:
            raise ValueError("Las comisiones no pueden ser negativas.")

        return quantity_dec, price_per_unit_dec, fees_dec
    except InvalidOperation:
        raise ValueError("Cantidad, precio o comisiones contienen valores numéricos inválidos.")
    except ValueError as ve:
        raise ve

def create_transaction(db: Session, owner_id: int, asset_id: int, transaction_type: models.TransactionType,
                       quantity: float | str | Decimal, price_per_unit: float | str | Decimal, transaction_date: datetime,
                       fees: float | str | Decimal = 0.0, notes: str | None = None):
    asset = get_asset(db, asset_id=asset_id, owner_id=owner_id)
    if not asset:
        raise ValueError("El activo especificado no existe o no pertenece al usuario.")

    quantity_dec, price_per_unit_dec, fees_dec = _validate_and_convert_transaction_data(
        quantity, price_per_unit, fees
    )

    db_transaction = models.Transaction(
        owner_id=owner_id, asset_id=asset_id, transaction_type=transaction_type,
        quantity=quantity_dec, price_per_unit=price_per_unit_dec,
        transaction_date=transaction_date, fees=fees_dec, notes=notes.strip() if notes else None
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    logging.info(f"Transacción {transaction_type.name} de {quantity_dec} {asset.symbol} registrada para usuario ID {owner_id}.")
    return db_transaction

def update_transaction(db: Session, transaction_id: int, owner_id: int, updates: dict) -> models.Transaction | None:
    db_transaction = get_transaction(db, transaction_id=transaction_id, owner_id=owner_id)
    if not db_transaction:
        logging.warning(f"Intento de actualizar transacción inexistente o no autorizada: ID {transaction_id}, Usuario ID {owner_id}")
        return None

    validated_updates = {}
    temp_data = {
        'quantity': updates.get('quantity', db_transaction.quantity),
        'price_per_unit': updates.get('price_per_unit', db_transaction.price_per_unit),
        'fees': updates.get('fees', db_transaction.fees)
    }
    try:
        q, p, f = _validate_and_convert_transaction_data(
            temp_data['quantity'], temp_data['price_per_unit'], temp_data['fees']
        )
        if 'quantity' in updates: validated_updates['quantity'] = q
        if 'price_per_unit' in updates: validated_updates['price_per_unit'] = p
        if 'fees' in updates: validated_updates['fees'] = f
    except ValueError as e:
        logging.error(f"Error de validación al actualizar transacción ID {transaction_id}: {e}")
        raise ValueError(f"Datos de actualización inválidos: {e}")

    for key, value in updates.items():
        if key in ['quantity', 'price_per_unit', 'fees']:
            continue

        if hasattr(db_transaction, key):
            try:
                if key == 'transaction_date':
                    if isinstance(value, str):
                        try: new_value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                        except ValueError: new_value = datetime.strptime(value, '%Y-%m-%d')
                    elif isinstance(value, datetime): new_value = value
                    else: raise ValueError("Formato de fecha inválido.")
                    validated_updates[key] = new_value
                elif key == 'transaction_type':
                    # <<< CORRECCIÓN >>> Asegurarse de que el valor sea el Enum, no el string
                    if isinstance(value, models.TransactionType):
                        new_value = value
                    elif isinstance(value, str) and value.upper() in models.TransactionType.__members__:
                        new_value = models.TransactionType[value.upper()]
                    else:
                        raise ValueError("Tipo de transacción inválido.")
                    validated_updates[key] = new_value
                elif key == 'asset_id':
                    new_asset_id = int(value)
                    new_asset = get_asset(db, asset_id=new_asset_id, owner_id=owner_id)
                    if not new_asset: raise ValueError("El nuevo activo especificado no existe o no pertenece al usuario.")
                    validated_updates[key] = new_asset_id
                elif key == 'notes':
                     validated_updates[key] = value.strip() if value else None
                # else: # Ignorar otros campos no manejados explícitamente
                #    pass
            except (ValueError, TypeError) as e:
                logging.error(f"Error al procesar campo '{key}' para transacción ID {transaction_id}: {e}")
                raise ValueError(f"Valor inválido para el campo '{key}': {e}")
        else:
            logging.warning(f"Intento de actualizar campo inexistente '{key}' en transacción ID {transaction_id}")

    if not validated_updates:
        logging.info(f"No se detectaron cambios válidos para la transacción ID {transaction_id}.")
        return db_transaction

    for key, value in validated_updates.items():
        setattr(db_transaction, key, value)

    try:
        db.commit()
        db.refresh(db_transaction)
        log_symbol = db_transaction.asset.symbol
        logging.info(f"Transacción ID {transaction_id} ({db_transaction.transaction_type.name} {db_transaction.quantity} {log_symbol}) actualizada para usuario ID {owner_id}.")
        return db_transaction
    except Exception as e:
        db.rollback()
        logging.error(f"Error al hacer commit de la actualización para transacción ID {transaction_id}: {e}")
        raise

def delete_transaction(db: Session, transaction_id: int, owner_id: int) -> bool:
    db_transaction = get_transaction(db, transaction_id=transaction_id, owner_id=owner_id)
    if db_transaction:
        try:
            log_info = f"ID {transaction_id} ({db_transaction.transaction_type.name} {db_transaction.quantity} {db_transaction.asset.symbol})"
            db.delete(db_transaction)
            db.commit()
            logging.info(f"Transacción {log_info} eliminada para usuario ID {owner_id}.")
            return True
        except Exception as e:
            db.rollback()
            logging.error(f"Error al eliminar transacción ID {transaction_id}: {e}")
            return False
    else:
        logging.warning(f"Intento de eliminar transacción inexistente o no autorizada: ID {transaction_id}, Usuario ID {owner_id}")
        return False

# --- Funciones de Lógica de Negocio (Portafolio) ---
def get_portfolio_performance(db: Session, user_id: int) -> dict:
    """
    Calcula el rendimiento del portafolio para un usuario.
    Utiliza FIFO (First-In, First-Out) implícito para calcular el coste base en las ventas.
    Retorna un diccionario con detalles por activo.
    """
    user_assets = get_assets_by_user(db, owner_id=user_id, limit=10000)
    portfolio = {}
    logging.info(f"Calculando rendimiento para usuario ID {user_id}...")

    for asset in user_assets:
        transactions = get_transactions_by_asset(db, asset_id=asset.id, owner_id=user_id)
        if not transactions:
            logging.debug(f"Sin transacciones para {asset.symbol}, omitiendo.")
            continue

        purchase_lots: list[tuple[datetime, Decimal, Decimal]] = []
        realized_pnl_asset = Decimal(0)
        current_quantity = Decimal(0)
        total_investment = Decimal(0)

        logging.debug(f"Procesando {len(transactions)} transacciones para {asset.symbol}...")
        for t in transactions:
            # Asegurarse de que los valores de la BD son Decimal
            t_quantity = Decimal(t.quantity)
            t_price = Decimal(t.price_per_unit)
            t_fees = Decimal(t.fees) if t.fees is not None else Decimal(0)

            if t.transaction_type == models.TransactionType.BUY:
                cost_of_this_lot = (t_quantity * t_price) + t_fees
                cost_per_unit_with_fees = cost_of_this_lot / t_quantity if t_quantity > ZERO_TOLERANCE else Decimal(0)

                purchase_lots.append((t.transaction_date, t_quantity, cost_per_unit_with_fees))
                current_quantity += t_quantity
                total_investment += cost_of_this_lot
                logging.debug(f"  BUY {t_quantity} {asset.symbol} @ {t_price} (Coste Lote: {cost_of_this_lot:.4f}). Cantidad actual: {current_quantity}, Inversión total: {total_investment:.4f}")

            elif t.transaction_type == models.TransactionType.SELL:
                sell_quantity = t_quantity
                proceeds = (sell_quantity * t_price) - t_fees
                cost_basis_of_sold_units = Decimal(0)

                logging.debug(f"  SELL {sell_quantity} {asset.symbol} @ {t_price} (Ingresos: {proceeds:.4f}). Cantidad antes: {current_quantity}")

                if sell_quantity > current_quantity + ZERO_TOLERANCE:
                    logging.warning(f"Usuario {user_id}, Activo {asset.symbol}: Venta de {sell_quantity} excede la cantidad actual {current_quantity}. Se ajustará a {current_quantity}.")
                    sell_quantity = current_quantity

                remaining_sell_quantity = sell_quantity
                temp_lots = []
                purchase_lots.sort(key=lambda x: x[0])

                for lot_date, lot_quantity, lot_cost_per_unit in purchase_lots:
                    if remaining_sell_quantity <= ZERO_TOLERANCE:
                        temp_lots.append((lot_date, lot_quantity, lot_cost_per_unit))
                        continue

                    quantity_from_this_lot = min(remaining_sell_quantity, lot_quantity)
                    cost_basis_of_sold_units += quantity_from_this_lot * lot_cost_per_unit
                    remaining_sell_quantity -= quantity_from_this_lot

                    if lot_quantity > quantity_from_this_lot + ZERO_TOLERANCE:
                        remaining_lot_quantity = lot_quantity - quantity_from_this_lot
                        temp_lots.append((lot_date, remaining_lot_quantity, lot_cost_per_unit))
                        logging.debug(f"    - Vendido {quantity_from_this_lot} del lote {lot_date:%Y-%m-%d}. Quedan {remaining_lot_quantity}")
                    else:
                         logging.debug(f"    - Vendido {quantity_from_this_lot} (todo) del lote {lot_date:%Y-%m-%d}.")

                purchase_lots = temp_lots
                current_quantity -= sell_quantity
                total_investment -= cost_basis_of_sold_units
                realized_pnl_this_sale = proceeds - cost_basis_of_sold_units
                realized_pnl_asset += realized_pnl_this_sale

                logging.debug(f"  Venta completada. Coste base vendido: {cost_basis_of_sold_units:.4f}. P&L Realizado Venta: {realized_pnl_this_sale:.4f}")
                logging.debug(f"  Cantidad actual: {current_quantity}. Inversión restante: {total_investment:.4f}")

        if current_quantity > ZERO_TOLERANCE:
            total_cost_basis = total_investment
            average_cost_basis = total_cost_basis / current_quantity

            logging.debug(f"Calculando métricas finales para {asset.symbol}: Cantidad={current_quantity}, Coste Base Total={total_cost_basis:.4f}, Coste Medio={average_cost_basis:.4f}")

            current_price = get_current_price(asset.symbol)
            market_value, unrealized_pnl, unrealized_pnl_percent = None, None, None

            if current_price is not None:
                market_value = current_quantity * current_price
                unrealized_pnl = market_value - total_cost_basis
                if total_cost_basis > ZERO_TOLERANCE:
                    unrealized_pnl_percent = (unrealized_pnl / total_cost_basis) * Decimal(100)
                elif market_value > ZERO_TOLERANCE:
                    unrealized_pnl_percent = Decimal('inf')
                    logging.warning(f"Coste base <= 0 para {asset.symbol} con valor de mercado > 0. P&L% es infinito.")
                else:
                    unrealized_pnl_percent = Decimal(0)

                logging.debug(f"  Precio Actual: {current_price:.4f}, Valor Mercado: {market_value:.4f}, P&L No Real.: {unrealized_pnl:.4f}, %P&L: {unrealized_pnl_percent if unrealized_pnl_percent != Decimal('inf') else 'Inf'}")
            else:
                 logging.warning(f"No se pudo obtener precio actual para {asset.symbol}. No se calculará valor de mercado ni P&L.")

            portfolio[asset.symbol] = {
                "asset": asset, "quantity": current_quantity,
                "average_cost_basis": average_cost_basis, "total_cost_basis": total_cost_basis,
                "current_price": current_price, "market_value": market_value,
                "unrealized_pnl": unrealized_pnl, "unrealized_pnl_percent": unrealized_pnl_percent
            }
        else:
             logging.info(f"Posición final en {asset.symbol} es cero o negativa ({current_quantity}). No se incluye en el resumen de posiciones abiertas.")

    logging.info(f"Cálculo de rendimiento para usuario ID {user_id} completado. {len(portfolio)} posiciones abiertas encontradas.")
    return portfolio

# --- Funciones Adicionales (Ejemplos) ---
def get_realized_gains(db: Session, user_id: int, start_date: date | None = None, end_date: date | None = None):
    logging.warning("La función get_realized_gains aún no está implementada.")
    return None