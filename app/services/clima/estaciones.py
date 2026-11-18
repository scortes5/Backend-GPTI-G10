"""Catastro de estaciones de la Red Agroclimática Nacional (agromet.cl).

app/data/estaciones_agromet.json viene del catastro publicado por Agromet (abril 2022, 417 EMA,
vía el paquete abierto agrometR). Si la red agrega estaciones, basta actualizar ese archivo.
"""
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ARCHIVO = Path(__file__).resolve().parents[2] / "data" / "estaciones_agromet.json"
RADIO_TIERRA_KM = 6371.0


@dataclass(frozen=True)
class Estacion:
    id: int
    nombre: str
    institucion: str
    comuna: str
    region: str
    latitud: float
    longitud: float


@lru_cache
def todas() -> tuple[Estacion, ...]:
    with open(ARCHIVO, encoding="utf-8") as archivo:
        return tuple(Estacion(**dato) for dato in json.load(archivo))


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia sobre la superficie terrestre (fórmula del haversine)."""
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df, dl = f2 - f1, math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(a))


def mas_cercana(latitud: float, longitud: float) -> tuple[Estacion, float]:
    return min(
        ((e, distancia_km(latitud, longitud, e.latitud, e.longitud)) for e in todas()),
        key=lambda par: par[1],
    )
