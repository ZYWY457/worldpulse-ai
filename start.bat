@echo off
setlocal

echo Starting WorldPulse Trade...
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment not found. Running install.bat first is recommended.
  python -m venv .venv
)

start "WorldPulse Trade Backend" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn backend.main:app --reload --port 8000"
start "WorldPulse Trade Frontend" cmd /k "cd frontend && npm run dev -- --host 0.0.0.0 --port 5173"

endlocal
