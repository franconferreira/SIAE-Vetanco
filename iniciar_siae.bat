@echo off
setlocal
title SIAE-Vetanco - Lanzador Silencioso

set BASE_DIR=%~dp0
cd /d "%BASE_DIR%"

:: 1. Si no existe el archivo .env en backend, crearlo a partir del ejemplo
if not exist "backend\.env" (
    echo [*] Configurando variables de entorno iniciales...
    copy "backend\.env.example" "backend\.env" >nul
)

:: 2. Si no existe el venv, crearlo e instalar dependencias Python
if not exist "backend\venv\Scripts\python.exe" (
    echo [*] Configurando entorno virtual de Python por primera vez...
    cd backend
    python -m venv venv
    call venv\Scripts\pip install -r requirements.txt
    cd /d "%BASE_DIR%"
)

:: 3. Si no existen las dependencias de node_modules en el frontend, instalarlas
if not exist "frontend\node_modules" (
    echo [*] Instalando dependencias del Frontend (npm install)...
    cd frontend
    call npm install
    cd /d "%BASE_DIR%"
)

:: 4. Si el frontend no tiene dist compilado, compilarlo
if not exist "frontend\dist\index.html" (
    echo [*] Compilando frontend para modo silencioso...
    cd frontend
    call npm run build
    cd /d "%BASE_DIR%"
)

:: 5. Lanzar silenciosamente a traves de VBScript sin consolas visibles
wscript.exe "Iniciar SIAE.vbs"

exit
