# src/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # Para default timestamp
from enum import Enum as PyEnum
from database import Base # Importa la Base de database.py

# Enum para tipos de activo (opcional pero útil)
class AssetType(PyEnum):
    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    OTHER = "OTHER"

class User(Base):
    __tablename__ = "users" # Nombre de la tabla en la BBDD

    id = Column(Integer, primary_key=True, index=True) # Clave primaria autoincremental
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False) # ¡Guardaremos el hash, no la contraseña!
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación con activos (un usuario puede tener muchos activos) - Opcional por ahora
    # assets = relationship("Asset", back_populates="owner")
    # transactions = relationship("Transaction", back_populates="owner")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False) # Ej: 'AAPL', 'BTC-USD'
    name = Column(String, nullable=True) # Ej: 'Apple Inc.', 'Bitcoin'
    asset_type = Column(SQLEnum(AssetType), nullable=False) # Usamos el Enum
    # (Más adelante añadiremos relación con usuario y transacciones)
    # owner_id = Column(Integer, ForeignKey("users.id"))
    # owner = relationship("User", back_populates="assets")
    # transactions = relationship("Transaction", back_populates="asset")

    def __repr__(self):
        return f"<Asset(symbol='{self.symbol}', type='{self.asset_type.name}')>"

# (Más adelante añadiremos la tabla Transaction aquí)

print("Modelos User y Asset definidos.")