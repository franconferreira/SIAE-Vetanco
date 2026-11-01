# SIAE-Vetanco — Script de Arranque PowerShell
$Host.UI.RawUI.WindowTitle = "SIAE-Vetanco — Lanzador PowerShell"
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "         SIAE-Vetanco: Sistema de Facturas para SAP S/4HANA" -ForegroundColor Yellow
Write-Host "      Dirección de Proyectos Informáticos — UADE (Grupo 8)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$BaseDir = $PSScriptRoot
Set-Location $BaseDir

$BackendDir = Join-Path $BaseDir "backend"
$FrontendDir = Join-Path $BaseDir "frontend"
$EnvFile = Join-Path $BackendDir ".env"
$EnvExample = Join-Path $BackendDir ".env.example"

# 0. Archivo .env
if (-not (Test-Path $EnvFile) -and (Test-Path $EnvExample)) {
    Write-Host "[*] Creando backend\.env a partir de .env.example..." -ForegroundColor Green
    Copy-Item $EnvExample $EnvFile
}

# 1. Backend venv
Write-Host "`n[*] Verificando Backend Python..." -ForegroundColor Green
$VenvPython = Join-Path $BackendDir "venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[!] Creando venv e instalando dependencias Python..." -ForegroundColor Yellow
    Set-Location $BackendDir
    python -m venv venv
    .\venv\Scripts\pip install -r requirements.txt
    Set-Location $BaseDir
}

$DbPath = Join-Path $BackendDir "data\siae_staging.db"
if (-not (Test-Path $DbPath)) {
    Write-Host "[*] Inicializando base de datos y 6 facturas demo de prueba..." -ForegroundColor Yellow
    Start-Process -FilePath $VenvPython -ArgumentList "scripts\seed_demo.py" -WorkingDirectory $BackendDir -Wait
}

# 2. Frontend node_modules
Write-Host "`n[*] Verificando dependencias de Frontend..." -ForegroundColor Green
$NodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $NodeModules)) {
    Write-Host "[!] Ejecutando npm install por primera vez..." -ForegroundColor Yellow
    Set-Location $FrontendDir
    npm install
    Set-Location $BaseDir
}

# 3. Iniciar Backend
Write-Host "[*] Iniciando Backend FastAPI en http://127.0.0.1:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$BackendDir'; .\venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

Start-Sleep -Seconds 3

# 4. Iniciar Frontend
Write-Host "[*] Iniciando Frontend React en http://localhost:5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$FrontendDir'; npm run dev"

Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"

Write-Host "`n[OK] SIAE-Vetanco iniciado correctamente." -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "API Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
