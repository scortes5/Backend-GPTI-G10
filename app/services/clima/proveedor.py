from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Medicion:
    """Una lectura horaria de una estación. Los valores que la estación no mide quedan en None."""

    fecha_hora: datetime
    temperatura: float | None = None  # °C, promedio de la hora
    temperatura_min: float | None = None  # °C
    temperatura_max: float | None = None  # °C
    humedad: float | None = None  # % humedad relativa
    precipitacion: float | None = None  # mm en la hora
    viento: float | None = None  # km/h, máximo de la hora


class ProveedorClima(Protocol):
    """Puerto (patrón Adapter): lo único que el dominio sabe de la fuente de datos climáticos."""

    nombre: str

    def mediciones(self, estacion_id: int, desde: datetime, hasta: datetime) -> list[Medicion]: ...
