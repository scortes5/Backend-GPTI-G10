"""Datos climáticos de ejemplo, sin red: para desarrollo, demos y mientras no haya acceso a Agromet.

Son plausibles para la latitud y la época del año (hemisferio sur) y siempre iguales para la misma
estación y hora, así las pantallas no cambian en cada recarga.
"""
import math
import random
from datetime import datetime, timedelta

from app.services.clima import estaciones
from app.services.clima.proveedor import Medicion


class ProveedorClimaSimulado:
    nombre = "simulado"

    def mediciones(self, estacion_id: int, desde: datetime, hasta: datetime) -> list[Medicion]:
        estacion = next((e for e in estaciones.todas() if e.id == estacion_id), None)
        latitud = estacion.latitud if estacion else -38.7
        hora = desde.replace(minute=0, second=0, microsecond=0)
        resultado = []
        while hora <= hasta:
            resultado.append(self._lectura(estacion_id, latitud, hora))
            hora += timedelta(hours=1)
        return resultado

    @staticmethod
    def _lectura(estacion_id: int, latitud: float, hora: datetime) -> Medicion:
        dia = random.Random(f"{estacion_id}-{hora:%Y%m%d}")  # el clima de cada día
        azar = random.Random(f"{estacion_id}-{hora:%Y%m%d%H}")
        # Temperatura media: más fría al sur y en invierno (enero es el mes más cálido).
        media = 25 - 0.32 * abs(latitud) + 6 * math.cos(2 * math.pi * (hora.month - 1) / 12) + dia.uniform(-3, 3)
        amplitud = dia.uniform(5, 9)
        temperatura = media + amplitud * math.sin(2 * math.pi * (hora.hour - 9) / 24) + azar.uniform(-0.6, 0.6)
        llueve = dia.random() < (0.15 + max(0.0, abs(latitud) - 33) * 0.02)
        precipitacion = round(azar.uniform(0.2, 2.5), 1) if llueve and azar.random() < 0.5 else 0.0
        humedad = min(100.0, max(25.0, 95 - 3.2 * (temperatura - media + amplitud) + (12 if llueve else 0) + azar.uniform(-4, 4)))
        viento = max(0.0, dia.uniform(6, 22) + 8 * math.sin(2 * math.pi * (hora.hour - 12) / 24) + azar.uniform(-4, 6))
        return Medicion(
            fecha_hora=hora,
            temperatura=round(temperatura, 1),
            temperatura_min=round(temperatura - 0.5, 1),
            temperatura_max=round(temperatura + 0.5, 1),
            humedad=round(humedad),
            precipitacion=precipitacion,
            viento=round(viento, 1),
        )
