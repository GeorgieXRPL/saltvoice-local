@echo off
cd /d "%~dp0"
set SALT_WHISPER_MODEL=tiny.en
set SALT_WHISPER_DEVICE=cpu
set SALT_WHISPER_COMPUTE=int8
"C:\Users\justa\saltvoice-local\.venv\Scripts\python.exe" server.py
