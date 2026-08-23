@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11+ from https://www.python.org/downloads/
  echo Check "Add python.exe to PATH" during setup, then run this again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Failed to create .venv
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install packages. On Windows you may also need the VC++ runtime:
  echo https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
  pause
  exit /b 1
)

if not exist "config.yaml" (
  copy "config.example.yaml" "config.yaml" >nul
)

chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONPATH=%~dp0src
echo.
echo Saltvoice Local is starting. Offline Whisper — no API key.
echo Look for a window titled Saltvoice Local at the TOP of the screen.
echo Start: Salt open voice over
echo Stop:  Salt stop voice over
echo First run downloads the Whisper model, then it stays on this PC.
echo Keep this window open.
echo.
python -m saltvoice_local %*
if errorlevel 1 pause
