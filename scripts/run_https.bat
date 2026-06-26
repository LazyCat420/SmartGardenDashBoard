@echo off
echo Starting Smart Garden Dashboard with HTTPS...
cd /d "%~dp0"
call venv\Scripts\activate.bat
cd backend
python main_md.py --https --port 5000
pause
