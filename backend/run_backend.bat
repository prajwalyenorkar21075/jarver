@echo off
setlocal
title JARVIS Backend Server
set "BACKEND_DIR=%~dp0"
set "PYTHON_EXE=%BACKEND_DIR%.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python.exe"
)

set "PYTHONPATH=%BACKEND_DIR%"
echo ========================================================
echo   J.A.R.V.I.S. BACKEND DAEMON (PORT 8000)
echo   Python: %PYTHON_EXE%
echo   App Dir: %BACKEND_DIR%
echo ========================================================
"%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir "%BACKEND_DIR%" %*
endlocal
