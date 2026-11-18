"""Datos estructurados de cada consulta, para proveedores que no interpretan texto (el simulado)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class LoteEnBodega:
    cultivo: str
    kilos: float
    dias: int  # desde la cosecha


@dataclass(frozen=True)
class ContextoCampo:
    temperatura_min: float | None = None
    temperatura_max: float | None = None
    lluvia_24h: float = 0.0
    humedad_media: float | None = None
    viento_max: float | None = None
    humedad_suelo: float | None = None  # None: sin sensor o sin lectura reciente
    temperatura_suelo: float | None = None
    lotes: tuple[LoteEnBodega, ...] = ()


@dataclass(frozen=True)
class ContextoLote:
    cultivo: str
    kilos: float
    kilos_disponibles: float
    dias: int


Contexto = ContextoCampo | ContextoLote
