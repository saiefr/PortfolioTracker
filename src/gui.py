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
        # Resetear selección y estado de botones de edición/eliminación al cambiar de frame
        self.selected_transaction_id = None
        if hasattr(self, 'edit_transaction_button'): self.edit_transaction_button.configure(state="disabled")
        if hasattr(self, 'delete_transaction_button'): self.delete_transaction_button.configure(state="disabled")

        # Actualizar color de botones de navegación
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
        self.update_portfolio_frame()

    def transactions_button_event(self):
        self.select_frame_by_name("transactions")
        self.update_transactions_frame()

    # --- Lógica Login/Logout ---
    def toggle_login_logout(self):
        if self.current_user:
            # Si hay usuario logueado, mostrar confirmación de logout
            confirm = CTkMessagebox(title="Confirmar Logout", message="¿Estás seguro de que quieres cerrar sesión?",
                                    icon="question", option_1="Cancelar", option_2="Sí")
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
            # Si no hay usuario, ir al frame de login
            self.select_frame_by_name("login")

    # --- Métodos para limpiar frames ---
    def _clear_frame_widgets(self, frame):
         # Elimina todos los widgets hijos de un frame dado
         for widget in frame.winfo_children():
             widget.destroy()

    def _clear_portfolio_frame(self):
         # Limpia específicamente el frame del portafolio
         self._clear_frame_widgets(self.portfolio_frame)

    def _clear_transactions_frame(self):
         # Limpia específicamente el frame de transacciones
         self._clear_frame_widgets(self.transactions_frame)

    # --- Métodos para actualizar frames ---
    def update_portfolio_frame(self):
        self._clear_portfolio_frame()
        if not self.current_user: return # No hacer nada si no hay usuario

        # --- Cabecera del Frame Portafolio ---
        header_frame = ctk.CTkFrame(self.portfolio_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1) # Label se expande a la izquierda
        label = ctk.CTkLabel(header_frame, text=f"Resumen del Portafolio ({self.current_user.username})", font=ctk.CTkFont(size=18, weight="bold"))
        label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        refresh_button = ctk.CTkButton(header_frame, text="Refrescar", width=100, command=self.update_portfolio_frame)
        refresh_button.grid(row=0, column=1, padx=5, pady=5, sticky="e") # Botón a la derecha

        try:
            # --- Obtener y Mostrar Datos del Portafolio ---
            portfolio_details = crud.get_portfolio_performance(self.db, user_id=self.current_user.id)

            if not portfolio_details:
                # Mostrar mensaje si no hay posiciones
                no_data_label = ctk.CTkLabel(self.portfolio_frame, text="No hay posiciones abiertas en el portafolio.", font=ctk.CTkFont(size=14))
                no_data_label.grid(row=1, column=0, padx=20, pady=20, sticky="n")
                self._add_empty_portfolio_totals() # Mostrar totales en cero
                return

            # --- Preparar Datos para la Tabla ---
            headers = ["Símbolo", "Cantidad", "Coste Medio", "Coste Total", "Precio Act.", "Valor Mercado", "P&L No Real.", "% P&L"]
            table_data = [headers]
            total_portfolio_market_value = Decimal(0)
            total_portfolio_cost_basis = Decimal(0)

            sorted_symbols = sorted(portfolio_details.keys()) # Ordenar por símbolo

            for symbol in sorted_symbols:
                data = portfolio_details[symbol]
                quantity, avg_cost, total_cost, current_price, market_value, unrealized_pnl, unrealized_pnl_percent = (
                    data["quantity"], data["average_cost_basis"], data["total_cost_basis"], data["current_price"],
                    data["market_value"], data["unrealized_pnl"], data["unrealized_pnl_percent"]
                )

                # Acumular totales
                if market_value is not None: total_portfolio_market_value += market_value
                if total_cost is not None: total_portfolio_cost_basis += total_cost

                # Formatear números para mostrar (con precisión y manejo de N/A)
                q_prec, p_prec, v_prec, pct_prec = 8, 4, 2, 2 # Precisiones
                quantity_str = f"{quantity:.{q_prec}f}".rstrip('0').rstrip('.') if quantity is not None else "N/A"
                avg_cost_str = f"{avg_cost:,.{p_prec}f}" if avg_cost is not None else "N/A"
                total_cost_str = f"{total_cost:,.{v_prec}f}" if total_cost is not None else "N/A"
                current_price_str = f"{current_price:,.{p_prec}f}" if current_price is not None else "N/A"
                market_value_str = f"{market_value:,.{v_prec}f}" if market_value is not None else "N/A"
                unrealized_pnl_str = f"{unrealized_pnl:,.{v_prec}f}" if unrealized_pnl is not None else "N/A"

                # Formateo especial para % P&L (infinito, N/A)
                if unrealized_pnl_percent is None: pnl_percent_str = "N/A"
                elif unrealized_pnl_percent == Decimal('inf'): pnl_percent_str = "+Inf%"
                elif unrealized_pnl_percent == Decimal('-inf'): pnl_percent_str = "-Inf%"
                else: pnl_percent_str = f"{unrealized_pnl_percent:,.{pct_prec}f}%"

                table_data.append([symbol, quantity_str, avg_cost_str, total_cost_str, current_price_str, market_value_str, unrealized_pnl_str, pnl_percent_str])

            # --- Crear y Mostrar Tabla ---
            table_frame = ctk.CTkScrollableFrame(self.portfolio_frame, corner_radius=0)
            table_frame.grid(row=1, column=0, padx=15, pady=(5,15), sticky="nsew") # Ocupa el espacio principal

            if len(table_data) > 1: # Si hay datos además de la cabecera
                table = CTkTable(master=table_frame, values=table_data,
                                 header_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                                 hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"],
                                 corner_radius=6)
                table.pack(expand=True, fill="both", padx=5, pady=5)
            else:
                 # Mensaje si por alguna razón no hay datos en la tabla (no debería pasar si portfolio_details no estaba vacío)
                 no_data_label = ctk.CTkLabel(table_frame, text="No se encontraron datos para mostrar.", font=ctk.CTkFont(size=14))
                 no_data_label.pack(padx=20, pady=20)

            # --- Añadir Totales del Portafolio ---
            self._add_portfolio_totals(total_portfolio_cost_basis, total_portfolio_market_value)

        except Exception as e:
            # --- Manejo de Errores al Cargar Portafolio ---
            logging.error(f"Error al actualizar el frame del portafolio: {e}", exc_info=True)
            self._clear_portfolio_frame() # Limpiar por si algo se dibujó parcialmente

            # Re-crear cabecera mínima con botón refrescar
            header_frame = ctk.CTkFrame(self.portfolio_frame, fg_color="transparent")
            header_frame.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
            header_frame.grid_columnconfigure(1, weight=1) # Botón a la derecha
            refresh_button = ctk.CTkButton(header_frame, text="Refrescar", width=100, command=self.update_portfolio_frame)
            refresh_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")

            # Mostrar mensaje de error
            error_label = ctk.CTkLabel(self.portfolio_frame,
                                       text=f"Error al cargar datos del portafolio:\n{e}\n\nIntenta refrescar o revisa los logs.",
                                       text_color="red", font=ctk.CTkFont(size=14), justify="left")
            error_label.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
            self._add_empty_portfolio_totals() # Mostrar totales en cero

    # --- Métodos Auxiliares Portafolio ---
    def _add_portfolio_totals(self, total_cost, total_value):
        # Frame para mostrar los totales debajo de la tabla
        totals_frame = ctk.CTkFrame(self.portfolio_frame, fg_color="transparent")
        totals_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        totals_frame.grid_columnconfigure(1, weight=1) # Columna de valores se expande

        ctk.CTkLabel(totals_frame, text="--- Totales ---", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=(0,5), sticky="w")

        ctk.CTkLabel(totals_frame, text="Coste Total Base:").grid(row=1, column=0, sticky="w", padx=5)
        ctk.CTkLabel(totals_frame, text=f"{total_cost:,.2f}", anchor="e").grid(row=1, column=1, sticky="e", padx=5)

        ctk.CTkLabel(totals_frame, text="Valor de Mercado Total:").grid(row=2, column=0, sticky="w", padx=5)
        ctk.CTkLabel(totals_frame, text=f"{total_value:,.2f}", anchor="e").grid(row=2, column=1, sticky="e", padx=5)

        total_unrealized_pnl = total_value - total_cost
        ctk.CTkLabel(totals_frame, text="P&L No Realizado Total:").grid(row=3, column=0, sticky="w", padx=5)
        ctk.CTkLabel(totals_frame, text=f"{total_unrealized_pnl:,.2f}", anchor="e").grid(row=3, column=1, sticky="e", padx=5)

        # Calcular % P&L Total con manejo de división por cero e infinito
        total_pnl_percent_str = "N/A"
        try:
            if abs(total_cost) > crud.ZERO_TOLERANCE:
                total_pnl_percent = (total_unrealized_pnl / total_cost) * Decimal(100)
                total_pnl_percent_str = f"{total_pnl_percent:,.2f}%"
            elif total_unrealized_pnl > crud.ZERO_TOLERANCE: total_pnl_percent_str = "+Inf%"
            elif total_unrealized_pnl < -crud.ZERO_TOLERANCE: total_pnl_percent_str = "-Inf%"
            else: total_pnl_percent_str = "0.00%" # Si coste es 0 y PNL es 0
        except (InvalidOperation, DivisionByZero):
            total_pnl_percent_str = "Error" # En caso de error inesperado

        ctk.CTkLabel(totals_frame, text="% P&L Total:").grid(row=4, column=0, sticky="w", padx=5)
        ctk.CTkLabel(totals_frame, text=total_pnl_percent_str, anchor="e").grid(row=4, column=1, sticky="e", padx=5)

    def _add_empty_portfolio_totals(self):
        # Llama a la función de totales con valores cero
        self._add_portfolio_totals(Decimal(0), Decimal(0))


    # --- Actualizar Frame Transacciones ---
    def update_transactions_frame(self):
        self._clear_transactions_frame()
        if not self.current_user: return # No hacer nada si no hay usuario

        # --- Cabecera y Botones de Acción ---
        action_frame = ctk.CTkFrame(self.transactions_frame, fg_color="transparent")
        action_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1) # Label a la izquierda

        label = ctk.CTkLabel(action_frame, text=f"Historial de Transacciones ({self.current_user.username})", font=ctk.CTkFont(size=18, weight="bold"))
        label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Botones a la derecha
        add_button = ctk.CTkButton(action_frame, text="Añadir", width=80, command=self.add_transaction_dialog)
        add_button.grid(row=0, column=1, padx=(10, 5), pady=5, sticky="e")
        edit_button = ctk.CTkButton(action_frame, text="Editar", width=80, command=self.edit_transaction_dialog, state="disabled")
        edit_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        delete_button = ctk.CTkButton(action_frame, text="Eliminar", width=80, command=self.delete_transaction_confirm, state="disabled", fg_color="red", hover_color="darkred")
        delete_button.grid(row=0, column=3, padx=(5, 0), pady=5, sticky="e")

        # Guardar referencias a los botones para habilitar/deshabilitar al seleccionar fila
        self.edit_transaction_button = edit_button
        self.delete_transaction_button = delete_button

        try:
            # --- Obtener y Mostrar Transacciones ---
            transactions = crud.get_transactions_for_user(self.db, user_id=self.current_user.id)

            if not transactions:
                # Mostrar mensaje si no hay transacciones
                no_data_label = ctk.CTkLabel(self.transactions_frame, text="No hay transacciones registradas.", font=ctk.CTkFont(size=14))
                no_data_label.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
                return

            # --- Preparar Datos para la Tabla ---
            headers = ["ID", "Fecha", "Tipo", "Símbolo", "Cantidad", "Precio", "Coste Total", "Comisión", "Notas"]
            table_data = [headers]

            for tx in transactions:
                # Calcular coste total incluyendo comisiones
                total_cost = (tx.quantity * tx.price_per_unit)
                if tx.fees is not None:
                    if tx.transaction_type == models.TransactionType.BUY: total_cost += tx.fees
                    elif tx.transaction_type == models.TransactionType.SELL: total_cost -= tx.fees

                # Formatear datos para la fila
                tx_id_str = str(tx.id)
                timestamp_str = tx.transaction_date.strftime('%d-%m-%Y %H:%M') if tx.transaction_date else "N/A"
                type_str = tx.transaction_type.name.capitalize() if tx.transaction_type else "N/A"
                symbol_str = tx.asset.symbol if tx.asset else "N/A"

                # Formateo de números decimales
                qty_decimals, price_decimals, value_decimals = 8, 4, 2
                quantity_str = f"{tx.quantity:.{qty_decimals}f}".rstrip('0').rstrip('.') if tx.quantity is not None else "N/A"
                price_str = f"{tx.price_per_unit:.{price_decimals}f}".rstrip('0').rstrip('.') if tx.price_per_unit is not None else "N/A"
                total_cost_str = f"{total_cost:,.{value_decimals}f}" if total_cost is not None else "N/A"
                commission_str = f"{tx.fees:.{value_decimals}f}".rstrip('0').rstrip('.') if tx.fees is not None else "N/A"
                notes_str = tx.notes if tx.notes else ""

                table_data.append([tx_id_str, timestamp_str, type_str, symbol_str, quantity_str, price_str, total_cost_str, commission_str, notes_str])

            # --- Crear y Mostrar Tabla ---
            table_frame = ctk.CTkScrollableFrame(self.transactions_frame, corner_radius=0)
            table_frame.grid(row=1, column=0, padx=15, pady=(5,15), sticky="nsew") # Ocupa el espacio principal

            if len(table_data) > 1: # Si hay datos además de la cabecera
                self.transaction_table = CTkTable(master=table_frame, values=table_data,
                                                  header_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                                                  hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"],
                                                  corner_radius=6,
                                                  command=self.transaction_table_click) # Añadir comando para click
                self.transaction_table.pack(expand=True, fill="both", padx=5, pady=5)
            else:
                 # Mensaje si no hay datos (no debería ocurrir si 'transactions' no estaba vacío)
                 no_data_label = ctk.CTkLabel(table_frame, text="No se encontraron datos para mostrar en la tabla.", font=ctk.CTkFont(size=14))
                 no_data_label.pack(padx=20, pady=20)

        except Exception as e:
            # --- Manejo de Errores al Cargar Transacciones ---
            logging.error(f"Error al actualizar el frame de transacciones: {e}", exc_info=True)
            self._clear_transactions_frame() # Limpiar por si acaso

            # Re-crear cabecera mínima con botón añadir
            action_frame = ctk.CTkFrame(self.transactions_frame, fg_color="transparent")
            action_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
            action_frame.grid_columnconfigure(0, weight=1)
            label = ctk.CTkLabel(action_frame, text=f"Historial de Transacciones ({self.current_user.username})", font=ctk.CTkFont(size=18, weight="bold"))
            label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
            add_button = ctk.CTkButton(action_frame, text="Añadir", width=80, command=self.add_transaction_dialog)
            add_button.grid(row=0, column=1, padx=(10, 5), pady=5, sticky="e")

            # Mostrar mensaje de error
            error_label = ctk.CTkLabel(self.transactions_frame,
                                       text=f"Error al cargar historial de transacciones:\n{e}\n\nRevisa los logs.",
                                       text_color="red", font=ctk.CTkFont(size=14), justify="left")
            error_label.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")


    # --- Click en Tabla Transacciones ---
    def transaction_table_click(self, click_data):
        # Este método se llama cuando se hace clic en una celda de la tabla de transacciones
        try:
            row_index = click_data.get("row") # Obtener el índice de la fila clickeada
            edit_exists = hasattr(self, 'edit_transaction_button') # Verificar si los botones existen
            delete_exists = hasattr(self, 'delete_transaction_button')

            if row_index is not None and row_index > 0: # Ignorar click en cabecera (fila 0)
                if hasattr(self, 'transaction_table') and self.transaction_table:
                    # Obtener el ID de la transacción de la primera columna de la fila seleccionada
                    selected_id_str = self.transaction_table.get_row(row_index)[0]
                    self.selected_transaction_id = int(selected_id_str)
                    logging.info(f"Fila {row_index} seleccionada. ID Transacción: {self.selected_transaction_id}")
                    # Habilitar botones de editar y eliminar
                    if edit_exists: self.edit_transaction_button.configure(state="normal")
                    if delete_exists: self.delete_transaction_button.configure(state="normal")
                else:
                    # Caso raro: se hizo click pero la tabla no existe
                    logging.warning("Intento de click en tabla de transacciones pero el widget no existe.")
                    self.selected_transaction_id = None
                    if edit_exists: self.edit_transaction_button.configure(state="disabled")
                    if delete_exists: self.delete_transaction_button.configure(state="disabled")
            else:
                # Si se hizo click en la cabecera o fuera de una fila válida
                self.selected_transaction_id = None
                # Deshabilitar botones
                if edit_exists: self.edit_transaction_button.configure(state="disabled")
                if delete_exists: self.delete_transaction_button.configure(state="disabled")
                logging.info("Clic en cabecera o fuera de fila, selección reseteada.")
        except Exception as e:
            # Manejo de errores inesperados durante el click
            logging.error(f"Error al procesar clic en tabla de transacciones: {e}", exc_info=True)
            self.selected_transaction_id = None
            if hasattr(self, 'edit_transaction_button'): self.edit_transaction_button.configure(state="disabled")
            if hasattr(self, 'delete_transaction_button'): self.delete_transaction_button.configure(state="disabled")


    # --- Diálogos ---
    def add_transaction_dialog(self):
        # Abre una ventana Toplevel para añadir una nueva transacción
        if not self.current_user: return # Requiere usuario logueado

        dialog = ctk.CTkToplevel(self)
        dialog.title("Añadir Nueva Transacción")
        dialog.geometry("450x450")
        dialog.resizable(False, False)
        dialog.transient(self) # Hacer que la ventana sea modal respecto a la principal
        dialog.grab_set()      # Capturar eventos para esta ventana

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        main_frame.grid_columnconfigure(1, weight=1) # Columna de entradas se expande

        row_num = 0 # Contador para las filas del grid

        # --- Widgets de Entrada ---
        ctk.CTkLabel(main_frame, text="Símbolo:").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        symbol_entry = ctk.CTkEntry(main_frame, placeholder_text="Ej: AAPL, BTC-USD")
        symbol_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Tipo:").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        type_combo = ctk.CTkComboBox(main_frame, values=["Compra", "Venta"], state="readonly")
        type_combo.set("Compra") # Valor por defecto
        type_combo.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Cantidad:").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        quantity_entry = ctk.CTkEntry(main_frame, placeholder_text="Ej: 10.5 o 10,5")
        quantity_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Precio Unitario:").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        price_entry = ctk.CTkEntry(main_frame, placeholder_text="Ej: 150.75 o 150,75")
        price_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Fecha (YYYY-MM-DD HH:MM):").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M') # Fecha/hora actual por defecto
        date_entry = ctk.CTkEntry(main_frame, placeholder_text=now_str)
        date_entry.insert(0, now_str)
        date_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Comisión:").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        fees_entry = ctk.CTkEntry(main_frame, placeholder_text="Ej: 1.99 o 1,99")
        fees_entry.insert(0, "0") # Comisión cero por defecto
        fees_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Notas (Opcional):").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        notes_entry = ctk.CTkEntry(main_frame)
        notes_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        # --- Botones Guardar/Cancelar ---
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=row_num, column=0, columnspan=2, pady=(15, 0))
        button_frame.grid_columnconfigure((0, 1), weight=1) # Centrar botones

        save_button = ctk.CTkButton(button_frame, text="Guardar", width=100,
                                    command=lambda: self._save_new_transaction(dialog, symbol_entry, type_combo, quantity_entry,
                                                                               price_entry, date_entry, fees_entry, notes_entry))
        save_button.grid(row=0, column=0, padx=10)

        cancel_button = ctk.CTkButton(button_frame, text="Cancelar", width=100, fg_color="gray", command=dialog.destroy)
        cancel_button.grid(row=0, column=1, padx=10)

        symbol_entry.focus() # Poner el foco en el primer campo

    def _save_new_transaction(self, dialog, symbol_entry, type_combo, quantity_entry,
                              price_entry, date_entry, fees_entry, notes_entry):
        # Lógica para guardar la nueva transacción introducida en el diálogo
        logging.info("--- Iniciando _save_new_transaction ---")
        # --- Obtener y Limpiar Datos ---
        symbol = symbol_entry.get().strip().upper()
        tx_type_str = type_combo.get() # Es "Compra" o "Venta"
        quantity_str = quantity_entry.get().strip().replace(',', '.') # Reemplazar coma por punto
        price_str = price_entry.get().strip().replace(',', '.')
        date_str = date_entry.get().strip()
        fees_str = fees_entry.get().strip().replace(',', '.')
        notes = notes_entry.get().strip()
        logging.info(f"Datos obtenidos (coma->punto): S={symbol}, T={tx_type_str}, Q={quantity_str}, P={price_str}, D={date_str}, F={fees_str}")

        # --- Validación de Campos Obligatorios ---
        if not all([symbol, tx_type_str, quantity_str, price_str, date_str, fees_str]):
            logging.warning("Validación fallida: Campos obligatorios.")
            CTkMessagebox(title="Error de Validación", message="Todos los campos excepto Notas son obligatorios.", icon="warning")
            return

        # --- Validación: Existencia del Activo ---
        logging.info(f"Buscando activo: {symbol} para user ID: {self.current_user.id}")
        asset = crud.get_asset_by_symbol(self.db, symbol=symbol, owner_id=self.current_user.id)
        if not asset:
            logging.warning(f"Validación fallida: Activo '{symbol}' no encontrado.")
            CTkMessagebox(title="Error de Validación", message=f"El activo con símbolo '{symbol}' no existe en la base de datos para este usuario.\n\nPor favor, crea el activo primero (funcionalidad pendiente) o verifica el símbolo.", icon="cancel")
            return
        asset_id = asset.id
        logging.info(f"Activo encontrado: ID={asset_id}")

        # --- Validación: Tipo de Transacción ---
        try:
            if tx_type_str == "Compra": tx_type_enum = models.TransactionType.BUY
            elif tx_type_str == "Venta": tx_type_enum = models.TransactionType.SELL
            else: raise ValueError("Tipo de transacción inválido.") # No debería ocurrir con ComboBox readonly
            logging.info(f"Tipo validado: {tx_type_enum.name}")
        except ValueError as e:
             logging.warning(f"Validación fallida: Tipo - {e}")
             CTkMessagebox(title="Error de Validación", message=str(e), icon="warning")
             return

        # --- Validación: Cantidad ---
        try:
            quantity_dec = Decimal(quantity_str)
            if quantity_dec <= crud.ZERO_TOLERANCE: raise ValueError("La cantidad debe ser mayor que cero.")
        except InvalidOperation:
            logging.warning("Validación fallida: Cantidad - InvalidOperation")
            CTkMessagebox(title="Error de Validación", message="Valor inválido para Cantidad (debe ser numérico).", icon="warning")
            return
        except ValueError as e: # Captura el "La cantidad debe ser > 0"
            logging.warning(f"Validación fallida: Cantidad - {e}")
            CTkMessagebox(title="Error de Validación", message=str(e), icon="warning")
            return

        # --- Validación: Precio ---
        try:
            price_dec = Decimal(price_str)
            if price_dec < 0: raise ValueError("El precio no puede ser negativo.")
        except InvalidOperation:
            logging.warning("Validación fallida: Precio - InvalidOperation")
            CTkMessagebox(title="Error de Validación", message="Valor inválido para Precio Unitario (debe ser numérico).", icon="warning")
            return
        except ValueError as e: # Captura el "El precio no puede ser negativo"
            logging.warning(f"Validación fallida: Precio - {e}")
            CTkMessagebox(title="Error de Validación", message=str(e), icon="warning")
            return

        # --- Validación: Comisión ---
        try:
            fees_dec = Decimal(fees_str)
            if fees_dec < 0: raise ValueError("La comisión no puede ser negativa.")
        except InvalidOperation:
            logging.warning("Validación fallida: Comisión - InvalidOperation")
            CTkMessagebox(title="Error de Validación", message="Valor inválido para Comisión (debe ser numérico).", icon="warning")
            return
        except ValueError as e: # Captura el "La comisión no puede ser negativa"
            logging.warning(f"Validación fallida: Comisión - {e}")
            CTkMessagebox(title="Error de Validación", message=str(e), icon="warning")
            return

        logging.info(f"Números validados: Q={quantity_dec}, P={price_dec}, F={fees_dec}")

        # --- Validación: Fecha ---
        date_obj = None
        supported_formats = ['%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'] # Formatos aceptados
        for fmt in supported_formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                break # Salir del bucle si un formato funciona
            except ValueError:
                continue # Probar el siguiente formato
        if date_obj is None:
            # Si ningún formato funcionó
            logging.warning("Validación fallida: Fecha - Formato inválido")
            CTkMessagebox(title="Error de Validación", message=f"Formato de fecha inválido. Usa YYYY-MM-DD HH:MM o YYYY-MM-DD.", icon="warning")
            return
        logging.info(f"Fecha validada: {date_obj}")

        # --- Crear Transacción en la Base de Datos ---
        try:
            logging.info("--- Llamando a crud.create_transaction ---")
            new_transaction = crud.create_transaction(
                db=self.db,
                owner_id=self.current_user.id,
                asset_id=asset_id,
                transaction_type=tx_type_enum,
                quantity=quantity_dec,
                price_per_unit=price_dec,
                transaction_date=date_obj,
                fees=fees_dec,
                notes=notes if notes else None # Pasar None si las notas están vacías
            )
            if new_transaction:
                 logging.info(f"--- crud.create_transaction retornó: ID {new_transaction.id} ---")
                 CTkMessagebox(title="Éxito", message="Transacción añadida correctamente.", icon="check") # Mensaje en ventana principal
                 dialog.destroy() # Cerrar el diálogo
                 self.update_transactions_frame() # Actualizar tabla de transacciones
                 self.update_portfolio_frame()    # Actualizar resumen del portafolio
            else:
                 # Esto no debería ocurrir si create_transaction no lanza excepción pero no retorna objeto
                 logging.error("--- crud.create_transaction retornó None o Falsy ---")
                 CTkMessagebox(title="Error", message="La función CRUD no retornó una transacción válida.", icon="cancel")

        except ValueError as ve: # Errores de validación desde CRUD (aunque la mayoría se validan aquí)
            logging.error(f"Error de valor al crear transacción: {ve}")
            CTkMessagebox(title="Error al Guardar", message=f"Error: {ve}", icon="cancel")
        except Exception as e: # Otros errores inesperados (ej. DB)
            logging.error(f"Error inesperado al crear transacción: {e}", exc_info=True)
            CTkMessagebox(title="Error Inesperado", message=f"Ocurrió un error inesperado al guardar:\n{e}", icon="cancel")
        logging.info("--- Fin _save_new_transaction ---")

    # --- Diálogo para editar transacción (con corrección de tipo) ---
    def edit_transaction_dialog(self):
        # Abre una ventana Toplevel para editar una transacción existente
        if not self.current_user or self.selected_transaction_id is None:
            CTkMessagebox(title="Aviso", message="Por favor, selecciona una transacción de la tabla para editar.", icon="warning")
            return

        logging.info(f"Iniciando edición para transacción ID: {self.selected_transaction_id}")
        # Obtener los datos actuales de la transacción
        transaction = crud.get_transaction(self.db, transaction_id=self.selected_transaction_id, owner_id=self.current_user.id)

        if not transaction:
            logging.error(f"No se encontró la transacción con ID {self.selected_transaction_id} para editar.")
            CTkMessagebox(title="Error", message="No se encontró la transacción seleccionada. Puede haber sido eliminada.", icon="cancel")
            self.selected_transaction_id = None # Resetear selección
            if hasattr(self, 'edit_transaction_button'): self.edit_transaction_button.configure(state="disabled")
            if hasattr(self, 'delete_transaction_button'): self.delete_transaction_button.configure(state="disabled")
            return

        # Crear el diálogo
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Editar Transacción (ID: {transaction.id})")
        dialog.geometry("450x450")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        main_frame.grid_columnconfigure(1, weight=1)

        row_num = 0

        # --- Widgets de Entrada (pre-rellenados) ---
        ctk.CTkLabel(main_frame, text="Símbolo:").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        # Símbolo es de solo lectura para evitar cambiar el asset_id fácilmente
        symbol_label = ctk.CTkLabel(main_frame, text=transaction.asset.symbol, font=ctk.CTkFont(weight="bold"))
        symbol_label.grid(row=row_num, column=1, padx=5, pady=8, sticky="w"); row_num += 1

        ctk.CTkLabel(main_frame, text="Tipo:").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        # Usar "Compra"/"Venta" consistentemente
        type_combo = ctk.CTkComboBox(main_frame, values=["Compra", "Venta"], state="readonly")
        # Mapear el enum al string correcto para el ComboBox
        current_type_str = "Compra" if transaction.transaction_type == models.TransactionType.BUY else "Venta"
        type_combo.set(current_type_str) # Establecer valor actual ("Compra" o "Venta")
        type_combo.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Cantidad:").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        quantity_entry = ctk.CTkEntry(main_frame)
        # Formatear Decimal a string para el Entry
        quantity_str = f"{transaction.quantity:.8f}".rstrip('0').rstrip('.') if transaction.quantity is not None else ""
        quantity_entry.insert(0, quantity_str)
        quantity_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Precio Unitario:").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        price_entry = ctk.CTkEntry(main_frame)
        # Formatear Decimal a string
        price_str = f"{transaction.price_per_unit:.4f}".rstrip('0').rstrip('.') if transaction.price_per_unit is not None else ""
        price_entry.insert(0, price_str)
        price_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Fecha (YYYY-MM-DD HH:MM):").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        date_entry = ctk.CTkEntry(main_frame)
        # Formatear datetime a string
        date_str = transaction.transaction_date.strftime('%Y-%m-%d %H:%M') if transaction.transaction_date else ""
        date_entry.insert(0, date_str)
        date_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Comisión:").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        fees_entry = ctk.CTkEntry(main_frame)
        # Formatear Decimal a string
        fees_str = f"{transaction.fees:.2f}".rstrip('0').rstrip('.') if transaction.fees is not None else "0"
        fees_entry.insert(0, fees_str)
        fees_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        ctk.CTkLabel(main_frame, text="Notas (Opcional):").grid(row=row_num, column=0, padx=5, pady=8, sticky="w")
        notes_entry = ctk.CTkEntry(main_frame)
        notes_entry.insert(0, transaction.notes if transaction.notes else "") # Insertar notas actuales
        notes_entry.grid(row=row_num, column=1, padx=5, pady=8, sticky="ew"); row_num += 1

        # --- Botones Guardar/Cancelar ---
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=row_num, column=0, columnspan=2, pady=(15, 0))
        button_frame.grid_columnconfigure((0, 1), weight=1)

        save_button = ctk.CTkButton(button_frame, text="Guardar Cambios", width=140,
                                    command=lambda: self._save_edited_transaction(dialog, transaction.id, type_combo, quantity_entry,
                                                                                  price_entry, date_entry, fees_entry, notes_entry))
        save_button.grid(row=0, column=0, padx=10)

        cancel_button = ctk.CTkButton(button_frame, text="Cancelar", width=100, fg_color="gray", command=dialog.destroy)
        cancel_button.grid(row=0, column=1, padx=10)

        quantity_entry.focus() # Poner foco en el primer campo editable

    # --- Lógica para guardar los cambios de una transacción editada (con corrección de tipo) ---
    def _save_edited_transaction(self, dialog, transaction_id, type_combo, quantity_entry,
                                 price_entry, date_entry, fees_entry, notes_entry):
        logging.info(f"--- Iniciando _save_edited_transaction para ID: {transaction_id} ---")

        # --- Obtener Datos Editados ---
        tx_type_str = type_combo.get() # <-- Obtendrá "Compra" o "Venta"
        quantity_str = quantity_entry.get().strip().replace(',', '.')
        price_str = price_entry.get().strip().replace(',', '.')
        date_str = date_entry.get().strip()
        fees_str = fees_entry.get().strip().replace(',', '.')
        notes = notes_entry.get().strip()
        logging.info(f"Datos editados obtenidos: T={tx_type_str}, Q={quantity_str}, P={price_str}, D={date_str}, F={fees_str}")

        # --- Validación (similar a añadir, pero sin validar símbolo/activo) ---
        if not all([tx_type_str, quantity_str, price_str, date_str, fees_str]):
            logging.warning("Validación fallida (edit): Campos obligatorios.")
            CTkMessagebox(title="Error de Validación", message="Todos los campos excepto Notas son obligatorios.", icon="warning")
            return

        # Tipo (Validar contra "Compra" y "Venta")
        try:
            if tx_type_str == "Compra": tx_type_enum = models.TransactionType.BUY
            elif tx_type_str == "Venta": tx_type_enum = models.TransactionType.SELL
            else: raise ValueError("Tipo de transacción inválido.")
        except ValueError as e:
             logging.warning(f"Validación fallida (edit): Tipo - {e}")
             CTkMessagebox(title="Error de Validación", message=str(e), icon="warning")
             return

        # Cantidad
        try:
            quantity_dec = Decimal(quantity_str)
            if quantity_dec <= crud.ZERO_TOLERANCE: raise ValueError("La cantidad debe ser mayor que cero.")
        except InvalidOperation:
            logging.warning("Validación fallida (edit): Cantidad - InvalidOperation")
            CTkMessagebox(title="Error de Validación", message="Valor inválido para Cantidad.", icon="warning")
            return
        except ValueError as e:
            logging.warning(f"Validación fallida (edit): Cantidad - {e}")
            CTkMessagebox(title="Error de Validación", message=str(e), icon="warning")
            return

        # Precio
        try:
            price_dec = Decimal(price_str)
            if price_dec < 0: raise ValueError("El precio no puede ser negativo.")
        except InvalidOperation:
            logging.warning("Validación fallida (edit): Precio - InvalidOperation")
            CTkMessagebox(title="Error de Validación", message="Valor inválido para Precio Unitario.", icon="warning")
            return
        except ValueError as e:
            logging.warning(f"Validación fallida (edit): Precio - {e}")
            CTkMessagebox(title="Error de Validación", message=str(e), icon="warning")
            return

        # Comisión
        try:
            fees_dec = Decimal(fees_str)
            if fees_dec < 0: raise ValueError("La comisión no puede ser negativa.")
        except InvalidOperation:
            logging.warning("Validación fallida (edit): Comisión - InvalidOperation")
            CTkMessagebox(title="Error de Validación", message="Valor inválido para Comisión.", icon="warning")
            return
        except ValueError as e:
            logging.warning(f"Validación fallida (edit): Comisión - {e}")
            CTkMessagebox(title="Error de Validación", message=str(e), icon="warning")
            return

        # Fecha
        date_obj = None
        supported_formats = ['%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
        for fmt in supported_formats:
            try: date_obj = datetime.strptime(date_str, fmt); break
            except ValueError: continue
        if date_obj is None:
            logging.warning("Validación fallida (edit): Fecha - Formato inválido")
            CTkMessagebox(title="Error de Validación", message=f"Formato de fecha inválido. Usa YYYY-MM-DD HH:MM o YYYY-MM-DD.", icon="warning")
            return

        logging.info(f"Datos editados validados: T={tx_type_enum}, Q={quantity_dec}, P={price_dec}, D={date_obj}, F={fees_dec}")

        # --- Preparar Diccionario de Actualizaciones ---
        updates = {
            "transaction_type": tx_type_enum,
            "quantity": quantity_dec,
            "price_per_unit": price_dec,
            "transaction_date": date_obj,
            "fees": fees_dec,
            "notes": notes if notes else None
        }

        # --- Actualizar Transacción en la Base de Datos ---
        try:
            logging.info(f"--- Llamando a crud.update_transaction para ID: {transaction_id} ---")
            updated_transaction = crud.update_transaction(
                db=self.db,
                transaction_id=transaction_id,
                owner_id=self.current_user.id,
                updates=updates
            )

            if updated_transaction:
                 logging.info(f"--- crud.update_transaction retornó éxito para ID {transaction_id} ---")
                 CTkMessagebox(title="Éxito", message="Transacción actualizada correctamente.", icon="check")
                 dialog.destroy()
                 self.update_transactions_frame()
                 self.update_portfolio_frame()
            else:
                 # Esto podría ocurrir si update_transaction retorna None (ej. no encontrada, aunque ya la buscamos antes)
                 logging.error(f"--- crud.update_transaction retornó None/Falsy para ID {transaction_id} ---")
                 CTkMessagebox(title="Error", message="No se pudo actualizar la transacción (posiblemente no encontrada).", icon="cancel")

        except ValueError as ve: # Errores de validación desde CRUD (menos probable aquí)
            logging.error(f"Error de valor al actualizar transacción ID {transaction_id}: {ve}")
            CTkMessagebox(title="Error al Guardar", message=f"Error: {ve}", icon="cancel")
        except Exception as e: # Otros errores inesperados (ej. DB)
            logging.error(f"Error inesperado al actualizar transacción ID {transaction_id}: {e}", exc_info=True)
            CTkMessagebox(title="Error Inesperado", message=f"Ocurrió un error inesperado al guardar los cambios:\n{e}", icon="cancel")
        logging.info(f"--- Fin _save_edited_transaction para ID: {transaction_id} ---")


    def delete_transaction_confirm(self):
        # Pide confirmación y elimina la transacción seleccionada
        if not self.current_user or self.selected_transaction_id is None:
            CTkMessagebox(title="Aviso", message="Por favor, selecciona una transacción de la tabla para eliminar.", icon="warning")
            return

        # Mostrar diálogo de confirmación
        confirm = CTkMessagebox(title="Confirmar Eliminación",
                                message=f"¿Estás seguro de que quieres eliminar la transacción con ID {self.selected_transaction_id}?\nEsta acción no se puede deshacer.",
                                icon="warning", option_1="Cancelar", option_2="Eliminar")

        if confirm.get() == "Eliminar":
            try:
                logging.info(f"Intentando eliminar transacción ID: {self.selected_transaction_id}")
                # ### CORRECCIÓN AQUÍ ###: Cambiar user_id por owner_id
                success = crud.delete_transaction(self.db, transaction_id=self.selected_transaction_id, owner_id=self.current_user.id)

                if success:
                    logging.info(f"Transacción ID: {self.selected_transaction_id} eliminada.")
                    CTkMessagebox(title="Éxito", message="Transacción eliminada correctamente.", icon="check")
                    # Resetear selección y actualizar vistas
                    self.selected_transaction_id = None
                    # Asegurarse que los botones existen antes de configurarlos
                    if hasattr(self, 'edit_transaction_button'): self.edit_transaction_button.configure(state="disabled")
                    if hasattr(self, 'delete_transaction_button'): self.delete_transaction_button.configure(state="disabled")
                    self.update_transactions_frame()
                    self.update_portfolio_frame()
                else:
                    # Si delete_transaction retorna False (no encontrada o sin permiso)
                    logging.warning(f"No se pudo eliminar transacción ID: {self.selected_transaction_id}. No encontrada o sin permiso.")
                    CTkMessagebox(title="Error", message="No se pudo eliminar la transacción. Puede que ya no exista o no tengas permiso.", icon="cancel")
                    # Actualizar la tabla por si acaso el estado cambió
                    self.update_transactions_frame()
            except Exception as e:
                # Error inesperado durante la eliminación
                logging.error(f"Error al eliminar transacción ID {self.selected_transaction_id}: {e}", exc_info=True)
                CTkMessagebox(title="Error", message=f"Ocurrió un error al intentar eliminar la transacción:\n{e}", icon="cancel")


    # --- Métodos de Configuración y Lógica de Login ---
    def _setup_login_frame(self):
        # Configura los widgets dentro del frame de login
        self._clear_login_frame() # Limpiar frame por si se llama más de una vez

        login_container = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        # Centrar el contenedor dentro del frame principal de login
        login_container.grid(row=0, column=0, padx=30, pady=30, sticky="")
        self.login_frame.grid_rowconfigure(0, weight=1)
        self.login_frame.grid_columnconfigure(0, weight=1)

        login_label = ctk.CTkLabel(login_container, text="Iniciar Sesión", font=ctk.CTkFont(size=20, weight="bold"))
        login_label.grid(row=0, column=0, padx=10, pady=(0, 15))

        username_entry = ctk.CTkEntry(login_container, placeholder_text="Nombre de usuario", width=250)
        username_entry.grid(row=1, column=0, padx=10, pady=10)

        password_entry = ctk.CTkEntry(login_container, placeholder_text="Contraseña", show="*", width=250)
        password_entry.grid(row=2, column=0, padx=10, pady=10)

        # Función callback para el botón y la tecla Enter
        def attempt_login_callback(event=None): # Aceptar argumento 'event' opcional para el bind
            self._attempt_login(username_entry, password_entry)

        login_button = ctk.CTkButton(login_container, text="Login", command=attempt_login_callback, width=250)
        login_button.grid(row=3, column=0, padx=10, pady=(20, 10))

        # Vincular tecla Enter en los campos de entrada al login
        username_entry.bind("<Return>", attempt_login_callback)
        password_entry.bind("<Return>", attempt_login_callback)

        # Botón informativo para registro (funcionalidad no implementada en GUI)
        def show_register_info():
            CTkMessagebox(title="Registro", message="La función de registro aún no está implementada en la GUI.\nPor favor, usa la versión de consola o script para registrar nuevos usuarios.", icon="info")

        register_button = ctk.CTkButton(login_container, text="Registrar (Info)", command=show_register_info, width=150, fg_color="gray")
        register_button.grid(row=4, column=0, padx=10, pady=10)

        username_entry.focus() # Poner foco en el campo de usuario

    def _clear_login_frame(self):
         # Limpia específicamente el frame de login
         self._clear_frame_widgets(self.login_frame)

    def _attempt_login(self, username_entry, password_entry):
        # Intenta loguear al usuario con los datos introducidos
        username = username_entry.get().strip()
        password = password_entry.get() # No quitar espacios de la contraseña

        if not username or not password:
            CTkMessagebox(title="Error de Validación", message="El nombre de usuario y la contraseña no pueden estar vacíos.", icon="warning")
            return

        user = crud.get_user_by_username(self.db, username=username)
        login_ok = False

        if user:
            try:
                # Verificar contraseña usando passlib
                login_ok = crud.verify_password(password, user.hashed_password)
            except AttributeError as ae:
                 # Manejo específico para un error conocido de bcrypt/passlib a veces
                 if "'bcrypt' has no attribute '__about__'" in str(ae):
                     logging.warning("Error conocido de atributo en bcrypt detectado. Reintentando verificación...")
                     try:
                         # Reintentar la verificación puede funcionar a veces
                         login_ok = crud.verify_password(password, user.hashed_password)
                     except Exception as verify_e:
                         logging.error(f"Error en el reintento de verificación de contraseña: {verify_e}", exc_info=True)
                         login_ok = False
                 else:
                     # Otro AttributeError inesperado
                     logging.error(f"AttributeError inesperado durante la verificación de contraseña: {ae}", exc_info=True)
                     login_ok = False
                     CTkMessagebox(title="Error Interno", message="Ocurrió un error interno al verificar la contraseña.", icon="cancel")
            except Exception as e:
                # Otros errores durante la verificación
                logging.error(f"Error inesperado durante verify_password: {e}", exc_info=True)
                login_ok = False
                CTkMessagebox(title="Error Interno", message="Ocurrió un error inesperado durante el proceso de login.", icon="cancel")

        if login_ok:
            # --- Login Exitoso ---
            self.current_user = user
            self.login_logout_button.configure(text="Logout")
            self.portfolio_button.configure(state="normal")
            self.transactions_button.configure(state="normal")
            self.title(f"Portfolio Tracker Pro - {user.username}") # Actualizar título ventana
            self.select_frame_by_name("portfolio") # Ir al portafolio por defecto
            self.update_portfolio_frame() # Cargar datos del portafolio
            logging.info(f"Usuario '{user.username}' inició sesión.")
            # Limpiar campos de login (opcional)
            username_entry.delete(0, "end")
            password_entry.delete(0, "end")
            self.portfolio_button.focus() # Mover foco a un botón de navegación
        else:
            # --- Login Fallido ---
            logging.warning(f"Intento de login fallido para usuario '{username}'.")
            if user: # Si el usuario existe pero la contraseña es incorrecta
                CTkMessagebox(title="Error de Login", message="Nombre de usuario o contraseña incorrectos.", icon="cancel")
            elif not user and username: # Si el usuario no existe
                CTkMessagebox(title="Error de Login", message=f"El usuario '{username}' no existe.", icon="cancel")
            # Limpiar solo contraseña y mantener foco en usuario
            password_entry.delete(0, "end")
            username_entry.focus()


# --- Punto de Entrada para la GUI ---
def run_gui():
    db_session = SessionLocal() # Crear una sesión de BD al inicio
    app = None # Referencia a la aplicación
    try:
        # Crear e iniciar la aplicación principal
        app = PortfolioApp(db_session)
        app._setup_login_frame() # Configurar la pantalla de login inicial
        app.mainloop() # Iniciar el bucle principal de la GUI

    except Exception as e:
        # --- Manejo de Errores Fatales ---
        logging.critical("Error fatal durante la ejecución de la GUI", exc_info=True)
        try:
            # Intentar mostrar un mensaje de error gráfico si tkinter aún funciona
            root_error = ctk.CTk()
            root_error.withdraw() # Ocultar la ventana raíz vacía
            CTkMessagebox(title="Error Fatal",
                          message=f"Error crítico irrecuperable:\n{e}\n\nLa aplicación se cerrará.",
                          icon="cancel")
            root_error.destroy()
        except Exception as mb_error:
            # Si ni siquiera se puede mostrar el messagebox, imprimir en consola
            print(f"[CRITICAL] No se pudo mostrar el messagebox de error fatal: {mb_error}")
            print(f"[CRITICAL] Error fatal original: {e}")

        # Intentar cerrar la sesión de BD en caso de excepción ANTES de salir
        if db_session:
            try:
                print("[*] Cerrando sesión BD (debido a excepción)...")
                db_session.close()
            except Exception as db_close_err:
                logging.error(f"Error al cerrar sesión BD tras excepción: {db_close_err}")

        sys.exit(1) # Salir de la aplicación con un código de error

    finally:
        # --- Limpieza Final (se ejecuta si no hubo sys.exit antes) ---
        # Este bloque se ejecuta cuando mainloop termina normally (cerrando la ventana)
        db_closed = False
        # Intentar cerrar la sesión a través del objeto app si existe y tiene la sesión
        if app and hasattr(app, 'db') and app.db:
            try:
                # Verificar si la sesión es la misma que la inicial (por si acaso)
                if app.db is db_session:
                    print("[*] Cerrando sesión BD (cierre normal de GUI)...")
                    app.db.close()
                    db_closed = True
                else:
                    # Caso raro: la sesión en app no es la que se creó aquí
                    logging.warning("La sesión de BD en la app no coincide con la sesión inicial.")
                    # Intentar cerrar ambas por si acaso? Podría ser arriesgado.
                    # Por ahora, solo cerramos la de la app si existe.
                    try:
                        print("[*] Cerrando sesión BD (app.db)...")
                        app.db.close()
                    except Exception as app_db_err:
                         logging.error(f"Error al cerrar app.db: {app_db_err}")
                    # Intentar cerrar la sesión original también si no se marcó como cerrada
                    if not db_closed and db_session:
                         try:
                             print("[*] Cerrando sesión BD (original - fallback)...")
                             db_session.close()
                             db_closed = True
                         except Exception as db_close_fall_err:
                             logging.error(f"Error cierre BD (fallback en finally): {db_close_fall_err}")

            except Exception as db_close_norm_err:
                logging.error(f"Error al cerrar sesión BD (cierre normal): {db_close_norm_err}")
                db_closed = False # Marcar como no cerrada si hubo error

        # Si por alguna razón la sesión no se cerró a través de 'app' y la sesión original existe
        if not db_closed and db_session:
            try:
                # Podríamos añadir una comprobación aquí para ver si la sesión ya está inactiva
                # pero un simple intento de cierre es común.
                print("[*] Cerrando sesión BD (fallback final)...")
                db_session.close()
            except Exception as db_close_fall_err:
                # Puede dar error si ya estaba cerrada, lo cual es aceptable aquí.
                logging.warning(f"Error cierre BD (fallback final) - puede ser normal si ya estaba cerrada: {db_close_fall_err}")
        print("[*] Aplicación GUI finalizada.")