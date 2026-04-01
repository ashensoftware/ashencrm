import subprocess
import sys
import threading
import time
from pathlib import Path

def prefix_output(stream, prefix):
    for line in iter(stream.readline, b''):
        try:
            text = line.decode('utf-8', errors='replace')
            sys.stdout.write(f"{prefix} {text}")
            sys.stdout.flush()
        except:
            pass

def run_process(cmd, cwd, show_logs=False, prefix=""):
    kwargs = {
        "cwd": cwd,
        "shell": True
    }
    
    if not show_logs:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    else:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
        
    process = subprocess.Popen(cmd, **kwargs)
    
    if show_logs and prefix:
        threading.Thread(target=prefix_output, args=(process.stdout, prefix), daemon=True).start()
        
    return process

def install_h3_if_needed(cwd):
    try:
        import h3
    except ImportError:
        print("[SISTEMA] Falta h3. Instalando libreria h3 automaticamente...")
        subprocess.run("call .venv\\Scripts\\activate.bat && pip install h3", cwd=cwd, shell=True, stdout=subprocess.DEVNULL)
        print("[SISTEMA] h3 instalado exitosamente.")

def main():
    show_both = "--logs" in sys.argv
    show_front = "--front-logs" in sys.argv
    show_back = "--back-logs" in sys.argv
    
    front_logs = show_both or show_front
    back_logs = show_both or show_back
    
    root = Path(__file__).parent.parent.parent
    
    # Auto-install missing deps
    install_h3_if_needed(root)
    
    print("Iniciando Ashen CRM...")
    print("Recarga automatica: API (uvicorn --reload en /backend) + frontend (Vite HMR en :5173).")
    print("En desarrollo abre el dashboard en http://localhost:5173 — el puerto 8000 sirve la API y archivos estaticos sin HMR.")
    
    # Backend: --reload + --reload-dir solo en `backend` para no reiniciar al escribir en data/*.db
    backend_cmd = (
        "call .venv\\Scripts\\activate.bat && python -m uvicorn backend.main:app "
        "--reload --reload-dir backend --port 8000"
    )
    frontend_cmd = "cd frontend && npm run dev"
    
    if front_logs or back_logs:
        print(f"Modo logs activado. (Front: {'SI' if front_logs else 'NO'} | Back: {'SI' if back_logs else 'NO'}) Usa Ctrl+C para salir.")
        print("-" * 50)
    else:
        print("Modo silencioso. Los servidores estan corriendo en segundo plano en esta terminal.")
        print("Opciones disponibles para ver logs:")
        print("  --logs       (Muestra front y back)")
        print("  --front-logs (Muestra solo frontend)")
        print("  --back-logs  (Muestra solo backend)")
        print("-" * 50)
        
    p1 = run_process(backend_cmd, root, back_logs, "\033[94m[BACK]\033[0m")
    p2 = run_process(frontend_cmd, root, front_logs, "\033[95m[FRONT]\033[0m")
    
    try:
        if not front_logs and not back_logs:
            print(" Servidores activos en:")
            print(" - API: http://localhost:8000")
            print(" - Dashboard: http://localhost:5173")
            print("\nPresiona Ctrl+C para detener ambos servidores.")
            
        p1.wait()
        p2.wait()
    except KeyboardInterrupt:
        print("\n[SISTEMA] Deteniendo servidores...")
        subprocess.run(f"taskkill /F /T /PID {p1.pid}", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(f"taskkill /F /T /PID {p2.pid}", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[SISTEMA] Servidores detenidos exitosamente.")
        sys.exit(0)

if __name__ == "__main__":
    main()
