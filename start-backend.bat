@echo off
echo Starting Shankar Card backend on http://127.0.0.1:8000
cd /d "%~dp0backend"
if not exist ".venv\Scripts\activate.bat" (
  echo ERROR: backend\.venv not found. Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
  exit /b 1
)
call .venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
