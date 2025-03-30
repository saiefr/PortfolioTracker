# src/crud.py
from sqlalchemy.orm import Session
import bcrypt # Para hashing

# Importa los modelos y el esquema (si tuvieras esquemas Pydantic, aquí irían)
import models
# from . import schemas # Descomentar si usas Pydantic más adelante

# --- Funciones para User ---

def get_user_by_email(db: Session, email: str):
    """Busca un usuario por su email."""
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    """Busca un usuario por su nombre de usuario."""
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, username: str, email: str, password: str):
    """Crea un nuevo usuario con contraseña hasheada."""
    # Hashear la contraseña antes de guardarla
    hashed_password_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashed_password_str = hashed_password_bytes.decode('utf-8') # Guardar como string

    # Crear la instancia del modelo User
    db_user = models.User(
        username=username,
        email=email,
        hashed_password=hashed_password_str
    )

    # Añadir a la sesión y confirmar para guardar en BBDD
    db.add(db_user)
    db.commit()
    db.refresh(db_user) # Refresca el objeto db_user con datos de la BBDD (como el ID asignado)
    return db_user

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña plana coincide con una hasheada."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- Funciones para Asset (las añadiremos más adelante) ---
# def create_asset(...)
# def get_assets(...)

# --- Funciones para Transaction (las añadiremos más adelante) ---
# def create_transaction(...)
# def get_transactions(...)

print("Funciones CRUD definidas.")