import socket
import json
import hashlib as _hashlib

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9090

def set_server_address(host: str, port: int):
    global DEFAULT_HOST, DEFAULT_PORT
    if host:
        DEFAULT_HOST = host
    if port:
        DEFAULT_PORT = int(port)

def _hash_pw(password: str) -> str:
    """SHA-256 del password. El texto plano nunca sale del cliente."""
    return _hashlib.sha256(password.encode()).hexdigest()


# En el contexto del proyecto, estas funciones son llamadas por hilos
# independientes en el cliente (simulando usuarios concurrentes)
# para enviar y recibir datos del servidor protegiendo el flujo TCP.
# IMPORTANTE: host/port son None por defecto y se resuelven en tiempo
# de LLAMADA (no de importacion) para que set_server_address() funcione.
def send_request(request, host=None, port=None):
    if host is None:
        host = DEFAULT_HOST
    if port is None:
        port = DEFAULT_PORT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # TCP_NODELAY: desactiva el algoritmo de Nagle para envío inmediato
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(15)
        s.connect((host, port))
        s.sendall(json.dumps(request).encode() + b"\n")
        data = b""
        while True:
            chunk = s.recv(65536)   # buffer grande: menos viajes de red
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
    return json.loads(data.decode().strip())


def check(zone_id, session_id=None, host=None, port=None):
    req = {"action": "check", "zone_id": zone_id}
    if session_id:
        req["session_id"] = session_id
    return send_request(req, host, port)


def login(username, password, session_id=None, host=None, port=None):
    """
    Autentica al usuario contra el servidor.
    Solo envia el hash SHA-256 de la contrasena, nunca el texto plano.
    Incluye session_id para que el servidor re-asocie holds/reservas previas al nuevo session.
    """
    req = {"action": "login", "username": username, "pw_hash": _hash_pw(password)}
    if session_id:
        req["session_id"] = session_id
    return send_request(req, host, port)


def register(username, password, session_id=None, host=None, port=None):
    """
    Registra un nuevo usuario en el servidor.
    Solo envia el hash SHA-256 de la contrasena, nunca el texto plano.
    Incluye session_id para que el servidor registre la sesión activa desde el inicio.
    """
    req = {"action": "register", "username": username, "pw_hash": _hash_pw(password)}
    if session_id:
        req["session_id"] = session_id
    return send_request(req, host, port)


def select_seat(zone_id, row, col, session_id, host=None, port=None):
    """Pre-selecciona un asiento en el servidor (AVAILABLE -> SELECTED)."""
    return send_request(
        {"action": "select", "zone_id": zone_id, "row": row, "col": col, "session_id": session_id},
        host, port
    )


def deselect_seat(zone_id, row, col, session_id, host=None, port=None):
    """Libera un asiento pre-seleccionado (SELECTED -> AVAILABLE)."""
    return send_request(
        {"action": "deselect", "zone_id": zone_id, "row": row, "col": col, "session_id": session_id},
        host, port
    )


def reserve(zone_id, row, col, session_id=None, host=None, port=None):
    req = {"action": "reserve", "zone_id": zone_id, "row": row, "col": col}
    if session_id:
        req["session_id"] = session_id
    return send_request(req, host, port)


def reserve_multiple(seats, session_id=None, host=None, port=None):
    req = {"action": "reserve_multiple", "seats": seats}
    if session_id:
        req["session_id"] = session_id
    return send_request(req, host, port)


def confirm(tx_id, session_id=None, host=None, port=None):
    req = {"action": "confirm", "tx_id": tx_id}
    if session_id:
        req["session_id"] = session_id
    return send_request(req, host, port)


def cancel(tx_id, session_id=None, host=None, port=None):
    req = {"action": "cancel", "tx_id": tx_id}
    if session_id:
        req["session_id"] = session_id
    return send_request(req, host, port)


def release_session(session_id, host=None, port=None):
    """Libera todos los asientos de esta sesion en el servidor (llamar al cerrar)."""
    return send_request(
        {"action": "release_session", "session_id": session_id},
        host, port
    )


def get_ttl(session_id, host=None, port=None):
    """Consulta cuantos segundos quedan en el TTL de sesion.
    Util al reconectarse para sincronizar el countdown con el tiempo real del servidor.
    Devuelve 0 si la sesion no tiene holds activos o si el TTL expiro.
    """
    return send_request(
        {"action": "ttl_status", "session_id": session_id},
        host, port
    )


def global_state(session_id=None, host=None, port=None):
    req = {"action": "global_state"}
    if session_id:
        req["session_id"] = session_id
    return send_request(req, host, port)


def get_log(host=None, port=None):
    return send_request({"action": "log"}, host, port)

def reset_server(host=None, port=None):
    return send_request({"action": "reset"}, host, port)