# run_tracker.py
import sys
import os
import logging # Importar logging aquí también por si acaso

# Configuración básica de logging (opcional pero útil para depurar el exe)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Iniciando Portfolio Tracker desde run_tracker.py...")

try:
    # Importa la función principal desde tu paquete src
    # Usa una importación absoluta
    from src.gui import run_gui

    # Llama a la función principal
    if __name__ == "__main__":
        logging.info("Llamando a run_gui()...")
        run_gui()
        logging.info("run_gui() finalizado.")

except ImportError as e:
    logging.critical(f"Error de importación: {e}. Asegúrate de que el paquete 'src' esté accesible.", exc_info=True)
    # Podrías mostrar un messagebox aquí si tkinter/customtkinter ya estuviera disponible
    # pero es más seguro loguear y salir si la importación principal falla.
    sys.exit(f"Error crítico de importación: {e}")
except Exception as e:
    logging.critical(f"Error inesperado al iniciar la aplicación: {e}", exc_info=True)
    sys.exit(f"Error crítico inesperado: {e}")

logging.info("run_tracker.py finalizado.")