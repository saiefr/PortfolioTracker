# src/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# --- Configuración de la Base de Datos ---
# Lee la URL de la base de datos desde una variable de entorno 'DATABASE_URL'.
# Si no se encuentra la variable de entorno, usa por defecto un archivo SQLite llamado
# 'portfolio.db' ubicado en el directorio RAÍZ del proyecto (un nivel arriba de 'src').
DEFAULT_DB_FILENAME = "portfolio.db"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, DEFAULT_DB_FILENAME)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

print(f"[*] Conectando a la base de datos: {DATABASE_URL}") # Mensaje informativo

engine = create_engine(
    DATABASE_URL,
    # connect_args es específico para SQLite. Necesario para permitir
    # el uso de la sesión de base de datos desde diferentes hilos (si fuera necesario,
    # aunque en este CLI simple no es estrictamente requerido pero es buena práctica).
    connect_args={"check_same_thread": False}
)

# SessionLocal es una 'fábrica' de sesiones de base de datos.
# Cada instancia de SessionLocal será una nueva sesión.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base es la clase base para nuestros modelos SQLAlchemy (declarative).
# Nuestras clases de modelos heredarán de esta.
Base = declarative_base()

# --- Función de Dependencia (Útil para frameworks web, opcional para CLI) ---
def get_db():
    """
    Generador que proporciona una sesión de base de datos.
    Asegura que la sesión se cierre correctamente después de su uso.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        print("[*] Cerrando sesión de base de datos (get_db).") # Mensaje informativo
        db.close()