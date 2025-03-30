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

# --- Funciones para User ---
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()
def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()
def create_user(db: Session, username: str, email: str, password: str):
    hashed_password_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashed_password_str = hashed_password_bytes.decode('utf-8')
    db_user = models.User(username=username, email=email, hashed_password=hashed_password_str)
    db.add(db_user); db.commit(); db.refresh(db_user); return db_user
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- Funciones para Asset ---
def get_asset_by_symbol(db: Session, symbol: str, owner_id: int = None):
    query = db.query(models.Asset).filter(models.Asset.symbol == symbol.upper())
    if owner_id: query = query.filter(models.Asset.owner_id == owner_id)
    return query.first()
def create_asset(db: Session, owner_id: int, symbol: str, name: str, asset_type: models.AssetType):
    symbol_upper = symbol.upper()
    db_asset = models.Asset(symbol=symbol_upper, name=name, asset_type=asset_type, owner_id=owner_id)
    db.add(db_asset); db.commit(); db.refresh(db_asset); return db_asset

# --- Funciones para Transaction ---
def create_transaction(db: Session, owner_id: int, asset_id: int,
                       transaction_type: models.TransactionType, quantity: float, price_per_unit: float,
                       transaction_date: datetime, fees: float = 0.0, notes: str = None):
    if quantity <= 0 or price_per_unit < 0: raise ValueError("Cantidad debe ser positiva y precio no negativo.")
    db_transaction = models.Transaction(owner_id=owner_id, asset_id=asset_id, transaction_type=transaction_type,
                                        quantity=quantity, price_per_unit=price_per_unit, transaction_date=transaction_date,
                                        fees=fees, notes=notes)
    db.add(db_transaction); db.commit(); db.refresh(db_transaction); return db_transaction
def get_transactions_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Transaction).filter(models.Transaction.owner_id == user_id)\
             .order_by(models.Transaction.transaction_date.desc()).offset(skip).limit(limit).all()
def get_transactions_by_asset(db: Session, asset_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Transaction).filter(models.Transaction.asset_id == asset_id)\
             .order_by(models.Transaction.transaction_date.desc()).offset(skip).limit(limit).all()

# --- Funciones de Lógica de Portafolio ---
def get_user_positions(db: Session, user_id: int) -> dict[models.Asset, float]:
    """Calcula las posiciones actuales (cantidad neta) de cada activo para un usuario."""
    # print(f"\n--- Calculando posiciones para User ID: {user_id} ---") # Comentado para limpieza
    transactions = db.query(models.Transaction)\
                     .filter(models.Transaction.owner_id == user_id)\
                     .order_by(models.Transaction.asset_id, models.Transaction.transaction_date)\
                     .all()
    positions_by_asset_id = defaultdict(float)
    for t in transactions:
        quantity = float(t.quantity)
        if t.transaction_type == models.TransactionType.BUY: positions_by_asset_id[t.asset_id] += quantity
        elif t.transaction_type == models.TransactionType.SELL: positions_by_asset_id[t.asset_id] -= quantity
    final_positions = {}
    if positions_by_asset_id:
        asset_ids = list(positions_by_asset_id.keys())
        assets = db.query(models.Asset).filter(models.Asset.id.in_(asset_ids)).all()
        asset_map = {asset.id: asset for asset in assets}
        for asset_id, quantity in positions_by_asset_id.items():
            if not math.isclose(quantity, 0, abs_tol=1e-9):
                asset = asset_map.get(asset_id)
                if asset: final_positions[asset] = quantity
    # print(f"Posiciones calculadas: {len(final_positions)} activos con holdings.") # Comentado
    return final_positions

# --- Funciones de Datos de Mercado ---
def get_current_prices(symbols: list[str]) -> dict[str, float]:
    """Obtiene el precio actual para una lista de símbolos usando yfinance."""
    print(f"\n--- Obteniendo precios actuales para: {', '.join(symbols)} ---")
    prices = {}
    if not symbols: return prices
    try:
        data = yf.download(symbols, period="1d", progress=False)
        if data.empty: print("Advertencia: yfinance no devolvió datos."); return prices
        if isinstance(data.columns, pd.MultiIndex):
            price_col = 'Adj Close' if 'Adj Close' in data.columns.levels[0] else 'Close'
            if price_col in data.columns.levels[0]:
                 last_prices = data[price_col].iloc[-1]; prices = last_prices.to_dict()
            else: print(f"Advertencia: No se encontró columna '{price_col}' multi-index.")
        elif len(symbols) == 1 and not data.empty:
            price_col = 'Adj Close' if 'Adj Close' in data.columns else 'Close'
            if price_col in data.columns: prices[symbols[0]] = data[price_col].iloc[-1]
            else: print(f"Advertencia: No se encontró columna '{price_col}' para {symbols[0]}.")
        else: print("Advertencia: Formato inesperado de yfinance.")
    except Exception as e: print(f"Error obteniendo precios de yfinance: {e}")
    valid_prices = {symbol: float(price) for symbol, price in prices.items() if pd.notna(price)}
    print(f"Precios obtenidos: {len(valid_prices)} válidos.")
    return valid_prices