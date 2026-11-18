"""Adapter de sensores de Instacrops.

Aún no tenemos la especificación de su API: este contrato es una propuesta, implementada también por
simuladores/main.py. Cuando exista la especificación real, los cambios deberían quedar en este archivo.

    GET {INSTACROPS_API_URL}/v1/lecturas?latitud=..&longitud=..&horas=24
    Authorization: Bearer <INSTACROPS_API_KEY>

    {"dispositivo": "IC-1234",
     "lecturas": [{"fecha_hora": "2026-11-18T10:00:00", "humedad_suelo": 52.1, "temperatura_suelo": 14.2}]}
"""
import time
from datetime import datetime

from app.exceptions import ServicioExternoNoDisponible
from app.services.sensores.proveedor import DatosSensores, LecturaSensor


def _numero(valor) -> float | None:
    return None if valor is None else float(valor)


def _fecha(valor: str) -> datetime:
    fecha = datetime.fromisoformat(valor)
    return fecha.astimezone().replace(tzinfo=None) if fecha.tzinfo else fecha


def interpretar(datos: dict) -> DatosSensores:
    try:
        lecturas = [
            LecturaSensor(_fecha(l["fecha_hora"]), _numero(l.get("humedad_suelo")), _numero(l.get("temperatura_suelo")))
            for l in datos["lecturas"]
        ]
        return DatosSensores(str(datos["dispositivo"]), sorted(lecturas, key=lambda l: l.fecha_hora))
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        raise ServicioExternoNoDisponible("Instacrops respondió en un formato inesperado") from e


class InstacropsAdapter:
    def __init__(self, url: str, api_key: str, cache_minutos: int = 5, timeout: float = 10, nombre: str = "instacrops"):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.cache_segundos = cache_minutos * 60
        self.timeout = timeout
        self.nombre = nombre
        self._cache: dict[tuple, tuple[float, DatosSensores]] = {}

    def lecturas(self, latitud: float, longitud: float, horas: int = 24) -> DatosSensores:
        clave = (latitud, longitud, horas)
        ahora = time.monotonic()
        guardado = self._cache.get(clave)
        if guardado and ahora - guardado[0] < self.cache_segundos:
            return guardado[1]
        resultado = interpretar(self._descargar(latitud, longitud, horas))
        self._cache = {k: v for k, v in self._cache.items() if ahora - v[0] < self.cache_segundos}
        self._cache[clave] = (ahora, resultado)
        return resultado

    def _descargar(self, latitud: float, longitud: float, horas: int) -> dict:
        import httpx

        try:
            respuesta = httpx.get(
                f"{self.url}/v1/lecturas",
                params={"latitud": latitud, "longitud": longitud, "horas": horas},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        except httpx.RequestError as e:
            raise ServicioExternoNoDisponible("No se pudo conectar con los sensores de Instacrops.") from e
        if respuesta.status_code in (401, 403):
            raise ServicioExternoNoDisponible("Instacrops rechazó la credencial configurada.")
        if not respuesta.is_success:
            raise ServicioExternoNoDisponible(f"Instacrops no está disponible ({respuesta.status_code}).")
        try:
            return respuesta.json()
        except ValueError as e:
            raise ServicioExternoNoDisponible("Instacrops respondió en un formato inesperado") from e
