@echo off
setlocal

echo [WorldPulse Trade] Installing Python dependencies...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [WorldPulse Trade] Installing frontend dependencies...
cd frontend
npm install
cd ..

echo.
echo Install completed.
echo Run start.bat to launch the backend and frontend.
endlocal
