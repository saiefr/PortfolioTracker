# src/crud.py
from sqlalchemy.orm import Session
import bcrypt
# --- Importación Relativa ---
from . import models
from datetime import datetime

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
def get_asset_by_symbol(db: Session, symbol: str, owner_id: int = None): # Opcional filtrar por owner_id
    query = db.query(models.Asset).filter(models.Asset.symbol == symbol.upper())
    if owner_id:
        query = query.filter(models.Asset.owner_id == owner_id)
    return query.first()
# Modificado para aceptar owner_id
def create_asset(db: Session, owner_id: int, symbol: str, name: str, asset_type: models.AssetType):
    symbol_upper = symbol.upper()
    # Opcional: Verificar si ya existe ESE símbolo PARA ESE usuario
    # existing = get_asset_by_symbol(db, symbol=symbol_upper, owner_id=owner_id)
    # if existing:
    #    raise ValueError(f"Asset {symbol_upper} already exists for this user.")
    db_asset = models.Asset(symbol=symbol_upper, name=name, asset_type=asset_type, owner_id=owner_id)
    db.add(db_asset); db.commit(); db.refresh(db_asset); return db_asset

# --- Funciones para Transaction ---
def create_transaction(db: Session, owner_id: int, asset_id: int,
                       transaction_type: models.TransactionType, quantity: float, price_per_unit: float,
                       transaction_date: datetime, fees: float = 0.0, notes: str = None):
    if quantity <= 0 or price_per_unit < 0: # Permitir precio 0? Quizás no.
        raise ValueError("Cantidad debe ser positiva y precio no negativo.")
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

# print("Funciones CRUD definidas.") # Comentado para limpieza