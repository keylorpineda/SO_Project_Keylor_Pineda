"""
auth.py  -  Gestion de usuarios en el servidor
=================================================
Las credenciales se almacenan en ``server/usuarios.json`` como:
    { "username": "<sha256 del password>" }

La contrasena NUNCA viaja en texto plano: el cliente envia el hash
SHA-256 y el servidor lo compara directamente con el hash guardado.

Si el archivo no existe, se crea automaticamente con usuarios por defecto
la primera vez. A partir de ahi, el JSON es la unica fuente de verdad.

Acceso protegido por RLock para soportar multiples hilos concurrentes.
"""

import json
import os
import sys
import hashlib
import threading

# Directorio donde vive el ejecutable (o el script en desarrollo)
# En un .exe de PyInstaller: carpeta del exe (dist/)
# En desarrollo:             carpeta server/
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Archivo donde se persisten los usuarios
_USERS_FILE = os.path.join(_BASE_DIR, "usuarios.json")

# Usuarios iniciales que se crean SOLO si el archivo NO existe todavia.
# Una vez que el archivo existe, este diccionario NO se usa mas.
_BOOTSTRAP_USERS = {
    "keylor":   hashlib.sha256(b"1234").hexdigest(),
    "allan":    hashlib.sha256(b"1234").hexdigest(),
    "admin":    hashlib.sha256(b"admin").hexdigest(),
    "usuario1": hashlib.sha256(b"pass1").hexdigest(),
    "usuario2": hashlib.sha256(b"pass2").hexdigest(),
    "usuario3": hashlib.sha256(b"pass3").hexdigest(),
}

# Reglas de validacion
MIN_USER_LEN = 3
MIN_PASS_LEN = 4


class AuthManager:
    """
    Gestiona autenticacion y registro de usuarios de forma thread-safe.

    Protocolo de contrasena:
        - El cliente computa  sha256(password)  y envia el hexdigest.
        - El servidor guarda y compara directamente ese hexdigest.
        - Asi el texto plano NUNCA viaja por la red ni se guarda en disco.
    """

    def __init__(self):
        self._lock  = threading.RLock()
        self._users = {}
        self._load()

    # -- Persistencia --------------------------------------------------------
    def _load(self):
        """Carga usuarios EXCLUSIVAMENTE desde el archivo JSON.
        Si el archivo no existe, lo crea con los usuarios de bootstrap."""
        if os.path.exists(_USERS_FILE):
            try:
                with open(_USERS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                with self._lock:
                    self._users = dict(saved)
                print(f"[AUTH] {len(self._users)} usuarios cargados desde {_USERS_FILE}")
            except Exception as e:
                print(f"[AUTH] Error al leer {_USERS_FILE}: {e}")
                print("[AUTH] Usando usuarios de bootstrap como fallback.")
                with self._lock:
                    self._users = dict(_BOOTSTRAP_USERS)
        else:
            # Primera vez: crear el archivo con usuarios iniciales
            print(f"[AUTH] Archivo de usuarios no encontrado. Creando con usuarios por defecto...")
            with self._lock:
                self._users = dict(_BOOTSTRAP_USERS)
            self._save()
            print(f"[AUTH] {len(self._users)} usuarios creados en {_USERS_FILE}")

    def _save(self):
        """Escribe el estado actual en disco (llamar siempre dentro del lock)."""
        try:
            with open(_USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AUTH] Error al guardar usuarios: {e}")

    # -- Operaciones publicas (thread-safe) ----------------------------------
    def login(self, username: str, pw_hash: str) -> tuple:
        """
        Verifica credenciales.

        Args:
            username: nombre en minusculas.
            pw_hash:  sha256 hexdigest de la contrasena original.

        Returns:
            (True, username_capitalizado) | (False, mensaje_de_error)
        """
        username = username.strip().lower()
        if not username:
            return False, "El nombre de usuario no puede estar vacio."

        with self._lock:
            stored = self._users.get(username)

        if stored is None:
            return False, f"Usuario '{username}' no encontrado."
        if stored != pw_hash:
            return False, "Contrasena incorrecta."

        return True, username.capitalize()

    def register(self, username: str, pw_hash: str) -> tuple:
        """
        Registra un nuevo usuario.

        Validaciones:
            - username: >=3 chars, solo [a-z0-9_-] (tras lowercase).
            - pw_hash:  debe ser un hexdigest SHA-256 de 64 chars.
            - username no debe existir ya.

        Returns:
            (True, username_capitalizado) | (False, mensaje_de_error)
        """
        username = username.strip().lower()

        # Validar formato de username
        if len(username) < MIN_USER_LEN:
            return False, f"El nombre de usuario debe tener al menos {MIN_USER_LEN} caracteres."
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
        if not all(c in allowed for c in username):
            return False, "El nombre solo puede contener letras, numeros, guiones y '_'."

        # Validar hash (64 hex chars = SHA-256)
        if len(pw_hash) != 64 or not all(c in "0123456789abcdef" for c in pw_hash):
            return False, "Hash de contrasena invalido."

        with self._lock:
            if username in self._users:
                return False, f"El usuario '{username}' ya existe. Elige otro nombre."
            self._users[username] = pw_hash
            self._save()

        print(f"[AUTH] Usuario registrado: '{username}'")
        return True, username.capitalize()

    def user_count(self) -> int:
        with self._lock:
            return len(self._users)
