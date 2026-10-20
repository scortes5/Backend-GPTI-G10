"""Bloqueo temporal de un correo tras varios intentos de login fallidos (fuerza bruta).

Se guarda en memoria del proceso: suficiente para el piloto con una instancia. Con varias
instancias en AWS habría que moverlo a un almacenamiento compartido (p. ej. la base de datos).
"""
import threading
import time

MAX_FALLOS = 5
VENTANA_SEGUNDOS = 15 * 60


class LimitadorIntentos:
    def __init__(self, max_fallos: int = MAX_FALLOS, ventana_segundos: int = VENTANA_SEGUNDOS):
        self._max_fallos = max_fallos
        self._ventana = ventana_segundos
        self._fallos: dict[str, list[float]] = {}
        self._candado = threading.Lock()

    def bloqueado(self, clave: str) -> bool:
        with self._candado:
            return len(self._recientes(clave)) >= self._max_fallos

    def registrar_fallo(self, clave: str) -> None:
        with self._candado:
            self._fallos[clave] = self._recientes(clave) + [time.monotonic()]

    def limpiar(self, clave: str) -> None:
        with self._candado:
            self._fallos.pop(clave, None)

    def _recientes(self, clave: str) -> list[float]:
        limite = time.monotonic() - self._ventana
        return [momento for momento in self._fallos.get(clave, []) if momento > limite]


limitador_login = LimitadorIntentos()
