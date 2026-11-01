@echo off
setlocal
title SIAE-Vetanco - Lanzador Silencioso

set BASE_DIR=%~dp0
cd /d "%BASE_DIR%"

:: Si no existe el venv, crearlo (solo la primera vez)
if not exist "backend\venv\Scripts\python.exe" (
    echo [*] Configurando entorno virtual por primera vez...
    cd backend
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
    cd /d "%BASE_DIR%"
)

:: Si el frontend no tiene dist compilado, compilarlo
if not exist "frontend\dist\index.html" (
    echo [*] Compilando frontend para modo silencioso...
    cd frontend
    call npm run build
    cd /d "%BASE_DIR%"
)

:: Lanzar silenciosamente a traves de VBScript sin consolas visibles
wscript.exe "Iniciar SIAE.vbs"

exit
