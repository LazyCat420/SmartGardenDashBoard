@echo off
echo ========================================
echo Smart Garden Dashboard - Setup and Run
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        echo Make sure Python is installed and in your PATH
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install/update requirements
echo.
echo Installing/updating requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

REM Initialize database
echo.
echo Initializing database...
python database.py
if errorlevel 1 (
    echo WARNING: Database initialization had issues, but continuing...
)

REM Start the Flask app
echo.
echo ========================================
echo Starting Flask Backend Server...
echo ========================================
echo.
echo The server will start on http://localhost:5000
echo.
echo To use the app:
echo 1. Keep this window open (server is running)
echo 2. Open index.html in your web browser
echo 3. Press Ctrl+C here to stop the server
echo.
echo ========================================
echo.

python app.py

REM If the app exits, pause so user can see any errors
pause
