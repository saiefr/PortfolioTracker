# src/main.py
from database import SessionLocal, engine # Importa la sesión y el motor
import models # Importa los modelos (para que Base sepa de ellos si es necesario)
import crud # Importa nuestras funciones CRUD

# Opcional: Crear tablas si no existen (Alembic es la forma preferida, pero esto es útil para pruebas rápidas)
# models.Base.metadata.create_all(bind=engine)

def register_new_user():
    """Función simple para registrar un usuario desde la consola."""
    print("--- Registrar Nuevo Usuario ---")
    username = input("Nombre de usuario: ")
    email = input("Email: ")
    password = input("Contraseña: ")
    password_confirm = input("Confirmar contraseña: ")

    if password != password_confirm:
        print("Error: Las contraseñas no coinciden.")
        return

    # Obtener una sesión de base de datos
    db = SessionLocal()
    try:
        # Verificar si el usuario o email ya existen
        existing_user = crud.get_user_by_username(db, username=username)
        if existing_user:
            print(f"Error: El nombre de usuario '{username}' ya existe.")
            return
        existing_email = crud.get_user_by_email(db, email=email)
        if existing_email:
            print(f"Error: El email '{email}' ya está registrado.")
            return

        # Crear el usuario
        new_user = crud.create_user(db=db, username=username, email=email, password=password)
        print(f"¡Usuario '{new_user.username}' creado exitosamente con ID: {new_user.id}!")

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        db.rollback() # Deshacer cambios si hubo error
    finally:
        db.close() # Siempre cerrar la sesión

if __name__ == "__main__":
    register_new_user()
    # Puedes añadir un bucle o más opciones aquí si quieres
    print("\nPrograma finalizado.")