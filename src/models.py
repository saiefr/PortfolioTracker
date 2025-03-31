# src/models.py
from sqlalchemy import (Column, Integer, String, Float, DateTime, ForeignKey,
                        Enum as SQLEnum, Numeric, UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from .database import Base # RELATIVA

# --- Enums para Tipos ---

class AssetType(PyEnum):
    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    OTHER = "OTHER"

class TransactionType(PyEnum):
    BUY = "BUY"
    SELL = "SELL"
    # Podríamos añadir: DIVIDEND, INTEREST, FEE, SPLIT, etc. en el futuro

# --- Modelos SQLAlchemy ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones: Un usuario puede tener muchos activos y muchas transacciones.
    # 'cascade="all, delete-orphan"' significa que si se borra un usuario,
    # también se borrarán todos sus activos y transacciones asociados. ¡Usar con cuidado!
    assets = relationship("Asset", back_populates="owner", cascade="all, delete-orphan", passive_deletes=True)
    transactions = relationship("Transaction", back_populates="owner", cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

class Asset(Base):
    __tablename__ = "assets"
    # Añadir una restricción única para que un usuario no pueda tener el mismo símbolo dos veces
    __table_args__ = (UniqueConstraint('owner_id', 'symbol', name='uq_user_asset_symbol'),)

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False) # Ej: AAPL, BTC-USD
    name = Column(String, nullable=True) # Ej: Apple Inc., Bitcoin
    asset_type = Column(SQLEnum(AssetType), nullable=False) # Usar el Enum de SQLalchemy

    # Clave foránea para relacionar con el usuario propietario
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relaciones: Un activo pertenece a un usuario y puede tener muchas transacciones.
    owner = relationship("User", back_populates="assets")

    # --- MODIFICACIÓN IMPORTANTE ---
    # Se quita 'cascade="all, delete-orphan"' de aquí.
    # No queremos borrar el historial de transacciones si se elimina un activo.
    # Si quisiéramos borrar transacciones al borrar el activo, necesitaríamos lógica explícita
    # o re-añadir el cascade si estamos seguros de ese comportamiento.
    # 'passive_deletes=True' puede ser útil si la base de datos maneja la restricción FK.
    transactions = relationship("Transaction", back_populates="asset", cascade="save-update, merge", passive_deletes=True)

    def __repr__(self):
        return f"<Asset(id={self.id}, symbol='{self.symbol}', type='{self.asset_type.name}', owner_id={self.owner_id})>"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False) # BUY o SELL

    # Usar Numeric para precisión financiera.
    # precision: número total de dígitos.
    # scale: número de dígitos después del punto decimal.
    # Ajusta según necesites (e.g., para criptos con muchos decimales).
    quantity = Column(Numeric(precision=24, scale=10), nullable=False)
    price_per_unit = Column(Numeric(precision=24, scale=10), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    fees = Column(Numeric(precision=18, scale=8), nullable=True, default=0.0)
    notes = Column(String, nullable=True) # Para comentarios adicionales

    # Claves foráneas
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False) # Redundante pero útil para queries

    # Relaciones: Una transacción pertenece a un activo y a un usuario.
    asset = relationship("Asset", back_populates="transactions")
    owner = relationship("User", back_populates="transactions")

    def __repr__(self):
        try:
            # Intentar calcular el valor total, manejando posible None o error
            total_value = self.quantity * self.price_per_unit if self.quantity is not None and self.price_per_unit is not None else "N/A"
            if total_value != "N/A":
                total_value_str = f"{total_value:.2f}" # Formatear a 2 decimales si es numérico
            else:
                total_value_str = "N/A"
        except TypeError:
            total_value_str = "Error" # En caso de tipos incompatibles

        return (f"<Transaction(id={self.id}, type='{self.transaction_type.name}', "
                f"asset_id={self.asset_id}, qty={self.quantity}, price={self.price_per_unit}, "
                f"date='{self.transaction_date.strftime('%Y-%m-%d')}', total_value={total_value_str})>")