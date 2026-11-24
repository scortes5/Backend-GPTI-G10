"""Datos inventados para las APIs simuladas. Clima y suelo salen del mismo escenario, así son coherentes.

Para un mismo escenario, lugar y hora el resultado es siempre igual: las pantallas no cambian al recargar.
"""
import json
import math
import random
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ESCENARIOS = ("normal", "helada", "lluvia", "sequia", "sin_agromet", "sin_instacrops")
ARCHIVO_ESTACIONES = Path(__file__).resolve().parents[1] / "app" / "data" / "estaciones_agromet.json"
LATITUD_POR_DEFECTO = -38.7

_latitudes: dict[int, float] | None = None


@dataclass(frozen=True)
class Clima:
    temperatura: float
    temperatura_min: float
    temperatura_max: float
    humedad: float
    precipitacion: float
    direccion_viento: int
    viento: float


@dataclass(frozen=True)
class Suelo:
    humedad: float  # % de la capacidad de campo
    temperatura: float  # °C


def latitud_de_estacion(estacion_id: int) -> float:
    global _latitudes
    if _latitudes is None:
        estaciones = json.loads(ARCHIVO_ESTACIONES.read_text(encoding="utf-8"))
        _latitudes = {e["id"]: e["latitud"] for e in estaciones}
    return _latitudes.get(estacion_id, LATITUD_POR_DEFECTO)


def _ciclo(hora: datetime, desfase: int) -> float:
    return math.sin(2 * math.pi * (hora.hour - desfase) / 24)


def clima(estacion_id: int, hora: datetime, escenario: str) -> Clima:
    latitud = latitud_de_estacion(estacion_id)
    dia = random.Random(f"{estacion_id}-{hora:%Y%m%d}")
    azar = random.Random(f"{estacion_id}-{hora:%Y%m%d%H}")
    lluvia = 0.0
    if escenario == "helada":
        media, amplitud, humedad, viento = 3.0, 6.0, 78.0, dia.uniform(3, 8)
    elif escenario == "lluvia":
        media, amplitud, humedad, viento = 11.0, 2.0, 95.0, dia.uniform(18, 26)
        lluvia = azar.uniform(1.2, 3.2)
    elif escenario == "sequia":
        media, amplitud, humedad, viento = 26.0, 8.0, 32.0, dia.uniform(12, 20)
    else:  # más frío al sur y en invierno (enero es el mes más cálido)
        estacional = 25 - 0.32 * abs(latitud) + 6 * math.cos(2 * math.pi * (hora.month - 1) / 12)
        media, amplitud, humedad, viento = estacional + dia.uniform(-1.5, 1.5), dia.uniform(5, 6.5), 68.0, dia.uniform(8, 16)

    ciclo = _ciclo(hora, 9)
    temperatura = media + amplitud * ciclo + azar.uniform(-0.5, 0.5)
    return Clima(
        temperatura=round(temperatura, 1),
        temperatura_min=round(temperatura - 0.5, 1),
        temperatura_max=round(temperatura + 0.5, 1),
        humedad=round(min(100.0, max(20.0, humedad - 1.8 * amplitud * ciclo + azar.uniform(-3, 3)))),
        precipitacion=round(lluvia, 1),
        direccion_viento=azar.randrange(360),
        viento=round(viento + 4 * _ciclo(hora, 12) + azar.uniform(0, 4), 1),
    )


def dispositivo(latitud: float, longitud: float) -> str:
    return f"IC-{zlib.crc32(f'{latitud:.3f},{longitud:.3f}'.encode()) % 9000 + 1000}"


def suelo(latitud: float, longitud: float, hora: datetime, escenario: str) -> Suelo:
    lugar = f"{latitud:.3f},{longitud:.3f}"
    campo = random.Random(lugar)
    azar = random.Random(f"{lugar}-{hora:%Y%m%d%H}")
    humedad, temperatura = {
        "helada": (62.0, 5.0),
        "lluvia": (96.0, 10.0),
        "sequia": (18.0, 24.0),
    }.get(escenario, (52 + campo.uniform(-6, 10), 14.0))
    return Suelo(
        humedad=round(min(100.0, max(0.0, humedad + azar.uniform(-1, 1))), 1),
        temperatura=round(temperatura + 1.5 * _ciclo(hora, 14) + azar.uniform(-0.2, 0.2), 1),
    )
