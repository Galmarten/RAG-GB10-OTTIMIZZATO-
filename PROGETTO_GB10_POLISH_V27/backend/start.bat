@echo off
setlocal enabledelayedexpansion

REM Script di avvio UNIVPM RAG con Gunicorn
REM Uso: start.bat [dev|prod]

set MODE=%1
if "%MODE%"=="" set MODE=prod

set PORT=8000

echo.
echo ===============================================================
echo   UNIVPM RAG - Backend Server
echo ===============================================================
echo.

REM Verifica che Python sia disponibile
python --version >nul 2>&1
if errorlevel 1 (
    echo Errore: Python non trovato
    exit /b 1
)

REM Installa le dipendenze
echo [1/3] Installazione dipendenze...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Errore durante l'installazione delle dipendenze
    exit /b 1
)

REM Crea le directory necessarie
echo [2/3] Preparazione directory...
if not exist "data\docs" mkdir data\docs
if not exist "data\index" mkdir data\index
if not exist "data\config" mkdir data\config

REM Avvia il server
echo [3/3] Avvio server...
echo.

if "%MODE%"=="dev" (
    echo Modalita: SVILUPPO (con auto-reload)
    echo.
    echo UNIVPM RAG ^-> http://127.0.0.1:%PORT%/ (Maintenance: /admin)
    echo.
    python -m uvicorn app:app --host 0.0.0.0 --port %PORT% --reload
) else (
    echo Modalita: PRODUZIONE (Gunicorn multi-worker)
    echo.
    echo UNIVPM RAG ^-> http://127.0.0.1:%PORT%/ (Maintenance: /admin)
    echo.
    python -m gunicorn app:app --config gunicorn_conf.py
)

endlocal
