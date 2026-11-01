"""
Lanzador Maestro Silencioso - SIAE-Vetanco
Inicia Backend (puerto 8000) y Frontend Vite (puerto 5173) en segundo plano
SIN ninguna ventana de consola visible (CREATE_NO_WINDOW).
Espera a que ambos puertos estén activos antes de abrir http://localhost:5173.
Cuando el usuario cierra la pestaña o navegador, el sistema se cierra automáticamente.
"""
import os
import sys
import subprocess
import time
import urllib.request
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
VENV_PYTHONW = BACKEND_DIR / "venv" / "Scripts" / "pythonw.exe"
DB_PATH = BACKEND_DIR / "data" / "siae_staging.db"

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

def matar_puerto(port: int):
    """Mata cualquier proceso colgado en el puerto indicado."""
    if os.name == "nt":
        cmd = f'for /f "tokens=5" %a in (\'netstat -aon ^| findstr :{port}\') do taskkill /f /pid %a'
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def esperar_url(url: str, max_segundos: float = 20.0) -> bool:
    """Espera activamente a que una URL responda 200 antes de proceder."""
    inicio = time.time()
    while time.time() - inicio < max_segundos:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SIAE-Launcher"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status in (200, 304):
                    return True
        except Exception:
            pass
        time.sleep(0.4)
    return False

def main():
    # 0. Limpiar puertos previos si quedaron residuos
    matar_puerto(8000)
    matar_puerto(5173)

    # 1. Verificar base de datos inicializada
    if not DB_PATH.exists():
        try:
            subprocess.run(
                [str(VENV_PYTHON), "scripts/seed_demo.py"],
                cwd=str(BACKEND_DIR),
                creationflags=CREATE_NO_WINDOW,
                check=True
            )
        except Exception:
            pass

    # 2. Iniciar Backend FastAPI en puerto 8000 (sin ventana)
    py_exec = str(VENV_PYTHONW if VENV_PYTHONW.exists() else VENV_PYTHON)
    backend_proc = subprocess.Popen(
        [py_exec, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW
    )

    # 3. Iniciar Frontend Vite en puerto 5173 (sin ventana)
    vite_bin = FRONTEND_DIR / "node_modules" / ".bin" / "vite.cmd"
    if vite_bin.exists():
        vite_cmd = [str(vite_bin), "--port", "5173"]
    else:
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        vite_cmd = [npx_cmd, "vite", "--port", "5173"]

    frontend_proc = subprocess.Popen(
        vite_cmd,
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW
    )

    # 4. Esperar a que AMBOS servicios estén listos y respondiendo HTTP 200
    backend_ok = esperar_url("http://127.0.0.1:8000/api/dashboard/resumen", max_segundos=25)
    frontend_ok = esperar_url("http://localhost:5173/", max_segundos=25)

    if frontend_ok and backend_ok:
        # Abrir el navegador en el puerto conocido (5173) solo cuando ya está 100% listo
        webbrowser.open("http://localhost:5173")
    elif backend_ok:
        webbrowser.open("http://localhost:8000")

    # 5. Monitorear procesos en segundo plano
    # Si el backend se apaga (por el watchdog al cerrar la pestaña o por /api/system/shutdown),
    # matar el frontend y salir.
    try:
        backend_proc.wait()
    except Exception:
        pass
    finally:
        # Cerrar frontend y liberar puertos
        if frontend_proc.poll() is None:
            frontend_proc.terminate()
            try:
                frontend_proc.wait(timeout=3)
            except Exception:
                frontend_proc.kill()
        matar_puerto(5173)
        matar_puerto(8000)

if __name__ == "__main__":
    main()
