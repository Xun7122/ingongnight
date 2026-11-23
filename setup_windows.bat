@echo off
cd /d "%~dp0"
py -3 --version >nul 2>&1
if not errorlevel 1 (
  py -3 app.py setup
) else (
  python app.py setup
)
if errorlevel 1 echo Python 3.10+ is required. See README.md.
pause
