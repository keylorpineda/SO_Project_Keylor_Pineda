import threading
import time
import uuid
import json
import os

ZONE_CONFIG = {
    0: {"nombre": "VIP",                "rows": 5,  "cols": 10}, # 50 asientos
    1: {"nombre": "Preferencial Norte", "rows": 10, "cols": 10}, # 100 asientos
    2: {"nombre": "Preferencial Sur",   "rows": 10, "cols": 10}, # 100 asientos
    3: {"nombre": "General Oeste",      "rows": 10, "cols": 20}, # 200 asientos
    4: {"nombre": "General Este",       "rows": 15, "cols": 20}, # 300 asientos
}

AVAILABLE = "D"
SELECTED  = "S"   # NUEVO: Asiento pre-seleccionado / bloqueado temporalmente por un usuario
RESERVED  = "R"   # Reserva confirmada (esperando pago)
SOLD      = "V"   # Vendido

TTL_SESSION   = 60   # segundos de sesión desde la última selección (se resetea al agregar asientos)
TTL_RESERVED  = 60   # segundos para confirmar una reserva antes de que expire

import sys

if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(_BASE_DIR, "server_state.json")

class ConcertSystem:
    def __init__(self):
        # 1. Matriz de asientos: Recurso compartido crítico principal
        self.seat_matrix  = {}
        # 2. Semáforos por zona: Previenen overbooking y sirven de control de capacidad
        self.semaphores   = {}
        # 3. Locks por zona: Proveen exclusión mutua granular por zona
        self.zone_lock    = {}
        # 4. Lock global de tabla: Protege el diccionario de reservas en memoria
        self.table_lock   = threading.Lock()
        # 5. Lock de log: Protege la bitácora contra escrituras concurrentes
        self.log_lock     = threading.Lock()
        # 6. Lock de IO para escribir en disco
        self.io_lock      = threading.Lock()

        self.reservations = {}
        # holds: clave = (zone_id, row, col), valor = {session_id, created}
        self.holds        = {}
        self.event_log    = []
        # Deadline de TTL por sesión: session_id -> timestamp de expiración
        self.session_deadlines = {}

        for zone_id, cfg in ZONE_CONFIG.items():
            capacity = cfg["rows"] * cfg["cols"]
            self.semaphores[zone_id]  = threading.Semaphore(capacity)
            self.zone_lock[zone_id]   = threading.Lock()
            self.seat_matrix[zone_id] = [
                [AVAILABLE] * cfg["cols"] for _ in range(cfg["rows"])
            ]
            
        self._load_from_disk()

    def _save_state_to_disk(self):
        """Toma una instantánea segura del estado y la guarda en JSON"""
        state = self.get_global_state()
        data = {
            "matrix": {z: state[z]["matrix"] for z in state},
            "reservations": self.reservations,
        }
        with self.io_lock:
            try:
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            except Exception as e:
                print(f"[ERROR] No se pudo guardar el estado en disco: {e}")

    def _load_from_disk(self):
        """Carga el estado del JSON y ajusta los semáforos"""
        if not os.path.exists(DB_FILE):
            return
            
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            loaded_matrix = data.get("matrix", {})
            self.reservations = data.get("reservations", {})
            
            for zone_id, cfg in ZONE_CONFIG.items():
                str_z = str(zone_id)
                if str_z in loaded_matrix:
                    # Sobreescribir matriz
                    self.seat_matrix[zone_id] = loaded_matrix[str_z]
                    # Ajustar semáforos
                    for r in range(cfg["rows"]):
                        for c in range(cfg["cols"]):
                            state = self.seat_matrix[zone_id][r][c]
                            if state in (RESERVED, SOLD):
                                self.semaphores[zone_id].acquire()
                            elif state == SELECTED:
                                # Las preselecciones no sobreviven al reinicio, las limpiamos
                                self.seat_matrix[zone_id][r][c] = AVAILABLE
                                
            print("[PERSISTENCIA] Estado del servidor cargado con éxito.")
        except Exception as e:
            print(f"[ERROR] Error al cargar persistencia: {e}")

    def reset_system(self):
        """Reinicia todo el sistema a cero y elimina la base de datos."""
        # Tomamos todos los locks para evitar inconsistencias durante el reset
        with self.table_lock, self.io_lock, self.log_lock:
            for z in ZONE_CONFIG:
                self.zone_lock[z].acquire()
            
            try:
                self.reservations.clear()
                self.holds.clear()
                self.session_deadlines.clear()
                self.event_log.clear()
                
                for zone_id, cfg in ZONE_CONFIG.items():
                    capacity = cfg["rows"] * cfg["cols"]
                    # Re-instanciar semáforo
                    self.semaphores[zone_id] = threading.Semaphore(capacity)
                    self.seat_matrix[zone_id] = [
                        [AVAILABLE] * cfg["cols"] for _ in range(cfg["rows"])
                    ]
                
                if os.path.exists(DB_FILE):
                    os.remove(DB_FILE)
            finally:
                for z in reversed(list(ZONE_CONFIG.keys())):
                    self.zone_lock[z].release()
                    
            print("[RESET] Servidor reiniciado a estado inicial. Datos eliminados.")

    def _log(self, message):
        ts    = time.strftime("%H:%M:%S")
        
        # Asignar color ANSI según la palabra clave
        # En Windows 10+, os.system("") habilita los códigos de color
        os.system("")
        color = "\033[0m" # Reset
        if "[OK]" in message or "COMPRA CONFIRMADA" in message or "EXITO" in message:
            color = "\033[92m" # Verde brillante
        elif "[ERROR]" in message or "CANCELACIÓN" in message or "EXPIRADO" in message:
            color = "\033[91m" # Rojo brillante
        elif "[PERSISTENCIA]" in message or "[RESET]" in message:
            color = "\033[93m" # Amarillo
        elif "[AUTH]" in message:
            color = "\033[94m" # Azul brillante
        elif "[SELECCIÓN]" in message or "PRESELECCIÓN" in message:
            color = "\033[96m" # Cian
        elif "[NUEVA RESERVA]" in message:
            color = "\033[95m" # Magenta

        entry = f"[{ts}] {message}"
        with self.log_lock:
            self.event_log.append(entry)
            print(f"{color}{entry}\033[0m")

    def check_availability(self, zone_id):
        if zone_id not in self.seat_matrix:
            return None, "Zona no existe"
        with self.zone_lock[zone_id]:
            snapshot = [row[:] for row in self.seat_matrix[zone_id]]
        return snapshot, None

    # ── Selección temporal (pre-bloqueo) ────────────────────────────────────

    def select_seat(self, zone_id, row, col, session_id):
        """
        Pre-selecciona un asiento para una sesión de usuario.
        El asiento pasa de AVAILABLE → SELECTED y queda bloqueado para esa sesión.
        Si otro usuario intenta seleccionar el mismo asiento, recibe un error claro.
        """
        if zone_id not in self.seat_matrix:
            return False, "Zona no existe"
        cfg = ZONE_CONFIG[zone_id]
        if row < 0 or row >= cfg["rows"] or col < 0 or col >= cfg["cols"]:
            return False, "Asiento fuera de rango"

        with self.zone_lock[zone_id]:
            current = self.seat_matrix[zone_id][row][col]
            if current == SOLD:
                return False, f"El asiento F{row}C{col} ya fue vendido y no está disponible"
            if current == RESERVED:
                return False, f"El asiento F{row}C{col} está reservado por otro usuario y no puede seleccionarse"
            if current == SELECTED:
                # ¿Lo tiene el mismo usuario?
                hold = self.holds.get((zone_id, row, col))
                if hold and hold["session_id"] == session_id:
                    return True, None  # ya lo tiene, sin problema
                owner = hold["session_id"][:8] if hold else "desconocido"
                return False, (
                    f"El asiento F{row}C{col} ya está siendo seleccionado por otro usuario (sesión ...{owner}). "
                    f"Por favor elija otro asiento."
                )
            # Asiento disponible: bloquearlo
            self.seat_matrix[zone_id][row][col] = SELECTED
            self.holds[(zone_id, row, col)] = {
                "session_id": session_id,
                "created":    time.time(),
            }

        # Resetear (o iniciar) el deadline de TTL de sesión
        with self.table_lock:
            self.session_deadlines[session_id] = time.time() + TTL_SESSION

        zone_name = ZONE_CONFIG[zone_id]["nombre"]
        self._log(
            f"[SELECCIÓN] Sesión {session_id[:8]} pre-seleccionó asiento "
            f"F{row}C{col} en Zona {zone_name} — TTL sesión reseteado a {TTL_SESSION}s"
        )
        return True, None

    def deselect_seat(self, zone_id, row, col, session_id):
        """
        Libera un asiento pre-seleccionado por esta sesión.
        SELECTED → AVAILABLE.
        """
        if zone_id not in self.seat_matrix:
            return False, "Zona no existe"

        with self.zone_lock[zone_id]:
            hold = self.holds.get((zone_id, row, col))
            if not hold:
                return False, f"El asiento F{row}C{col} no estaba en modo de selección"
            if hold["session_id"] != session_id:
                return False, (
                    f"No puede deseleccionar el asiento F{row}C{col}: "
                    f"pertenece a otra sesión de usuario"
                )
            self.seat_matrix[zone_id][row][col] = AVAILABLE
            del self.holds[(zone_id, row, col)]

        zone_name = ZONE_CONFIG[zone_id]["nombre"]
        self._log(
            f"[DESELECCIÓN] Sesión {session_id[:8]} liberó asiento "
            f"F{row}C{col} en Zona {zone_name}"
        )
        return True, None

    def release_session(self, session_id):
        """
        Libera todos los asientos (SELECTED y RESERVED) asociados a una sesión.
        Se llama cuando el cliente se desconecta.
        """
        released_holds     = []
        released_reserved  = []

        # Liberar pre-selecciones
        with self.table_lock:
            keys_to_remove = [
                k for k, v in self.holds.items()
                if v["session_id"] == session_id
            ]
        for key in keys_to_remove:
            zone_id, row, col = key
            with self.zone_lock[zone_id]:
                if self.seat_matrix[zone_id][row][col] == SELECTED:
                    hold = self.holds.get(key)
                    if hold and hold["session_id"] == session_id:
                        self.seat_matrix[zone_id][row][col] = AVAILABLE
                        self.holds.pop(key, None)
                        released_holds.append(key)

        # Liberar reservas activas
        with self.table_lock:
            txs_to_release = [
                (tx_id, res) for tx_id, res in self.reservations.items()
                if res.get("session_id") == session_id and res.get("active")
            ]
        for tx_id, res in txs_to_release:
            with self.table_lock:
                res["active"] = False
            self._release_seats(res)
            released_reserved.append(tx_id)

        if released_holds or released_reserved:
            self._log(
                f"[DESCONEXIÓN] Sesión {session_id[:8]} cerró la conexión. "
                f"Asientos pre-seleccionados liberados: {len(released_holds)}, "
                f"Reservas canceladas: {len(released_reserved)}"
            )

    # ── Reserva (SELECTED → RESERVED) ───────────────────────────────────────

    def reserve_seat(self, zone_id, row, col, session_id=None):
        """
        Confirma la pre-selección como reserva formal.
        El asiento debe estar en SELECTED por esta sesión, o en AVAILABLE.
        """
        if zone_id not in self.seat_matrix:
            return None, "Zona no existe"
        cfg = ZONE_CONFIG[zone_id]
        if row < 0 or row >= cfg["rows"] or col < 0 or col >= cfg["cols"]:
            return None, "Asiento fuera de rango"

        # NIVEL 1: Adquisición de semáforo (Control de Capacidad)
        acquired = self.semaphores[zone_id].acquire(timeout=5)
        if not acquired:
            return None, "Sin disponibilidad en la zona (semáforo agotado)"

        tx_id   = str(uuid.uuid4())[:8].upper()
        success = False

        try:
            # NIVEL 2: Exclusión Mutua sobre la Zona
            self.zone_lock[zone_id].acquire()
            try:
                current = self.seat_matrix[zone_id][row][col]

                if current == SELECTED:
                    hold = self.holds.get((zone_id, row, col))
                    if hold and session_id and hold["session_id"] != session_id:
                        self.semaphores[zone_id].release()
                        owner = hold["session_id"][:8]
                        return None, (
                            f"El asiento F{row}C{col} está siendo seleccionado por otro usuario "
                            f"(sesión ...{owner}). No se puede reservar."
                        )
                    # Era nuestro hold: liberar la entrada del hold
                    self.holds.pop((zone_id, row, col), None)
                    # El semáforo ya fue adquirido arriba: liberar el doble conteo
                    # porque el hold NO consume semáforo (solo RESERVED lo consume).
                    # Ajuste: liberar el semáforo extra que acabamos de tomar.
                    self.semaphores[zone_id].release()

                elif current == AVAILABLE:
                    pass  # Reserva directa, el semáforo ya fue adquirido
                else:
                    self.semaphores[zone_id].release()
                    if current == RESERVED:
                        return None, f"El asiento F{row}C{col} ya fue reservado por otro usuario"
                    if current == SOLD:
                        return None, f"El asiento F{row}C{col} ya fue vendido"
                    return None, "Asiento no disponible"

                self.seat_matrix[zone_id][row][col] = RESERVED

                # NIVEL 3: Exclusión Mutua sobre la Tabla de Reservas
                self.table_lock.acquire()
                try:
                    if session_id:
                        self.session_deadlines[session_id] = time.time() + TTL_SESSION
                    self.reservations[tx_id] = {
                        "zone_id":    zone_id,
                        "seats":      [(row, col)],
                        "created":    time.time(),
                        "ttl":        TTL_RESERVED,
                        "active":     True,
                        "session_id": session_id,
                    }
                    success = True
                finally:
                    self.table_lock.release()

                if not success:
                    self.seat_matrix[zone_id][row][col] = AVAILABLE

            finally:
                self.zone_lock[zone_id].release()

            if success:
                zone_name = ZONE_CONFIG[zone_id]["nombre"]
                self._log(
                    f"[RESERVA] TX:{tx_id} | Sesión {(session_id or 'N/A')[:8]} reservó "
                    f"asiento F{row}C{col} en Zona {zone_name}. "
                    f"Tiempo para confirmar: {TTL_RESERVED}s"
                )
                self._save_state_to_disk()
                return tx_id, None
            else:
                self.semaphores[zone_id].release()
                return None, "Error interno al crear la reserva"

        except Exception as e:
            self.semaphores[zone_id].release()
            return None, str(e)

    def reserve_multiple(self, requests, session_id=None):
        """
        Reserva múltiples asientos en un solo acto atómico.
        Acepta tanto asientos SELECTED (de esta sesión) como AVAILABLE.
        """
        zone_counts = {}
        for req in requests:
            z = req[0]
            zone_counts[z] = zone_counts.get(z, 0) + 1

        # ESTRATEGIA DE PREVENCIÓN DE DEADLOCKS (Eliminación de Espera Circular)
        unique_zones = sorted(zone_counts.keys())

        # NIVEL 1: Adquisición de semáforos — solo para asientos que NO son holds propios
        # (los holds ya "reservan" capacidad visualmente, el semáforo se toma al confirmar)
        acquired_sems = {z: 0 for z in unique_zones}

        # Primero calcular cuántos asientos son holds propios vs libres
        own_holds_by_zone = {}
        for zone_id, row, col in requests:
            hold = self.holds.get((zone_id, row, col))
            is_own = hold and session_id and hold["session_id"] == session_id
            if is_own:
                own_holds_by_zone[zone_id] = own_holds_by_zone.get(zone_id, 0) + 1

        for zone_id in unique_zones:
            count = zone_counts[zone_id]
            own   = own_holds_by_zone.get(zone_id, 0)
            sem_needed = count - own  # solo los asientos no-hold necesitan semáforo

            success = True
            for _ in range(sem_needed):
                if not self.semaphores[zone_id].acquire(timeout=5):
                    success = False
                    break
                acquired_sems[zone_id] += 1

            if not success:
                for z, amt in acquired_sems.items():
                    for _ in range(amt):
                        self.semaphores[z].release()
                zone_name = ZONE_CONFIG[zone_id]["nombre"]
                return None, f"Sin disponibilidad suficiente en Zona {zone_name}"

        acquired_locks = []
        tx_id   = str(uuid.uuid4())[:8].upper()
        success = False
        seats_reserved_from_available = []

        try:
            # NIVEL 2: Adquisición de locks en orden jerárquico
            for zone_id in unique_zones:
                self.zone_lock[zone_id].acquire()
                acquired_locks.append(zone_id)

            # Verificación de integridad
            for zone_id, row, col in requests:
                cfg     = ZONE_CONFIG[zone_id]
                current = self.seat_matrix[zone_id][row][col]
                if row < 0 or row >= cfg["rows"] or col < 0 or col >= cfg["cols"]:
                    raise ValueError(f"Asiento fuera de rango: Zona {ZONE_CONFIG[zone_id]['nombre']} F{row}C{col}")

                hold = self.holds.get((zone_id, row, col))
                is_own_hold = hold and session_id and hold["session_id"] == session_id

                if current == SELECTED and not is_own_hold:
                    owner = hold["session_id"][:8] if hold else "desconocido"
                    raise ValueError(
                        f"El asiento F{row}C{col} en Zona {ZONE_CONFIG[zone_id]['nombre']} "
                        f"está siendo seleccionado por otro usuario (sesión ...{owner})"
                    )
                if current not in (AVAILABLE, SELECTED) or (current == SELECTED and not is_own_hold):
                    if current == RESERVED:
                        raise ValueError(f"El asiento F{row}C{col} en Zona {ZONE_CONFIG[zone_id]['nombre']} ya fue reservado por otro usuario")
                    if current == SOLD:
                        raise ValueError(f"El asiento F{row}C{col} en Zona {ZONE_CONFIG[zone_id]['nombre']} ya fue vendido")
                    raise ValueError(f"El asiento F{row}C{col} en Zona {ZONE_CONFIG[zone_id]['nombre']} no está disponible")

            # Modificación atómica
            for zone_id, row, col in requests:
                hold = self.holds.get((zone_id, row, col))
                is_own_hold = hold and session_id and hold["session_id"] == session_id
                if is_own_hold:
                    self.holds.pop((zone_id, row, col), None)
                else:
                    seats_reserved_from_available.append((zone_id, row, col))
                self.seat_matrix[zone_id][row][col] = RESERVED

            # Nivel 3: Tabla de reservas
            self.table_lock.acquire()
            try:
                if session_id:
                    self.session_deadlines[session_id] = time.time() + TTL_SESSION
                self.reservations[tx_id] = {
                    "zone_id":    requests[0][0],
                    "seats":      [(z, r, c) for z, r, c in requests],
                    "created":    time.time(),
                    "ttl":        TTL_RESERVED,
                    "active":     True,
                    "multiple":   True,
                    "session_id": session_id,
                }
                success = True
            finally:
                self.table_lock.release()

            if not success:
                for zone_id, row, col in requests:
                    self.seat_matrix[zone_id][row][col] = AVAILABLE

        except Exception as e:
            # Rollback
            for zone_id, row, col in requests:
                if self.seat_matrix[zone_id][row][col] == RESERVED:
                    self.seat_matrix[zone_id][row][col] = AVAILABLE
            for z in reversed(acquired_locks):
                self.zone_lock[z].release()
            for z, amt in acquired_sems.items():
                for _ in range(amt):
                    self.semaphores[z].release()
            return None, str(e)

        for z in reversed(acquired_locks):
            self.zone_lock[z].release()

        if success:
            seats_str = ", ".join(
                f"Z{ZONE_CONFIG[z]['nombre']} F{r}C{c}" for z, r, c in requests
            )
            self._log(
                f"[RESERVA MÚLTIPLE] TX:{tx_id} | Sesión {(session_id or 'N/A')[:8]} | "
                f"{len(requests)} asientos: {seats_str}"
            )
            self._save_state_to_disk()
            return tx_id, None
        else:
            for z, amt in acquired_sems.items():
                for _ in range(amt):
                    self.semaphores[z].release()
            return None, "Error interno al guardar la reserva múltiple"

    # ── Confirmar / Cancelar ─────────────────────────────────────────────────

    def confirm_purchase(self, tx_id, session_id=None):
        with self.table_lock:
            res = self.reservations.get(tx_id)
            if not res or not res["active"]:
                return False, "Transacción no válida o ya procesada"
            # Verificar que la sesión que confirma es la dueña (si se proporcionó)
            if session_id and res.get("session_id") and res["session_id"] != session_id:
                return False, (
                    f"No tiene permiso para confirmar la transacción {tx_id}: "
                    f"pertenece a otra sesión de usuario"
                )
            res["active"] = False

        multiple = res.get("multiple", False)
        seats    = res["seats"]

        if multiple:
            for z in sorted(set(s[0] for s in seats)):
                with self.zone_lock[z]:
                    for s in seats:
                        if s[0] == z:
                            self.seat_matrix[s[0]][s[1]][s[2]] = SOLD
        else:
            row, col = seats[0]
            with self.zone_lock[res["zone_id"]]:
                self.seat_matrix[res["zone_id"]][row][col] = SOLD

        if multiple:
            seats_str = ", ".join(
                f"Zona {ZONE_CONFIG[s[0]]['nombre']} F{s[1]}C{s[2]}" for s in seats
            )
        else:
            seats_str = (
                f"Zona {ZONE_CONFIG[res['zone_id']]['nombre']} "
                f"F{seats[0][0]}C{seats[0][1]}"
            )

        self._log(
            f"[COMPRA CONFIRMADA] TX:{tx_id} | Sesión {(session_id or res.get('session_id', 'N/A'))[:8]} | "
            f"Asientos: {seats_str}"
        )
        self._save_state_to_disk()
        return True, None

    def cancel_reservation(self, tx_id, session_id=None):
        with self.table_lock:
            res = self.reservations.get(tx_id)
            if not res:
                return False, f"Transacción {tx_id} no encontrada"
            if not res.get("active", False) and not res.get("released", False):
                return False, "No se puede cancelar una compra que ya ha sido confirmada"
            if res.get("released", False):
                return False, "Esta reserva ya fue cancelada previamente"
            if session_id and res.get("session_id") and res["session_id"] != session_id:
                return False, (
                    f"No tiene permiso para cancelar la transacción {tx_id}: "
                    f"pertenece a otra sesión de usuario"
                )
            res["active"] = False

        self._release_seats(res)

        if res.get("multiple", False):
            seats_str = ", ".join(
                f"Zona {ZONE_CONFIG[s[0]]['nombre']} F{s[1]}C{s[2]}" for s in res["seats"]
            )
        else:
            seats_str = (
                f"Zona {ZONE_CONFIG[res['zone_id']]['nombre']} "
                f"F{res['seats'][0][0]}C{res['seats'][0][1]}"
            )

        self._log(
            f"[CANCELACIÓN] TX:{tx_id} | Sesión {(session_id or res.get('session_id', 'N/A'))[:8]} | "
            f"Asientos liberados: {seats_str}"
        )
        self._save_state_to_disk()
        return True, None

    def _release_seats(self, reservation):
        if reservation.get("released", False):
            return
        reservation["released"] = True

        seats    = reservation["seats"]
        multiple = reservation.get("multiple", False)

        if multiple:
            for z in sorted(set(s[0] for s in seats)):
                count = sum(1 for s in seats if s[0] == z)
                with self.zone_lock[z]:
                    for s in seats:
                        if s[0] == z and self.seat_matrix[s[0]][s[1]][s[2]] == RESERVED:
                            self.seat_matrix[s[0]][s[1]][s[2]] = AVAILABLE
                for _ in range(count):
                    self.semaphores[z].release()
        else:
            row, col = seats[0]
            zone_id  = reservation["zone_id"]
            with self.zone_lock[zone_id]:
                if self.seat_matrix[zone_id][row][col] == RESERVED:
                    self.seat_matrix[zone_id][row][col] = AVAILABLE
            self.semaphores[zone_id].release()

    def get_session_ttl(self, session_id):
        """Devuelve los segundos restantes del TTL de sesión (0 si expiró o no existe)."""
        deadline = self.session_deadlines.get(session_id)
        if deadline is None:
            return 0
        return max(0.0, deadline - time.time())

    def extend_session_ttl(self, session_id):
        """Extiende el TTL de la sesión al haber una interacción interactiva."""
        with self.table_lock:
            if session_id in self.session_deadlines:
                self.session_deadlines[session_id] = time.time() + TTL_SESSION

    def process_expirations(self):
        """
        Expira asientos pre-seleccionados (SELECTED) cuyo TTL de sesión venció,
        y reservas (RESERVED) con TTL individual vencido.

        El TTL de SELECTED es POR SESIÓN (no por asiento individual):
        - Cuando el usuario selecciona su primer asiento, se crea un deadline
          session_deadlines[session_id] = now + TTL_SESSION (60s).
        - Cada vez que selecciona un asiento adicional, el deadline se RESETEA.
        - Cuando el deadline expira, se liberan TODOS los holds de esa sesión.
        """
        now = time.time()

        # 1. Detectar sesiones con TTL de selección vencido
        expired_sessions = []
        with self.table_lock:
            for sid, deadline in list(self.session_deadlines.items()):
                if now >= deadline:
                    expired_sessions.append(sid)
            for sid in expired_sessions:
                del self.session_deadlines[sid]

        # Liberar todos los holds de las sesiones expiradas
        for sid in expired_sessions:
            expired_holds = []
            with self.table_lock:
                for key, hold in list(self.holds.items()):
                    if hold["session_id"] == sid:
                        expired_holds.append((key, hold))
                for key, _ in expired_holds:
                    self.holds.pop(key, None)

            for (zone_id, row, col), hold in expired_holds:
                with self.zone_lock[zone_id]:
                    if self.seat_matrix[zone_id][row][col] == SELECTED:
                        self.seat_matrix[zone_id][row][col] = AVAILABLE
                zone_name = ZONE_CONFIG[zone_id]["nombre"]
                self._log(
                    f"[TTL SESIÓN EXPIRADO] La sesión {sid[:8]} agotó su tiempo de "
                    f"{TTL_SESSION}s. Asiento F{row}C{col} en Zona {zone_name} liberado."
                )

        # 2. Expirar reservas formales (RESERVED) ligadas a la sesión
        expired_reservations = []
        with self.table_lock:
            for tx_id, res in self.reservations.items():
                if res["active"]:
                    sid = res.get("session_id")
                    if sid and sid in self.session_deadlines:
                        continue
                    elif sid and sid not in self.session_deadlines:
                        res["active"] = False
                        expired_reservations.append((tx_id, dict(res)))
                    else:
                        if (now - res["created"]) > res["ttl"]:
                            res["active"] = False
                            expired_reservations.append((tx_id, dict(res)))

        for tx_id, res in expired_reservations:
            self._release_seats(res)
            if res.get("multiple", False):
                seats_str = ", ".join(
                    f"Zona {ZONE_CONFIG[s[0]]['nombre']} F{s[1]}C{s[2]}" for s in res["seats"]
                )
            else:
                seats_str = (
                    f"Zona {ZONE_CONFIG[res['zone_id']]['nombre']} "
                    f"F{res['seats'][0][0]}C{res['seats'][0][1]}"
                )
            session_short = res.get("session_id", "N/A")
            if session_short:
                session_short = session_short[:8]
            self._log(
                f"[TTL RESERVA EXPIRADO] TX:{tx_id} | Sesión {session_short} | "
                f"Pasaron {res['ttl']}s y el usuario no pagó. "
                f"Asientos liberados: {seats_str}"
            )
            
        if expired_sessions or expired_reservations:
            self._save_state_to_disk()

    def get_log(self):
        with self.log_lock:
            return list(self.event_log)

    def get_global_state(self):
        state = {}
        for zone_id, cfg in ZONE_CONFIG.items():
            with self.zone_lock[zone_id]:
                matrix_copy = [row[:] for row in self.seat_matrix[zone_id]]
            total     = cfg["rows"] * cfg["cols"]
            sold      = sum(r.count(SOLD)      for r in matrix_copy)
            reserved  = sum(r.count(RESERVED)  for r in matrix_copy)
            selected  = sum(r.count(SELECTED)  for r in matrix_copy)
            available = total - sold - reserved - selected
            state[zone_id] = {
                "nombre":       cfg["nombre"],
                "total":        total,
                "disponibles":  available,
                "seleccionados": selected,
                "reservados":   reserved,
                "vendidos":     sold,
                "matrix":       matrix_copy,
            }
        return state
