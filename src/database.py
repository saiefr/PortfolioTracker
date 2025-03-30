# src/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Define la ubicación de la base de datos SQLite
# Estará en la carpeta raíz del proyecto (fuera de 'src')
DATABASE_URL = "sqlite:///../portfolio.db" # Tres barras para ruta relativa

# Crea el motor de SQLAlchemy
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Crea una fábrica de sesiones (SessionLocal)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crea una clase Base para nuestros modelos declarativos
Base = declarative_base()

# Función para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# print(f"SQLAlchemy Engine creado para: {DATABASE_URL}") # Comentado para limpieza