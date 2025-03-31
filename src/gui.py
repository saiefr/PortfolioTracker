# src/gui.py
import customtkinter as ctk
# Asegúrate de tener CTkMessagebox: pip install CTkMessagebox
from CTkMessagebox import CTkMessagebox
from . import crud
from . import models # Importar los modelos
from .database import SessionLocal, get_db # Para interactuar con la BD
# Importar otros módulos necesarios si se usan directamente aquí
import logging
import sys
from decimal import Decimal # Probablemente necesario para mostrar datos formateados
# from enum import Enum as PyEnum # Solo si usas los Enums directamente aquí

# --- Configuración de Apariencia ---
ctk.set_appearance_mode("System")  # Opciones: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Opciones: "blue", "green", "dark-blue"

class PortfolioApp(ctk.CTk):
    def __init__(self, db_session):
        super().__init__()

        self.db = db_session # Guardar la sesión de BD
        self.current_user: models.User | None = None # Para saber quién está logueado

        # --- Configuración de la Ventana Principal ---
        self.title("Portfolio Tracker Pro")
        self.geometry("1100x700") # Tamaño inicial (ancho x alto)
        self.minsize(800, 500) # Establecer un tamaño mínimo razonable

        # --- Configurar Grid Layout (1x2) ---
        self.grid_columnconfigure(1, weight=1) # La columna 1 (derecha) se expande
        self.grid_rowconfigure(0, weight=1)    # La fila 0 (única principal) se expande

        # --- Crear Frame de Navegación Izquierdo ---
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(4, weight=1) # Espacio empuja botones hacia arriba/abajo

        self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame, text=" Menú ",
                                                    font=ctk.CTkFont(size=15, weight="bold"))
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        # Botones de navegación
        self.portfolio_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10,
                                              text="Portafolio", fg_color="transparent", text_color=("gray10", "gray90"),
                                              hover_color=("gray70", "gray30"), anchor="w",
                                              command=self.portfolio_button_event, state="disabled") # Estado inicial
        self.portfolio_button.grid(row=1, column=0, sticky="ew", padx=5, pady=2) # Añadir padding

        self.transactions_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10,
                                                 text="Transacciones", fg_color="transparent", text_color=("gray10", "gray90"),
                                                 hover_color=("gray70", "gray30"), anchor="w",
                                                 command=self.transactions_button_event, state="disabled") # Estado inicial
        self.transactions_button.grid(row=2, column=0, sticky="ew", padx=5, pady=2) # Añadir padding

        # Botón de Login/Logout (al final del frame de navegación)
        self.login_logout_button = ctk.CTkButton(self.navigation_frame, text="Login",
                                                 command=self.toggle_login_logout)
        self.login_logout_button.grid(row=6, column=0, padx=20, pady=20, sticky="s")


        # --- Crear Frames Principales (Contenido Derecho) ---
        # 1. Frame de Login
        self.login_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.login_frame.grid_columnconfigure(0, weight=1) # Para centrar contenido

        # 2. Frame de Portafolio
        self.portfolio_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        # Configurar grid del frame de portafolio si se necesita (ej. para tabla)
        self.portfolio_frame.grid_columnconfigure(0, weight=1)
        self.portfolio_frame.grid_rowconfigure(1, weight=1) # Permitir que la tabla crezca

        # 3. Frame de Transacciones
        self.transactions_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        # Configurar grid del frame de transacciones
        self.transactions_frame.grid_columnconfigure(0, weight=1) # Permitir que la tabla/botones se expandan
        self.transactions_frame.grid_rowconfigure(1, weight=1) # Permitir que la tabla crezca


        # --- Inicializar mostrando el Frame de Login ---
        self.select_frame_by_name("login")


    # --- Métodos para Cambiar Frames ---
    def select_frame_by_name(self, name):
        # Resaltar botón activo
        self.portfolio_button.configure(fg_color=self.portfolio_button.cget("hover_color") if name == "portfolio" else "transparent")
        self.transactions_button.configure(fg_color=self.transactions_button.cget("hover_color") if name == "transactions" else "transparent")

        # Mostrar/Ocultar frames
        if name == "login": self.login_frame.grid(row=0, column=1, sticky="nsew")
        else: self.login_frame.grid_forget()

        if name == "portfolio": self.portfolio_frame.grid(row=0, column=1, sticky="nsew")
        else: self.portfolio_frame.grid_forget()

        if name == "transactions": self.transactions_frame.grid(row=0, column=1, sticky="nsew")
        else: self.transactions_frame.grid_forget()

    # --- Eventos de Botones de Navegación ---
    def portfolio_button_event(self):
        self.select_frame_by_name("portfolio")
        self.update_portfolio_frame() # Actualizar contenido al seleccionar

    def transactions_button_event(self):
        self.select_frame_by_name("transactions")
        self.update_transactions_frame() # Actualizar contenido al seleccionar

    # --- Lógica Login/Logout ---
    def toggle_login_logout(self):
        if self.current_user:
            # --- Logout ---
            confirm = CTkMessagebox(title="Confirmar Logout", message="¿Estás seguro de que quieres cerrar sesión?",
                                    icon="question", option_1="Cancelar", option_2="Sí", parent=self) # Añadir parent
            if confirm.get() == "Sí":
                self.current_user = None
                self.login_logout_button.configure(text="Login")
                self.portfolio_button.configure(state="disabled")
                self.transactions_button.configure(state="disabled")
                self.select_frame_by_name("login") # Volver a pantalla de login
                self.title("Portfolio Tracker Pro") # Resetear título
                # Limpiar frames de datos para evitar mostrar datos antiguos al volver a loguear
                self._clear_portfolio_frame()
                self._clear_transactions_frame()
                logging.info("Sesión cerrada.")
                # No mostrar messagebox de sesión cerrada, es obvio por el cambio de pantalla
        else:
            # --- Mostrar Login ---
            # Si no hay usuario, este botón solo asegura que el frame de login esté visible
            self.select_frame_by_name("login")

    # --- Métodos para limpiar frames ---
    def _clear_frame_widgets(self, frame):
         """Función auxiliar para borrar todos los widgets de un frame."""
         for widget in frame.winfo_children():
             widget.destroy()

    def _clear_portfolio_frame(self):
         self._clear_frame_widgets(self.portfolio_frame)

    def _clear_transactions_frame(self):
         self._clear_frame_widgets(self.transactions_frame)

    # --- Métodos para actualizar frames (Implementación básica) ---
    def update_portfolio_frame(self):
        self._clear_portfolio_frame()
        if not self.current_user:
            logging.warning("Intento de actualizar portafolio sin usuario logueado.")
            return # No hacer nada si no hay usuario

        # Título del Frame
        label = ctk.CTkLabel(self.portfolio_frame, text=f"Resumen del Portafolio ({self.current_user.username})",
                             font=ctk.CTkFont(size=18, weight="bold"))
        label.grid(row=0, column=0, padx=20, pady=(10, 15), sticky="nw")

        # --- Aquí irá la lógica para mostrar la tabla del portafolio ---
        # Ejemplo: Añadir un placeholder mientras se implementa la tabla
        placeholder_label = ctk.CTkLabel(self.portfolio_frame, text="Cargando datos del portafolio...\n(Tabla pendiente de implementación)",
                                         font=ctk.CTkFont(size=14))
        placeholder_label.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

        # TODO:
        # 1. Llamar a `crud.get_portfolio_performance(self.db, self.current_user.id)`
        # 2. Manejar posibles errores de la llamada a crud.
        # 3. Crear una tabla (usando CTkTable, o un CTkScrollableFrame con CTkLabels/CTkFrames)
        # 4. Poblar la tabla con los datos formateados del diccionario devuelto por crud.
        # 5. Mostrar totales del portafolio.
        # 6. Añadir botón de refrescar.

    def update_transactions_frame(self):
        self._clear_transactions_frame()
        if not self.current_user:
            logging.warning("Intento de actualizar transacciones sin usuario logueado.")
            return # No hacer nada si no hay usuario

        # Frame para botones de acción (arriba)
        action_frame = ctk.CTkFrame(self.transactions_frame, fg_color="transparent")
        action_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")

        add_button = ctk.CTkButton(action_frame, text="Añadir Transacción", command=self.add_transaction_dialog)
        add_button.pack(side="left", padx=5) # Empaquetar botones horizontalmente

        # Placeholder para la tabla
        table_placeholder = ctk.CTkLabel(self.transactions_frame, text="Cargando historial de transacciones...\n(Tabla y botones Edit/Delete pendientes)",
                                         font=ctk.CTkFont(size=14))
        table_placeholder.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

        # TODO:
        # 1. Llamar a `crud.get_transactions_by_user(self.db, self.current_user.id, limit=?)`
        # 2. Crear una tabla (CTkTable o similar) para mostrar las transacciones.
        # 3. Añadir botones "Editar" y "Eliminar" (quizás en la tabla o asociados a la selección).
        # 4. Implementar diálogos/ventanas para añadir y editar transacciones.
        # 5. Implementar confirmación para eliminar.
        # 6. Añadir paginación o scroll si hay muchas transacciones.

    # --- Diálogos (Pendiente de implementación) ---
    def add_transaction_dialog(self):
         if not self.current_user: return
         CTkMessagebox(title="Info", message="Función 'Añadir Transacción' pendiente de implementación.", icon="info", parent=self)
         # Aquí se abriría una nueva ventana (Toplevel) o un diálogo para ingresar los datos.


# --- Punto de Entrada para la GUI ---
def run_gui():
    """Inicia la aplicación GUI."""
    db_session = SessionLocal()
    app = None # Inicializar app a None para el finally
    try:
        app = PortfolioApp(db_session)

        # --- Widgets del Frame de Login ---
        login_container = ctk.CTkFrame(app.login_frame, fg_color="transparent")
        login_container.grid(row=0, column=0, padx=30, pady=30, sticky="") # Centrar el contenedor

        login_label = ctk.CTkLabel(login_container, text="Iniciar Sesión", font=ctk.CTkFont(size=20, weight="bold"))
        login_label.grid(row=0, column=0, padx=10, pady=(0, 15)) # Padding inferior

        username_entry = ctk.CTkEntry(login_container, placeholder_text="Nombre de usuario", width=250) # Un poco más ancho
        username_entry.grid(row=1, column=0, padx=10, pady=10)

        password_entry = ctk.CTkEntry(login_container, placeholder_text="Contraseña", show="*", width=250)
        password_entry.grid(row=2, column=0, padx=10, pady=10)

        # --- Función de Callback para el Botón de Login ---
        def attempt_login(event=None): # Añadir event=None para bind
            username = username_entry.get()
            password = password_entry.get()
            if not username or not password:
                CTkMessagebox(title="Error de Validación", message="El nombre de usuario y la contraseña no pueden estar vacíos.", icon="warning", parent=app)
                return

            user = crud.get_user_by_username(app.db, username=username)
            login_ok = False
            if user:
                try:
                    # Intentar verificar contraseña
                    login_ok = crud.verify_password(password, user.hashed_password)
                except AttributeError as ae:
                     # Manejar el warning específico de bcrypt si aún ocurre
                     if "'bcrypt' has no attribute '__about__'" in str(ae):
                         logging.warning("Error conocido al leer versión de bcrypt, reintentando verificación...")
                         try:
                             # Reintentar la verificación asumiendo que el warning no es fatal
                             login_ok = crud.verify_password(password, user.hashed_password)
                         except Exception as verify_e:
                              logging.error(f"Error durante el reintento de verificación de contraseña: {verify_e}", exc_info=True)
                              login_ok = False
                     else:
                          # Si es otro AttributeError, relanzarlo o loggearlo
                          logging.error(f"AttributeError inesperado durante verify_password: {ae}", exc_info=True)
                          login_ok = False
                          CTkMessagebox(title="Error Interno", message="Ocurrió un error al verificar la contraseña.", icon="cancel", parent=app)
                except Exception as e:
                     # Capturar cualquier otro error durante la verificación
                     logging.error(f"Error inesperado durante verify_password: {e}", exc_info=True)
                     login_ok = False
                     CTkMessagebox(title="Error Interno", message="Ocurrió un error inesperado durante el login.", icon="cancel", parent=app)

            # Procesar resultado del login
            if login_ok:
                app.current_user = user
                app.login_logout_button.configure(text="Logout")
                app.portfolio_button.configure(state="normal")
                app.transactions_button.configure(state="normal")
                app.title(f"Portfolio Tracker Pro - {user.username}")
                app.select_frame_by_name("portfolio") # Cambiar frame ANTES de actualizar
                app.update_portfolio_frame() # Cargar datos iniciales
                # No mostrar messagebox de bienvenida, el cambio de pantalla es suficiente feedback
                logging.info(f"Usuario '{user.username}' inició sesión exitosamente.")
                username_entry.delete(0, "end")
                password_entry.delete(0, "end")
                app.portfolio_button.focus() # Poner foco en un botón principal
            else:
                # Solo mostrar error si login_ok es False (no si user era None o hubo excepción ya mostrada)
                if user: # Solo mostrar si el usuario existía pero la contraseña falló
                    CTkMessagebox(title="Error de Login", message="Nombre de usuario o contraseña incorrectos.", icon="cancel", parent=app)
                elif not user: # Si el usuario no existe
                     CTkMessagebox(title="Error de Login", message=f"El usuario '{username}' no existe.", icon="cancel", parent=app)
                password_entry.delete(0, "end") # Borrar contraseña en fallo
                username_entry.focus() # Poner foco en usuario para reintentar

        # --- Botón de Login ---
        login_button = ctk.CTkButton(login_container, text="Login", command=attempt_login, width=250)
        login_button.grid(row=3, column=0, padx=10, pady=(20, 10)) # Más espacio arriba

        # Bind Enter key to login button (si el foco está en user/pass o botón)
        username_entry.bind("<Return>", attempt_login)
        password_entry.bind("<Return>", attempt_login)
        # login_button.bind("<Return>", attempt_login) # No necesario si los entries ya lo hacen

        # Opción para registrar (simplificado)
        def show_register_info():
             CTkMessagebox(title="Registro", message="La función de registro aún no está implementada en la GUI.\nPor favor, usa la versión de consola para registrarte.", icon="info", parent=app)

        register_button = ctk.CTkButton(login_container, text="Registrar (Info)", command=show_register_info, width=150, fg_color="gray")
        register_button.grid(row=4, column=0, padx=10, pady=10)

        # Poner foco inicial en el campo de usuario
        username_entry.focus()

        # --- Iniciar el Bucle Principal ---
        app.mainloop()

    except Exception as e:
        logging.critical("Error fatal al iniciar o durante la ejecución de la GUI", exc_info=True)
        try:
            # Intentar mostrar error en messagebox
            root_error = ctk.CTk()
            root_error.withdraw()
            CTkMessagebox(title="Error Fatal", message=f"Ocurrió un error crítico:\n{e}\n\nLa aplicación se cerrará.", icon="cancel", parent=root_error)
            root_error.destroy()
        except Exception as mb_error:
            print(f"[CRITICAL] No se pudo mostrar el error en messagebox: {mb_error}")
            print(f"[CRITICAL] Error original: {e}") # Imprimir error original en consola
        # Asegurar cierre de sesión de BD
        if db_session:
            try:
                db_session.close()
            except Exception as db_close_err:
                 logging.error(f"Error al cerrar sesión de BD en manejo de excepción: {db_close_err}")
        sys.exit(1) # Salir con error
    finally:
        # Cierre normal de la sesión de BD
        if app and hasattr(app, 'db') and app.db:
             try:
                 print("[*] Cerrando sesión de base de datos (GUI).")
                 app.db.close()
             except Exception as db_close_norm_err:
                  logging.error(f"Error al cerrar sesión de BD normalmente: {db_close_norm_err}")
        elif db_session: # Si app falló pero sesión existe
             try:
                 print("[*] Cerrando sesión de base de datos (GUI - fallback).")
                 db_session.close()
             except Exception as db_close_fall_err:
                  logging.error(f"Error al cerrar sesión de BD en fallback: {db_close_fall_err}")