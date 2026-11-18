from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class LecturaSensor:
    fecha_hora: datetime
    humedad_suelo: float | None = None  # % de la capacidad de campo
    temperatura_suelo: float | None = None  # °C


@dataclass(frozen=True)
class DatosSensores:
    dispositivo: str
    lecturas: list[LecturaSensor]  # de la más antigua a la más reciente


class ProveedorSensores(Protocol):
    """Puerto (patrón Adapter): lo único que el dominio sabe de los sensores del campo."""

    nombre: str

    def lecturas(self, latitud: float, longitud: float, horas: int = 24) -> DatosSensores: ...
