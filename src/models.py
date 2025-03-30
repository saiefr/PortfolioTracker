# src/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from .database import Base # RELATIVA

class AssetType(PyEnum):
    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    OTHER = "OTHER"

class TransactionType(PyEnum):
    BUY = "BUY"
    SELL = "SELL"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    assets = relationship("Asset", back_populates="owner", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="owner", cascade="all, delete-orphan")
    def __repr__(self): return f"<User(username='{self.username}', email='{self.email}')>"

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    name = Column(String, nullable=True)
    asset_type = Column(SQLEnum(AssetType), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="assets")
    transactions = relationship("Transaction", back_populates="asset", cascade="all, delete-orphan")
    def __repr__(self): return f"<Asset(symbol='{self.symbol}', type='{self.asset_type.name}')>"

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    quantity = Column(Numeric(precision=18, scale=8), nullable=False)
    price_per_unit = Column(Numeric(precision=18, scale=8), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    fees = Column(Numeric(precision=18, scale=8), nullable=True, default=0.0)
    notes = Column(String, nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    asset = relationship("Asset", back_populates="transactions")
    owner = relationship("User", back_populates="transactions")
    def __repr__(self): total = self.quantity * self.price_per_unit; return f"<Transaction(type='{self.transaction_type.name}', asset_id={self.asset_id}, qty={self.quantity}, price={self.price_per_unit}, total={total})>"