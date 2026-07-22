@echo off
echo Starting Shankar Card frontend on http://localhost:5173
cd /d "%~dp0frontend"
if not exist "node_modules" (
  echo Installing frontend dependencies...
  call npm install
)
npm run dev
