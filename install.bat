@echo off
echo ========================================
echo   Smart Garden Dashboard - Installer
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/4] Python found!
python --version
echo.

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [2/4] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo Virtual environment created!
) else (
    echo [2/4] Virtual environment already exists.
)
echo.

:: Activate virtual environment and install dependencies
echo [3/4] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)
echo Dependencies installed!
echo.

:: Initialize database
echo [4/4] Initializing database...
cd backend
python -c "from main import init_db; init_db()"
cd ..
echo Database initialized!
echo.

echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo To run the application:
echo   1. Make sure LMStudio is running on localhost:1234
echo   2. Run 'run.bat' or double-click it
echo.
echo LMStudio Setup:
echo   - Download from https://lmstudio.ai/
echo   - Load a model like granite-3.3-8b-instruct
echo   - Start the local server on port 1234
echo.
pause
