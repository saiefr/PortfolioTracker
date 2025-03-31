# src/crud.py
# --- Importaciones ---
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, case
from . import models # <--- CORRECCIÓN AQUÍ: Eliminado ', schemas'
from passlib.context import CryptContext # Asegúrate de instalar con: pip install "passlib[bcrypt]"
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import yfinance as yf
import logging
import os

# --- Configuración ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'portfolio.db')}"
print(f"[*] Conectando a la base de datos: {DATABASE_URL}") # Mensaje informativo

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ZERO_TOLERANCE = Decimal('1e-9')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Funciones de Utilidad ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_current_price(symbol: str) -> Decimal | None:
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.fast_info
        market_price = data.get('last_price')
        if market_price:
             return Decimal(str(market_price))
        else:
             logging.warning(f"No se pudo obtener 'last_price' de fast_info para {symbol}. Intentando con history.")
             hist = ticker.history(period="1d")
             if not hist.empty:
                 last_price = Decimal(str(hist['Close'].iloc[-1]))
                 logging.info(f"Precio actual (history) para {symbol}: {last_price}")
                 return last_price
             else:
                 logging.warning(f"No se encontró precio actual para {symbol} usando yfinance.")
                 return None
    except Exception as e:
        logging.error(f"Error al obtener precio para {symbol} con yfinance: {e}")
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
    hashed_password = get_password_hash(password)
    db_user = models.User(username=username, email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logging.info(f"Usuario '{username}' creado exitosamente.")
    return db_user

# --- Funciones CRUD para Asset ---
def get_asset(db: Session, asset_id: int, owner_id: int):
    return db.query(models.Asset).filter(models.Asset.id == asset_id, models.Asset.owner_id == owner_id).first()

def get_asset_by_symbol(db: Session, symbol: str, owner_id: int):
    return db.query(models.Asset).filter(func.upper(models.Asset.symbol) == func.upper(symbol), models.Asset.owner_id == owner_id).first()

def get_assets_by_user(db: Session, owner_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Asset).filter(models.Asset.owner_id == owner_id).order_by(models.Asset.symbol).offset(skip).limit(limit).all()

def create_asset(db: Session, owner_id: int, symbol: str, name: str, asset_type: models.AssetType):
    existing_asset = get_asset_by_symbol(db, symbol=symbol, owner_id=owner_id)
    if existing_asset:
        logging.warning(f"Intento de crear activo duplicado: Símbolo '{symbol}' ya existe para el usuario ID {owner_id}.")
        raise ValueError(f"El activo con símbolo '{symbol}' ya existe para este usuario.")
    db_asset = models.Asset(owner_id=owner_id, symbol=symbol.upper(), name=name, asset_type=asset_type)
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    logging.info(f"Activo '{symbol}' creado para el usuario ID {owner_id}.")
    return db_asset

# --- Funciones CRUD para Transaction ---
def get_transaction(db: Session, transaction_id: int, owner_id: int):
    return db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.owner_id == owner_id
    ).first()

def get_transactions_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Transaction)\
             .filter(models.Transaction.owner_id == user_id)\
             .order_by(desc(models.Transaction.transaction_date))\
             .offset(skip)\
             .limit(limit)\
             .all()

def get_transactions_by_asset(db: Session, asset_id: int, owner_id: int):
    return db.query(models.Transaction)\
             .filter(models.Transaction.asset_id == asset_id, models.Transaction.owner_id == owner_id)\
             .order_by(asc(models.Transaction.transaction_date), asc(models.Transaction.id))\
             .all()

def create_transaction(db: Session, owner_id: int, asset_id: int, transaction_type: models.TransactionType,
                       quantity: float, price_per_unit: float, transaction_date: datetime,
                       fees: float = 0.0, notes: str | None = None):
    asset = get_asset(db, asset_id=asset_id, owner_id=owner_id)
    if not asset: raise ValueError("El activo especificado no existe o no pertenece al usuario.")
    try:
        quantity_dec = Decimal(str(quantity))
        price_per_unit_dec = Decimal(str(price_per_unit))
        fees_dec = Decimal(str(fees))
        if quantity_dec <= ZERO_TOLERANCE: raise ValueError("La cantidad debe ser positiva.")
        if price_per_unit_dec < 0: raise ValueError("El precio por unidad no puede ser negativo.")
        if fees_dec < 0: raise ValueError("Las comisiones no pueden ser negativas.")
    except InvalidOperation: raise ValueError("Cantidad, precio o comisiones inválidas.")
    db_transaction = models.Transaction(
        owner_id=owner_id, asset_id=asset_id, transaction_type=transaction_type,
        quantity=quantity_dec, price_per_unit=price_per_unit_dec,
        transaction_date=transaction_date, fees=fees_dec, notes=notes
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
    asset_changed = False
    for key, value in updates.items():
        if hasattr(db_transaction, key):
            try:
                if key in ['quantity', 'price_per_unit', 'fees']:
                    new_value = Decimal(str(value))
                    if key == 'quantity' and new_value <= ZERO_TOLERANCE: raise ValueError("La cantidad debe ser positiva.")
                    if key == 'price_per_unit' and new_value < 0: raise ValueError("El precio por unidad no puede ser negativo.")
                    if key == 'fees' and new_value < 0: raise ValueError("Las comisiones no pueden ser negativas.")
                elif key == 'transaction_date':
                    if isinstance(value, str):
                        try: new_value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                        except ValueError: new_value = datetime.strptime(value, '%Y-%m-%d')
                    elif isinstance(value, datetime): new_value = value
                    else: raise ValueError("Formato de fecha inválido.")
                elif key == 'transaction_type':
                    if isinstance(value, models.TransactionType): new_value = value
                    elif isinstance(value, str) and value.upper() in models.TransactionType.__members__: new_value = models.TransactionType[value.upper()]
                    else: raise ValueError("Tipo de transacción inválido.")
                elif key == 'asset_id':
                    new_asset = get_asset(db, asset_id=int(value), owner_id=owner_id)
                    if not new_asset: raise ValueError("El nuevo activo especificado no existe o no pertenece al usuario.")
                    new_value = int(value)
                    if new_value != db_transaction.asset_id: asset_changed = True
                else: new_value = value
                setattr(db_transaction, key, new_value)
            except (InvalidOperation, ValueError) as e:
                logging.error(f"Error al actualizar campo '{key}' para transacción ID {transaction_id}: {e}")
                raise ValueError(f"Valor inválido para el campo '{key}': {e}")
        else:
            logging.warning(f"Intento de actualizar campo inexistente '{key}' en transacción ID {transaction_id}")
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
    user_assets = get_assets_by_user(db, owner_id=user_id, limit=10000)
    portfolio = {}
    for asset in user_assets:
        transactions = get_transactions_by_asset(db, asset_id=asset.id, owner_id=user_id)
        if not transactions: continue
        current_quantity = Decimal(0)
        total_cost_basis = Decimal(0)
        for t in transactions:
            if t.transaction_type == models.TransactionType.BUY:
                current_quantity += t.quantity
                total_cost_basis += (t.quantity * t.price_per_unit) + t.fees
            elif t.transaction_type == models.TransactionType.SELL:
                sold_quantity = t.quantity
                if sold_quantity > current_quantity + ZERO_TOLERANCE:
                     logging.warning(f"Usuario {user_id}, Activo {asset.symbol}: Venta de {sold_quantity} excede la cantidad actual {current_quantity}. Se ajustará a {current_quantity}.")
                     sold_quantity = current_quantity
                if current_quantity > ZERO_TOLERANCE:
                    proportion_sold = sold_quantity / current_quantity
                    cost_basis_reduction = total_cost_basis * proportion_sold
                    total_cost_basis -= cost_basis_reduction
                else:
                     logging.warning(f"Usuario {user_id}, Activo {asset.symbol}: Intento de venta con cantidad {current_quantity} <= 0. No se ajusta coste base.")
                current_quantity -= sold_quantity
        if current_quantity > ZERO_TOLERANCE:
            average_cost_basis = total_cost_basis / current_quantity if current_quantity > ZERO_TOLERANCE else Decimal(0)
            current_price = get_current_price(asset.symbol)
            market_value, unrealized_pnl, unrealized_pnl_percent = None, None, None
            if current_price is not None:
                market_value = current_quantity * current_price
                unrealized_pnl = market_value - total_cost_basis
                if total_cost_basis > ZERO_TOLERANCE:
                    unrealized_pnl_percent = (unrealized_pnl / total_cost_basis) * Decimal(100)
                else:
                    unrealized_pnl_percent = Decimal(100.0) if market_value > ZERO_TOLERANCE else Decimal(0.0)
            portfolio[asset.symbol] = {
                "asset": asset, "quantity": current_quantity,
                "average_cost_basis": average_cost_basis, "total_cost_basis": total_cost_basis,
                "current_price": current_price, "market_value": market_value,
                "unrealized_pnl": unrealized_pnl, "unrealized_pnl_percent": unrealized_pnl_percent
            }
    return portfolio

# --- Funciones Adicionales (Ejemplos) ---
def get_realized_gains(db: Session, user_id: int, start_date: date | None = None, end_date: date | None = None):
    logging.warning("La función get_realized_gains aún no está implementada.")
    return None