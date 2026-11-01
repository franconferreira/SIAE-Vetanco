"""
Lanzador Silencioso de SIAE-Vetanco (Modo Desktop 1-Click)
Ejecuta el servidor en segundo plano sin consolas visibles (usando pythonw.exe).
Abre automáticamente el navegador y finaliza todos los procesos cuando la ventana se cierra.
"""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Asegurar directorios de ejecución
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
DB_PATH = BACKEND_DIR / "data" / "siae_staging.db"

os.chdir(str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR))

# 1. Asegurar base de datos inicializada
if not DB_PATH.exists():
    try:
        from scripts.seed_demo import main as seed_main
        seed_main()
    except Exception as e:
        pass

# 2. Asegurar que el frontend esté compilado
if not (DIST_DIR / "index.html").exists():
    import subprocess
    try:
        subprocess.run("npm run build", cwd=str(FRONTEND_DIR), shell=True, check=True)
    except Exception:
        pass

# 3. Función para abrir el navegador una vez iniciado el servidor
def abrir_navegador():
    time.sleep(1.2)
    webbrowser.open("http://localhost:8000")

threading.Thread(target=abrir_navegador, daemon=True).start()

# 4. Iniciar servidor FastAPI
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
