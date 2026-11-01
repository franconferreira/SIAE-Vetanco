import subprocess
import time
import urllib.request
import json
import sys

print("[*] Iniciando servidor silencioso con venv python.exe...")
proc = subprocess.Popen(
    [r".\venv\Scripts\python.exe", "run_silent.py"],
    cwd=r"F:\Escritorio\UADE\2026\Segundo_Cuatrimestre\Direccion de proyectos informaticos\TPO\siae-vetanco\backend",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

try:
    print(f"[*] Servidor iniciado (PID: {proc.pid}). Esperando a que el puerto 8000 responda...")
    conectado = False
    for i in range(20):
        time.sleep(0.5)
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    print(f"[OK] Servidor activo tras {(i+1)*0.5:.1f}s | HTML: {len(resp.read())} bytes")
                    conectado = True
                    break
        except Exception:
            pass

    if not conectado:
        raise Exception("El servidor no respondió en el puerto 8000 tras 10 segundos.")

    # 1. Probar heartbeat
    req_hb = urllib.request.Request("http://127.0.0.1:8000/api/system/heartbeat", data=b"{}", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_hb, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print("[OK] POST /api/system/heartbeat ->", data)

    # 2. Probar señal de cierre
    print("[*] Simulando cierre de pestaña en el navegador (beforeunload -> /api/system/shutdown)...")
    req_sd = urllib.request.Request("http://127.0.0.1:8000/api/system/shutdown", data=b"{}", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_sd, timeout=5) as resp:
        data_sd = json.loads(resp.read().decode())
        print("[OK] POST /api/system/shutdown ->", data_sd)

    # 3. Esperar a que el proceso termine solo
    print("[*] Verificando que el proceso finalice automáticamente (gracia de 2.5s)...")
    exit_code = proc.wait(timeout=8)
    print(f"[EXITO TOTAL] El servidor se cerró solo automáticamente con código de salida: {exit_code}!")

except Exception as e:
    print("[ERROR]:", e)
    if proc.poll() is None:
        proc.kill()
    sys.exit(1)
