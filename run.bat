@echo off
echo ========================================
echo   Smart Garden Dashboard
echo ========================================
echo.

:: Check if venv exists
if not exist "venv" (
    echo Virtual environment not found!
    echo Please run install.bat first.
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Check LMStudio status
echo Checking LMStudio connection...
curl -s -o nul -w "%%{http_code}" http://localhost:1234/v1/models >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: LMStudio doesn't appear to be running!
    echo The AI features will not work without it.
    echo.
    echo To enable AI features:
    echo   1. Open LMStudio
    echo   2. Load a model ^(e.g., granite-3.3-8b-instruct^)
    echo   3. Start the local server on port 1234
    echo.
)

echo.
echo Starting Smart Garden Dashboard...
echo.
echo Dashboard will be available at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server.
echo.

:: Run the Flask application
cd backend
python main.py
cd ..

pause
