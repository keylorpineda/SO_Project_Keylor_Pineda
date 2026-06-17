import socket
import threading
import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recursos import ConcertSystem, ZONE_CONFIG
from gestor_ttl import TTLManager
from auth import AuthManager

HOST = "0.0.0.0"
PORT = 9090


# Hilo trabajador (Worker Thread)
# Cada cliente que se conecta es atendido por una instancia independiente de esta función.
# Al ejecutarse concurrentemente, es vital que las funciones del 'system' sean Thread-Safe.
def handle_client(conn, addr, system, auth):
    """
    Gestiona una petición de red (una conexión TCP por request).
    El cliente usa conexiones cortas — cerrar el socket NO significa que
    la sesión del usuario terminó. La limpieza de sesión ocurre vía:
      1. El cliente llama action=release_session al cerrar la app.
      2. El TTLManager expira la sesión automáticamente tras 60s de inactividad.
    """
    try:
        with conn:
            # TCP_NODELAY: envíos sin latencia
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            data = b""
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break
            if not data:
                return
            try:
                request = json.loads(data.decode().strip())
            except json.JSONDecodeError:
                conn.sendall(json.dumps({"ok": False, "error": "JSON inválido"}).encode() + b"\n")
                return

            response = process_request(request, system, auth)
            conn.sendall(json.dumps(response).encode() + b"\n")

    except Exception as e:
        try:
            conn.sendall(json.dumps({"ok": False, "error": str(e)}).encode() + b"\n")
        except Exception:
            pass


def process_request(request, system, auth):
    action     = request.get("action", "")
    session_id = request.get("session_id")

    if session_id and action not in ("check", "global_state", "log", "ttl_status", "release_session"):
        system.extend_session_ttl(session_id)

    # ── Autenticación ────────────────────────────────────────────────────────
    if action == "login":
        username = request.get("username", "").strip().lower()
        pw_hash  = request.get("pw_hash", "")
        ok, result = auth.login(username, pw_hash)
        if ok:
            # result contiene el username real. Registramos la sesión para evitar logins dobles.
            if session_id:
                reg_ok, err = system.register_session(session_id, result)
                if not reg_ok:
                    return {"ok": False, "error": err}
            return {"ok": True, "username": result}
        return {"ok": False, "error": result}

    elif action == "register":
        username = request.get("username", "").strip().lower()
        pw_hash  = request.get("pw_hash", "")
        ok, result = auth.register(username, pw_hash)
        if ok:
            if session_id:
                system.register_session(session_id, result)
            return {"ok": True, "username": result}
        return {"ok": False, "error": result}

    # ── Asientos ─────────────────────────────────────────────────────────────
    elif action == "check":
        zone_id = request.get("zone_id")
        state, err = system.check_availability(zone_id)
        if err:
            return {"ok": False, "error": err}
        return {
            "ok": True,
            "state": state,
            "my_reservations": system.get_my_reservations(session_id),
            "my_holds": system.get_my_holds(session_id),
        }

    elif action == "select":
        # Pre-selecciona un asiento: AVAILABLE → SELECTED (bloqueo temporal)
        zone_id = request.get("zone_id")
        row     = request.get("row")
        col     = request.get("col")
        if not session_id:
            return {"ok": False, "error": "Se requiere session_id para seleccionar asientos"}
        ok, err = system.select_seat(zone_id, row, col, session_id)
        if err:
            return {"ok": False, "error": err}
        return {"ok": True}

    elif action == "deselect":
        # Libera un asiento pre-seleccionado: SELECTED → AVAILABLE
        zone_id = request.get("zone_id")
        row     = request.get("row")
        col     = request.get("col")
        if not session_id:
            return {"ok": False, "error": "Se requiere session_id para deseleccionar asientos"}
        ok, err = system.deselect_seat(zone_id, row, col, session_id)
        if err:
            return {"ok": False, "error": err}
        return {"ok": True}

    elif action == "reserve":
        # Convierte asientos pre-seleccionados (o libres) en RESERVED
        zone_id = request.get("zone_id")
        row     = request.get("row")
        col     = request.get("col")
        tx_id, err = system.reserve_seat(zone_id, row, col, session_id)
        if err:
            return {"ok": False, "error": err}
        return {"ok": True, "tx_id": tx_id}

    elif action == "reserve_multiple":
        requests_seats = [tuple(s) for s in request.get("seats", [])]
        tx_id, err = system.reserve_multiple(requests_seats, session_id)
        if err:
            return {"ok": False, "error": err}
        return {"ok": True, "tx_id": tx_id}

    elif action == "confirm":
        tx_id   = request.get("tx_id")
        ok, err = system.confirm_purchase(tx_id, session_id)
        if err:
            return {"ok": False, "error": err}
        return {"ok": True}

    elif action == "cancel":
        tx_id   = request.get("tx_id")
        ok, err = system.cancel_reservation(tx_id, session_id)
        if err:
            return {"ok": False, "error": err}
        return {"ok": True}

    elif action == "reset":
        system.reset_system()
        return {"ok": True}

    elif action == "release_session":
        # El cliente puede llamar esto explícitamente al cerrar (además del cierre TCP)
        if session_id:
            system.release_session(session_id)
        return {"ok": True}

    elif action == "ttl_status":
        # Consulta cuántos segundos quedan en el TTL de sesión
        if not session_id:
            return {"ok": True, "remaining": 0}
        remaining = system.get_session_ttl(session_id)
        return {"ok": True, "remaining": remaining}

    elif action == "global_state":
        return {
            "ok": True,
            "state": system.get_global_state(),
            "my_reservations": system.get_my_reservations(session_id),
            "my_holds": system.get_my_holds(session_id),
        }

    elif action == "log":
        return {"ok": True, "log": system.get_log()}

    else:
        return {"ok": False, "error": f"Acción desconocida: {action}"}


def get_local_ip():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except Exception:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

def start_server():
    system      = ConcertSystem()
    auth        = AuthManager()
    ttl_manager = TTLManager(system)
    ttl_manager.start()

    # Socket TCP/IP estándar (Protocolo de Transporte de red).
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1024)  # Permite encolar hasta 1024 peticiones simultáneas

    local_ip = get_local_ip()
    os.system("") # Habilitar colores ANSI en Windows
    print("\033[96m" + "=" * 55 + "\033[0m")
    print("\033[96m   SERVIDOR DE RESERVAS — LISTO\033[0m")
    print("\033[96m" + "=" * 55 + "\033[0m")
    print(f"\033[92m  Escuchando en todas las interfaces: 0.0.0.0:{PORT}\033[0m")
    print(f"")
    print(f"\033[93m  Para conectar desde ESTA computadora:\033[0m")
    print(f"\033[97m    IP: 127.0.0.1       Puerto: {PORT}\033[0m")
    print(f"")
    print(f"\033[93m  Para conectar desde OTRA PC (misma red WiFi/LAN):\033[0m")
    print(f"\033[97m    IP: {local_ip:<15}  Puerto: {PORT}\033[0m")
    print("\033[96m" + "=" * 55 + "\033[0m")
    print(f"\033[95m  Zonas: {', '.join(v['nombre'] for v in ZONE_CONFIG.values())}\033[0m")
    print(f"\033[95m  Usuarios registrados: {auth.user_count()}\033[0m")
    print("\033[96m" + "=" * 55 + "\033[0m")
    print("\033[92m  Esperando conexiones...\033[0m")
    print()

    try:
        with ThreadPoolExecutor(max_workers=2000) as executor:
            while True:
                conn, addr = srv.accept()
                # Delegamos la conexión al pool de hilos en lugar de crear uno nuevo infinito
                executor.submit(handle_client, conn, addr, system, auth)
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        srv.close()
        ttl_manager.stop()


if __name__ == "__main__":
    start_server()
