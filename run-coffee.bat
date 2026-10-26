@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing. Follow README.md setup first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m scripts.run --coffee %*
if errorlevel 1 pause
