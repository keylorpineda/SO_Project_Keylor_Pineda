import threading
import time


class TTLManager(threading.Thread):
    """
    Componente Gestor de Transacciones:
    Este hilo corre en segundo plano de manera autónoma (Daemon Thread).
    Su responsabilidad es revisar periódicamente si hay reservas caducadas
    y liberar los asientos/semáforos de manera segura para mantener la propiedad de Liveness.
    """
    def __init__(self, system, interval=1):
        super().__init__(daemon=True)
        self.system   = system
        self.interval = interval
        self._running = True

    def run(self):
        while self._running:
            time.sleep(self.interval)
            self.system.process_expirations()

    def stop(self):
        self._running = False
