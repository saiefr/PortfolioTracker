# src/gui.py
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from CTkTable import CTkTable
# import pandas as pd # No se usa actualmente, se puede comentar o quitar
from . import crud
from . import models
from .database import SessionLocal
import logging
import sys
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, DivisionByZero
from datetime import datetime

# --- Configuración de Apariencia ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PortfolioApp(ctk.CTk):
    def __init__(self, db_session):
        super().__init__()

        self.db = db_session
        self.current_user: models.User | None = None
        self.selected_transaction_id: int | None = None

        # --- Configuración de la Ventana Principal ---
        self.title("Portfolio Tracker Pro")
        self.geometry("1100x700")
        self.minsize(800, 500)

        # --- Configurar Grid Layout (1x2) ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Crear Frame de Navegación Izquierdo ---
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(4, weight=1) # Espacio flexible

        self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame, text=" Menú ",
                                                    font=ctk.CTkFont(size=15, weight="bold"))
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        self.portfolio_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10,
                                              text="Portafolio", fg_color="transparent", text_color=("gray10", "gray90"),
                                              hover_color=("gray70", "gray30"), anchor="w",
                                              command=self.portfolio_button_event, state="disabled")
        self.portfolio_button.grid(row=1, column=0, sticky="ew", padx=5, pady=2)

        self.transactions_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10,
                                                 text="Transacciones", fg_color="transparent", text_color=("gray10", "gray90"),
                                                 hover_color=("gray70", "gray30"), anchor="w",
                                                 command=self.transactions_button_event, state="disabled")
        self.transactions_button.grid(row=2, column=0, sticky="ew", padx=5, pady=2)

        self.login_logout_button = ctk.CTkButton(self.navigation_frame, text="Login",
                                                 command=self.toggle_login_logout)
        self.login_logout_button.grid(row=5, column=0, padx=20, pady=20, sticky="s") # Usar fila 5 para dejar espacio


        # --- Crear Frames Principales (Contenido Derecho) ---
        self.login_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.login_frame.grid_columnconfigure(0, weight=1) # Centrar contenido login
        self.login_frame.grid_rowconfigure(0, weight=1)    # Centrar contenido login

        self.portfolio_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.portfolio_frame.grid_columnconfigure(0, weight=1) # Columna 0 se expande
        self.portfolio_frame.grid_rowconfigure(1, weight=1)    # Fila 1 (para la tabla) se expande

        self.transactions_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.transactions_frame.grid_columnconfigure(0, weight=1) # Columna 0 se expande
        self.transactions_frame.grid_rowconfigure(1, weight=1)    # Fila 1 (para la tabla) se expande

        # --- Inicializar mostrando el Frame de Login ---
        self.select_frame_by_name("login")


    # --- Métodos para Cambiar Frames ---
    def select_frame_by_name(self, name):
        self.selected_transaction_id = None
        if hasattr(self, 'edit_transaction_button'): self.edit_transaction_button.configure(state="disabled")
        if hasattr(self, 'delete_transaction_button'): self.delete_transaction_button.configure(state="disabled")

        self.portfolio_button.configure(fg_color=self.portfolio_button.cget("hover_color") if name == "portfolio" else "transparent")
        self.transactions_button.configure(fg_color=self.transactions_button.cget("hover_color") if name == "transactions" else "transparent")

        if name == "login": self.login_frame.grid(row=0, column=1, sticky="nsew")
        else: self.login_frame.grid_forget()
        if name == "portfolio": self.portfolio_frame.grid(row=0, column=1, sticky="nsew")
        else: self.portfolio_frame.grid_forget()
        if name == "transactions": self.transactions_frame.grid(row=0, column=1, sticky="nsew")
        else: self.transactions_frame.grid_forget()

    # --- Eventos de Botones de Navegación ---
    def portfolio_button_event(self):
        self.select_frame_by_name("portfolio")
        self.update_portfolio_frame()

    def transactions_button_event(self):
        self.select_frame_by_name("transactions")
        self.update_transactions_frame()

    # --- Lógica Login/Logout ---
    def toggle_login_logout(self):
        if self.current_user:
            confirm = CTkMessagebox(title="Confirmar Logout", message="¿Estás seguro de que quieres cerrar sesión?",
                                    icon="question", option_1="Cancelar", option_2="Sí", parent=self)
            if confirm.get() == "Sí":
                self.current_user = None
                self.login_logout_button.configure(text="Login")
                self.portfolio_button.configure(state="disabled")
                self.transactions_button.configure(state="disabled")
                self.select_frame_by_name("login")
                self.title("Portfolio Tracker Pro")
                self._clear_portfolio_frame()
                self._clear_transactions_frame()
                logging.info("Sesión cerrada.")
        else:
            self.select_frame_by_name("login")

    # --- Métodos para limpiar frames ---
    def _clear_frame_widgets(self, frame):
         for widget in frame.winfo_children():
             widget.destroy()

    def _clear_portfolio_frame(self):
         self._clear_frame_widgets(self.portfolio_frame)

    def _clear_transactions_frame(self):
         self._clear_frame_widgets(self.transactions_frame)

    # --- Métodos para actualizar frames ---
    def update_portfolio_frame(self):
        self._clear_portfolio_frame()
        if not self.current_user:
            logging.warning("Intento de actualizar portafolio sin usuario logueado.")
            return

        # --- Frame Header ---
        header_frame = ctk.CTkFrame(self.portfolio_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        label = ctk.CTkLabel(header_frame, text=f"Resumen del Portafolio ({self.current_user.username})",
                             font=ctk.CTkFont(size=18, weight="bold"))
        label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        refresh_button = ctk.CTkButton(header_frame, text="Refrescar", width=100,
                                       command=self.update_portfolio_frame)
        refresh_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        # --- Obtener y Mostrar Datos ---
        try:
            logging.info(f"Obteniendo datos de portafolio para usuario ID: {self.current_user.id}")
            portfolio_details = crud.get_portfolio_performance(self.db, user_id=self.current_user.id)
            logging.info(f"Datos obtenidos: {len(portfolio_details)} activos.")

            # --- Caso sin Datos ---
            if not portfolio_details:
                no_data_label = ctk.CTkLabel(self.portfolio_frame, text="No hay posiciones abiertas en el portafolio.",
                                             font=ctk.CTkFont(size=14))
                no_data_label.grid(row=1, column=0, padx=20, pady=20, sticky="n")
                self._add_empty_portfolio_totals()
                return

            # --- Preparar Datos Tabla ---
            headers = ["Símbolo", "Cantidad", "Coste Medio", "Coste Total", "Precio Act.", "Valor Mercado", "P&L No Real.", "% P&L"]
            table_data = [headers]
            total_portfolio_market_value = Decimal(0)
            total_portfolio_cost_basis = Decimal(0)
            sorted_symbols = sorted(portfolio_details.keys())

            for symbol in sorted_symbols:
                data = portfolio_details[symbol]
                quantity = data["quantity"]
                avg_cost = data["average_cost_basis"]
                total_cost = data["total_cost_basis"]
                current_price = data["current_price"]
                market_value = data["market_value"]
                unrealized_pnl = data["unrealized_pnl"]
                unrealized_pnl_percent = data["unrealized_pnl_percent"]

                if market_value is not None: total_portfolio_market_value += market_value
                if total_cost is not None: total_portfolio_cost_basis += total_cost

                # Formateo
                q_prec = 8; p_prec = 4; v_prec = 2; pct_prec = 2
                quantity_str = f"{quantity:.{q_prec}f}".rstrip('0').rstrip('.') if quantity is not None else "N/A"
                avg_cost_str = f"{avg_cost:,.{p_prec}f}" if avg_cost is not None else "N/A"
                total_cost_str = f"{total_cost:,.{v_prec}f}" if total_cost is not None else "N/A"
                current_price_str = f"{current_price:,.{p_prec}f}" if current_price is not None else "N/A"
                market_value_str = f"{market_value:,.{v_prec}f}" if market_value is not None else "N/A"
                unrealized_pnl_str = f"{unrealized_pnl:,.{v_prec}f}" if unrealized_pnl is not None else "N/A"

                if unrealized_pnl_percent is None: pnl_percent_str = "N/A"
                elif unrealized_pnl_percent == Decimal('inf'): pnl_percent_str = "+Inf%"
                elif unrealized_pnl_percent == Decimal('-inf'): pnl_percent_str = "-Inf%"
                else: pnl_percent_str = f"{unrealized_pnl_percent:,.{pct_prec}f}%"

                table_data.append([
                    symbol, quantity_str, avg_cost_str, total_cost_str,
                    current_price_str, market_value_str, unrealized_pnl_str, pnl_percent_str
                ])

            # --- Crear Tabla ---
            table_frame = ctk.CTkScrollableFrame(self.portfolio_frame, corner_radius=0)
            table_frame.grid(row=1, column=0, padx=15, pady=(5,15), sticky="nsew")

            if len(table_data) > 1:
                table = CTkTable(master=table_frame, values=table_data,
                                 header_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                                 hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"],
                                 corner_radius=6)
                table.pack(expand=True, fill="both", padx=5, pady=5)
            else:
                 no_data_label = ctk.CTkLabel(table_frame, text="No se encontraron datos para mostrar.",
                                             font=ctk.CTkFont(size=14))
                 no_data_label.pack(padx=20, pady=20)

            # --- Mostrar Totales ---
            self._add_portfolio_totals(total_portfolio_cost_basis, total_portfolio_market_value)

        # --- Manejo de Errores ---
        except Exception as e:
            logging.error(f"Error al actualizar el frame del portafolio: {e}", exc_info=True)
            self._clear_portfolio_frame()
            header_frame = ctk.CTkFrame(self.portfolio_frame, fg_color="transparent")
            header_frame.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
            header_frame.grid_columnconfigure(1, weight=1)
            refresh_button = ctk.CTkButton(header_frame, text="Refrescar", width=100, command=self.update_portfolio_frame)
            refresh_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")
            error_label = ctk.CTkLabel(self.portfolio_frame,
                                       text=f"Error al cargar datos del portafolio:\n{e}\n\nIntenta refrescar o revisa los logs.",
                                       text_color="red", font=ctk.CTkFont(size=14), justify="left")
            error_label.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
            self._add_empty_portfolio_totals()

    # --- Métodos Auxiliares Portafolio ---
    def _add_portfolio_totals(self, total_cost, total_value):
        totals_frame = ctk.CTkFrame(self.portfolio_frame, fg_color="transparent")
        totals_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        totals_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(totals_frame, text="--- Totales ---", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=(0,5), sticky="w")
        ctk.CTkLabel(totals_frame, text="Coste Total Base:").grid(row=1, column=0, sticky="w", padx=5)
        ctk.CTkLabel(totals_frame, text=f"{total_cost:,.2f}", anchor="e").grid(row=1, column=1, sticky="e", padx=5)
        ctk.CTkLabel(totals_frame, text="Valor de Mercado Total:").grid(row=2, column=0, sticky="w", padx=5)
        ctk.CTkLabel(totals_frame, text=f"{total_value:,.2f}", anchor="e").grid(row=2, column=1, sticky="e", padx=5)

        total_unrealized_pnl = total_value - total_cost
        ctk.CTkLabel(totals_frame, text="P&L No Realizado Total:").grid(row=3, column=0, sticky="w", padx=5)
        ctk.CTkLabel(totals_frame, text=f"{total_unrealized_pnl:,.2f}", anchor="e").grid(row=3, column=1, sticky="e", padx=5)

        total_pnl_percent_str = "N/A"
        try:
            if abs(total_cost) > crud.ZERO_TOLERANCE:
                total_pnl_percent = (total_unrealized_pnl / total_cost) * Decimal(100)
                total_pnl_percent_str = f"{total_pnl_percent:,.2f}%"
            elif total_unrealized_pnl > crud.ZERO_TOLERANCE: total_pnl_percent_str = "+Inf%"
            elif total_unrealized_pnl < -crud.ZERO_TOLERANCE: total_pnl_percent_str = "-Inf%"
            else: total_pnl_percent_str = "0.00%"
        except (InvalidOperation, DivisionByZero):
            total_pnl_percent_str = "Error"

        ctk.CTkLabel(totals_frame, text="% P&L Total:").grid(row=4, column=0, sticky="w", padx=5)
        ctk.CTkLabel(totals_frame, text=total_pnl_percent_str, anchor="e").grid(row=4, column=1, sticky="e", padx=5)

    def _add_empty_portfolio_totals(self):
        self._add_portfolio_totals(Decimal(0), Decimal(0))


    # --- Actualizar Frame Transacciones ---
    def update_transactions_frame(self):
        self._clear_transactions_frame()
        if not self.current_user:
            logging.warning("Intento de actualizar transacciones sin usuario logueado.")
            return

        # --- Frame Header con Botones ---
        action_frame = ctk.CTkFrame(self.transactions_frame, fg_color="transparent")
        action_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        label = ctk.CTkLabel(action_frame, text=f"Historial de Transacciones ({self.current_user.username})",
                             font=ctk.CTkFont(size=18, weight="bold"))
        label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        add_button = ctk.CTkButton(action_frame, text="Añadir", width=80, command=self.add_transaction_dialog)
        add_button.grid(row=0, column=1, padx=(10, 5), pady=5, sticky="e")
        edit_button = ctk.CTkButton(action_frame, text="Editar", width=80, command=self.edit_transaction_dialog, state="disabled")
        edit_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        delete_button = ctk.CTkButton(action_frame, text="Eliminar", width=80, command=self.delete_transaction_confirm, state="disabled", fg_color="red", hover_color="darkred")
        delete_button.grid(row=0, column=3, padx=(5, 0), pady=5, sticky="e")
        self.edit_transaction_button = edit_button
        self.delete_transaction_button = delete_button

        # --- Obtener y Mostrar Datos ---
        try:
            logging.info(f"Obteniendo transacciones para usuario ID: {self.current_user.id}")
            transactions = crud.get_transactions_for_user(self.db, user_id=self.current_user.id)
            logging.info(f"Transacciones obtenidas: {len(transactions)}")

            # --- Caso sin Datos ---
            if not transactions:
                no_data_label = ctk.CTkLabel(self.transactions_frame, text="No hay transacciones registradas.",
                                             font=ctk.CTkFont(size=14))
                no_data_label.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
                return

            # --- Preparar Datos Tabla ---
            headers = ["ID", "Fecha", "Tipo", "Símbolo", "Cantidad", "Precio", "Coste Total", "Comisión", "Notas"]
            table_data = [headers]
            qty_quantizer = Decimal('0.00000001'); price_quantizer = Decimal('0.0001'); value_quantizer = Decimal('0.01')

            # ===========================================================
            # <<< INICIO BLOQUE CORREGIDO >>>
            # ===========================================================
            for tx in transactions:
                # Calcular coste total (considerando comisión/fees)
                total_cost = (tx.quantity * tx.price_per_unit)
                if tx.fees is not None:
                    if tx.transaction_type == models.TransactionType.BUY:
                        total_cost += tx.fees
                    elif tx.transaction_type == models.TransactionType.SELL:
                        total_cost -= tx.fees

                # Formatear valores
                tx_id_str = str(tx.id)
                # Usa tx.transaction_date en lugar de tx.timestamp
                timestamp_str = tx.transaction_date.strftime('%Y-%m-%d %H:%M:%S') if tx.transaction_date else "N/A"
                type_str = tx.transaction_type.name.capitalize() if tx.transaction_type else "N/A"
                symbol_str = tx.asset.symbol if tx.asset else "N/A"
                quantity_str = str(tx.quantity.quantize(qty_quantizer).normalize()) if tx.quantity is not None else "N/A"
                price_str = str(tx.price_per_unit.quantize(price_quantizer).normalize()) if tx.price_per_unit is not None else "N/A"
                total_cost_str = str(total_cost.quantize(value_quantizer)) if total_cost is not None else "N/A"
                commission_str = str(tx.fees.quantize(value_quantizer).normalize()) if tx.fees is not None else "N/A"
                notes_str = tx.notes if tx.notes else ""

                table_data.append([
                    tx_id_str, timestamp_str, type_str, symbol_str,
                    quantity_str, price_str, total_cost_str, commission_str, notes_str
                ])
            # ===========================================================
            # <<< FIN BLOQUE CORREGIDO >>>
            # ===========================================================

            # --- Crear Tabla ---
            table_frame = ctk.CTkScrollableFrame(self.transactions_frame, corner_radius=0)
            table_frame.grid(row=1, column=0, padx=15, pady=(5,15), sticky="nsew")

            if len(table_data) > 1:
                self.transaction_table = CTkTable(master=table_frame,
                                 values=table_data,
                                 header_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                                 hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"],
                                 corner_radius=6,
                                 command=self.transaction_table_click)
                self.transaction_table.pack(expand=True, fill="both", padx=5, pady=5)
            else:
                 no_data_label = ctk.CTkLabel(table_frame, text="No se encontraron datos para mostrar en la tabla.",
                                             font=ctk.CTkFont(size=14))
                 no_data_label.pack(padx=20, pady=20)

        # --- Manejo de Errores ---
        except Exception as e:
            logging.error(f"Error al actualizar el frame de transacciones: {e}", exc_info=True)
            self._clear_transactions_frame()
            action_frame = ctk.CTkFrame(self.transactions_frame, fg_color="transparent")
            action_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
            action_frame.grid_columnconfigure(0, weight=1)
            label = ctk.CTkLabel(action_frame, text=f"Historial de Transacciones ({self.current_user.username})", font=ctk.CTkFont(size=18, weight="bold"))
            label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
            add_button = ctk.CTkButton(action_frame, text="Añadir", width=80, command=self.add_transaction_dialog)
            add_button.grid(row=0, column=1, padx=(10, 5), pady=5, sticky="e")
            error_label = ctk.CTkLabel(self.transactions_frame,
                                       text=f"Error al cargar historial de transacciones:\n{e}\n\nRevisa los logs.",
                                       text_color="red", font=ctk.CTkFont(size=14), justify="left")
            error_label.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")


    # --- Click en Tabla Transacciones ---
    def transaction_table_click(self, click_data):
        try:
            row_index = click_data.get("row")
            edit_exists = hasattr(self, 'edit_transaction_button')
            delete_exists = hasattr(self, 'delete_transaction_button')

            if row_index is not None and row_index > 0:
                if hasattr(self, 'transaction_table') and self.transaction_table:
                    selected_id_str = self.transaction_table.get_row(row_index)[0]
                    self.selected_transaction_id = int(selected_id_str)
                    logging.info(f"Fila {row_index} seleccionada. ID Transacción: {self.selected_transaction_id}")
                    if edit_exists: self.edit_transaction_button.configure(state="normal")
                    if delete_exists: self.delete_transaction_button.configure(state="normal")
                else:
                    logging.warning("Intento de click en tabla de transacciones pero el widget no existe.")
                    self.selected_transaction_id = None
                    if edit_exists: self.edit_transaction_button.configure(state="disabled")
                    if delete_exists: self.delete_transaction_button.configure(state="disabled")
            else:
                self.selected_transaction_id = None
                if edit_exists: self.edit_transaction_button.configure(state="disabled")
                if delete_exists: self.delete_transaction_button.configure(state="disabled")
                logging.info("Clic en cabecera o fuera de fila, selección reseteada.")
        except Exception as e:
            logging.error(f"Error al procesar clic en tabla de transacciones: {e}", exc_info=True)
            self.selected_transaction_id = None
            if hasattr(self, 'edit_transaction_button'): self.edit_transaction_button.configure(state="disabled")
            if hasattr(self, 'delete_transaction_button'): self.delete_transaction_button.configure(state="disabled")


    # --- Diálogos (Pendiente de implementación completa) ---
    def add_transaction_dialog(self):
         if not self.current_user: return
         CTkMessagebox(title="Info", message="Función 'Añadir Transacción' pendiente de implementación.", icon="info", parent=self)

    def edit_transaction_dialog(self):
        if not self.current_user or self.selected_transaction_id is None:
            logging.warning("Intento de editar sin seleccionar transacción.")
            CTkMessagebox(title="Aviso", message="Por favor, selecciona una transacción de la tabla para editar.", icon="warning", parent=self)
            return
        CTkMessagebox(title="Info", message=f"Función 'Editar Transacción' (ID: {self.selected_transaction_id}) pendiente.", icon="info", parent=self)

    def delete_transaction_confirm(self):
        if not self.current_user or self.selected_transaction_id is None:
            logging.warning("Intento de eliminar sin seleccionar transacción.")
            CTkMessagebox(title="Aviso", message="Por favor, selecciona una transacción de la tabla para eliminar.", icon="warning", parent=self)
            return

        confirm = CTkMessagebox(title="Confirmar Eliminación",
                                message=f"¿Estás seguro de que quieres eliminar la transacción con ID {self.selected_transaction_id}?\nEsta acción no se puede deshacer.",
                                icon="warning", option_1="Cancelar", option_2="Eliminar", parent=self)

        if confirm.get() == "Eliminar":
            try:
                logging.info(f"Intentando eliminar transacción ID: {self.selected_transaction_id}")
                success = crud.delete_transaction(self.db, transaction_id=self.selected_transaction_id, user_id=self.current_user.id)
                if success:
                    logging.info(f"Transacción ID: {self.selected_transaction_id} eliminada.")
                    CTkMessagebox(title="Éxito", message="Transacción eliminada correctamente.", icon="check", parent=self)
                    self.selected_transaction_id = None
                    self.edit_transaction_button.configure(state="disabled")
                    self.delete_transaction_button.configure(state="disabled")
                    self.update_transactions_frame()
                    self.update_portfolio_frame()
                else:
                    logging.warning(f"No se pudo eliminar transacción ID: {self.selected_transaction_id}. No encontrada o sin permiso.")
                    CTkMessagebox(title="Error", message="No se pudo eliminar la transacción. Puede que ya no exista.", icon="cancel", parent=self)
                    self.update_transactions_frame()

            except Exception as e:
                logging.error(f"Error al eliminar transacción ID {self.selected_transaction_id}: {e}", exc_info=True)
                CTkMessagebox(title="Error", message=f"Ocurrió un error al intentar eliminar la transacción:\n{e}", icon="cancel", parent=self)


    # ========================================================================
    # <<< Métodos de Configuración y Lógica de Login (DENTRO de la clase) >>>
    # ========================================================================

    def _setup_login_frame(self):
        login_container = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        login_container.grid(row=0, column=0, padx=30, pady=30, sticky="")
        self.login_frame.grid_rowconfigure(0, weight=1)
        self.login_frame.grid_columnconfigure(0, weight=1)

        login_label = ctk.CTkLabel(login_container, text="Iniciar Sesión", font=ctk.CTkFont(size=20, weight="bold"))
        login_label.grid(row=0, column=0, padx=10, pady=(0, 15))

        username_entry = ctk.CTkEntry(login_container, placeholder_text="Nombre de usuario", width=250)
        username_entry.grid(row=1, column=0, padx=10, pady=10)

        password_entry = ctk.CTkEntry(login_container, placeholder_text="Contraseña", show="*", width=250)
        password_entry.grid(row=2, column=0, padx=10, pady=10)

        def attempt_login_callback(event=None):
            self._attempt_login(username_entry, password_entry)

        login_button = ctk.CTkButton(login_container, text="Login", command=attempt_login_callback, width=250)
        login_button.grid(row=3, column=0, padx=10, pady=(20, 10))

        username_entry.bind("<Return>", attempt_login_callback)
        password_entry.bind("<Return>", attempt_login_callback)

        def show_register_info():
             CTkMessagebox(title="Registro", message="La función de registro aún no está implementada en la GUI.\nPor favor, usa la versión de consola para registrarte.", icon="info", parent=self)

        register_button = ctk.CTkButton(login_container, text="Registrar (Info)", command=show_register_info, width=150, fg_color="gray")
        register_button.grid(row=4, column=0, padx=10, pady=10)

        username_entry.focus()

    def _attempt_login(self, username_entry, password_entry):
        username = username_entry.get()
        password = password_entry.get()
        if not username or not password:
            CTkMessagebox(title="Error de Validación", message="El nombre de usuario y la contraseña no pueden estar vacíos.", icon="warning", parent=self)
            return

        user = crud.get_user_by_username(self.db, username=username)
        login_ok = False
        if user:
            try:
                login_ok = crud.verify_password(password, user.hashed_password)
            except AttributeError as ae:
                 if "'bcrypt' has no attribute '__about__'" in str(ae):
                     logging.warning("Error conocido al leer versión de bcrypt, reintentando verificación...")
                     try: login_ok = crud.verify_password(password, user.hashed_password)
                     except Exception as verify_e: logging.error(f"Error durante el reintento de verificación: {verify_e}", exc_info=True); login_ok = False
                 else:
                     logging.error(f"AttributeError inesperado en verificación: {ae}", exc_info=True); login_ok = False
                     CTkMessagebox(title="Error Interno", message="Error al verificar contraseña.", icon="cancel", parent=self)
            except Exception as e:
                logging.error(f"Error inesperado en verify_password: {e}", exc_info=True); login_ok = False
                CTkMessagebox(title="Error Interno", message="Error inesperado durante login.", icon="cancel", parent=self)

        if login_ok:
            self.current_user = user
            self.login_logout_button.configure(text="Logout")
            self.portfolio_button.configure(state="normal")
            self.transactions_button.configure(state="normal")
            self.title(f"Portfolio Tracker Pro - {user.username}")
            self.select_frame_by_name("portfolio")
            self.update_portfolio_frame()
            logging.info(f"Usuario '{user.username}' inició sesión.")
            username_entry.delete(0, "end")
            password_entry.delete(0, "end")
            self.portfolio_button.focus()
        else:
            if user:
                CTkMessagebox(title="Error de Login", message="Nombre de usuario o contraseña incorrectos.", icon="cancel", parent=self)
            elif not user and username:
                CTkMessagebox(title="Error de Login", message=f"El usuario '{username}' no existe.", icon="cancel", parent=self)
            password_entry.delete(0, "end")
            username_entry.focus()


# --- Punto de Entrada para la GUI ---
def run_gui():
    """Inicia la aplicación GUI."""
    db_session = SessionLocal()
    app = None
    try:
        app = PortfolioApp(db_session)
        app._setup_login_frame()
        app.mainloop()

    except Exception as e:
        logging.critical("Error fatal al iniciar o durante la ejecución de la GUI", exc_info=True)
        try:
            root_error = ctk.CTk(); root_error.withdraw()
            CTkMessagebox(title="Error Fatal",
                          message=f"Ocurrió un error crítico:\n{e}\n\nLa aplicación se cerrará.",
                          icon="cancel")
            root_error.destroy()
        except Exception as mb_error:
            print(f"[CRITICAL] No se pudo mostrar el error en messagebox: {mb_error}")
            print(f"[CRITICAL] Error original: {e}")
        if db_session:
            try: db_session.close()
            except Exception as db_close_err: logging.error(f"Error al cerrar sesión BD en manejo excepción: {db_close_err}")
        sys.exit(1)
    finally:
        db_closed = False
        if app and hasattr(app, 'db') and app.db:
             try:
                 print("[*] Cerrando sesión de base de datos (GUI).")
                 app.db.close()
                 db_closed = True
             except Exception as db_close_norm_err: logging.error(f"Error al cerrar sesión BD normalmente: {db_close_norm_err}")
        if not db_closed and db_session:
             try:
                 print("[*] Cerrando sesión de base de datos (GUI - fallback).")
                 db_session.close()
             except Exception as db_close_fall_err: logging.error(f"Error al cerrar sesión BD en fallback: {db_close_fall_err}")