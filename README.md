# Portfolio Tracker Pro

## Descripción

Una aplicación de escritorio desarrollada en Python para la gestión y el seguimiento del rendimiento de portafolios de inversión personales. Permite a los usuarios registrar transacciones, ver el estado actual de sus activos y analizar el rendimiento general.

## Funcionalidades Clave

*   **Autenticación Segura:** Sistema de registro y login de usuarios con hashing de contraseñas (bcrypt mediante `passlib`).
*   **Gestión Completa de Transacciones:** Añadir, editar y eliminar transacciones de compra/venta con validaciones robustas de datos (tipos, formatos numéricos `Decimal`, fechas).
*   **Resumen de Portafolio Automatizado:**
    *   Calcula y muestra la cantidad actual de cada activo.
    *   Determina el coste medio ponderado (lógica FIFO implícita).
    *   Calcula el coste total base.
    *   Obtiene el valor de mercado actual utilizando datos en tiempo real de `yfinance`.
    *   Presenta el Profit & Loss (P&L) no realizado (absoluto y porcentual).
*   **Persistencia de Datos:** Almacenamiento fiable de la información en una base de datos SQLite.
*   **Interfaz Gráfica Moderna:** GUI intuitiva y atractiva creada con `CustomTkinter`.

## Arquitectura y Tecnologías

*   **Lenguaje:** Python 3
*   **Interfaz Gráfica (GUI):** `CustomTkinter`
*   **Base de Datos:** SQLite
*   **ORM (Object-Relational Mapper):** `SQLAlchemy` (para interacción con la BD)
*   **Migraciones de Base de Datos:** `Alembic` (para versionar cambios en el esquema)
*   **API de Datos Financieros:** `yfinance` (para obtener precios de activos)
*   **Seguridad:** `passlib` (para hashing de contraseñas)
*   **Empaquetado:** `PyInstaller` (para crear ejecutable `.exe` en Windows)
*   **Gestión de Dependencias:** `venv`, `pip`, `requirements.txt`
*   **Control de Versiones:** Git

## Instalación y Uso (Ejemplo)

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/TamaraKaren/PortfolioTracker.git
    cd PortfolioTracker
    ```
2.  **Crear y activar un entorno virtual:**
    ```bash
    python -m venv venv
    # En Windows:
    .\venv\Scripts\activate
    # En macOS/Linux:
    source venv/bin/activate
    ```
3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Ejecutar la aplicación:**
    ```bash
    python run_tracker.py
    ```
    *(Nota: Puede existir un ejecutable pre-compilado en la sección de Releases del repositorio)*

## Habilidades Demostradas y Relevancia

Este proyecto demuestra:

*   Sólidas habilidades de desarrollo en **Python**.
*   Experiencia en la creación de **interfaces gráficas de usuario (GUI)**.
*   Competencia en el diseño, implementación y gestión de **bases de datos relacionales (SQLite)** utilizando un **ORM (SQLAlchemy)** y gestionando **migraciones (Alembic)**.
*   Capacidad para **integrar APIs externas (`yfinance`)** para obtener datos en tiempo real.
*   Implementación de **lógica de negocio compleja** (cálculos financieros como FIFO, P&L).
*   Aplicación de **buenas prácticas de desarrollo**: entornos virtuales, gestión de dependencias, control de versiones (Git) y empaquetado para distribución (`PyInstaller`).
*   Conocimientos básicos de **seguridad** (hashing de contraseñas).

# Portfolio Tracker Pro

## Description

A desktop application developed in Python designed for managing and tracking the performance of personal investment portfolios. It allows users to log transactions, view the current status of their assets, and analyze overall performance.

## Key Features

*   **Secure Authentication:** User registration and login system with password hashing (bcrypt via `passlib`).
*   **Comprehensive Transaction Management:** Add, edit, and delete buy/sell transactions with robust data validation (types, `Decimal` numeric formats, dates).
*   **Automated Portfolio Summary:**
    *   Calculates and displays the current quantity of each asset.
    *   Determines the weighted average cost (implicit FIFO logic).
    *   Calculates the total cost basis.
    *   Fetches the current market value using real-time data from `yfinance`.
    *   Presents unrealized Profit & Loss (P&L) in both absolute and percentage terms.
*   **Data Persistence:** Reliable storage of information in an SQLite database.
*   **Modern Graphical User Interface (GUI):** Intuitive and attractive GUI built with `CustomTkinter`.

## Architecture and Technologies

*   **Language:** Python 3
*   **Graphical User Interface (GUI):** `CustomTkinter`
*   **Database:** SQLite
*   **ORM (Object-Relational Mapper):** `SQLAlchemy` (for DB interaction)
*   **Database Migrations:** `Alembic` (for versioning schema changes)
*   **Financial Data API:** `yfinance` (for fetching asset prices)
*   **Security:** `passlib` (for password hashing)
*   **Packaging:** `PyInstaller` (for creating a standalone `.exe` on Windows)
*   **Dependency Management:** `venv`, `pip`, `requirements.txt`
*   **Version Control:** Git

## Installation and Usage (Example)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/TamaraKaren/PortfolioTracker.git
    cd PortfolioTracker
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the application:**
    ```bash
    python run_tracker.py
    ```
    *(Note: A pre-compiled executable might be available in the repository's Releases section)*

## Demonstrated Skills and Relevance

This project demonstrates:

*   Solid **Python** development skills.
*   Experience in creating **Graphical User Interfaces (GUI)**.
*   Proficiency in designing, implementing, and managing **relational databases (SQLite)** using an **ORM (SQLAlchemy)** and handling **migrations (Alembic)**.
*   Ability to **integrate external APIs (`yfinance`)** to fetch real-time data.
*   Implementation of **complex business logic** (financial calculations like FIFO, P&L).
*   Application of **development best practices**: virtual environments, dependency management, version control (Git), and packaging for distribution (`PyInstaller`).
*   Basic **security** knowledge (password hashing).
