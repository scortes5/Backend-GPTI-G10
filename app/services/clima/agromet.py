"""Adapter para la Red Agroclimática Nacional (agromet.cl).

Agromet no publica una API documentada. Este adapter usa el mismo servicio que alimenta los
gráficos del portal (getGraphData.php), tal como lo hace el paquete abierto agrometR:

    GET {AGROMET_URL}?ema_ia_id=<estación>&dateFrom=AAAA-MM-DD HH:MM:SS&dateTo=...&portada=false

La respuesta es XML: <gra> describe cada variable ("n|Nombre (unidad)|n") y cada <dato> es una
fila separada por "|" en la que la fecha y los valores ocupan las posiciones impares.

Importante: hoy el firewall de agromet.cl bloquea los clientes automáticos (HTTP 403). Para usarlo en
producción hay que pedir acceso a la red (info@agromet.cl). Mientras tanto se usa el proveedor
simulado (CLIMA_PROVEEDOR=simulado).
"""
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime

from app.exceptions import ServicioExternoNoDisponible
from app.services.clima.proveedor import Medicion

FORMATOS_FECHA = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M")


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower()


def campo_de_variable(descripcion: str) -> str | None:
    """Traduce el nombre de una variable de Agromet al campo de Medicion (o None si no se usa)."""
    d = _normalizar(descripcion)
    if "temperatura" in d and not any(otra in d for otra in ("suelo", "superficie", "rocio", "hoja")):
        if "min" in d:
            return "temperatura_min"
        if "max" in d:
            return "temperatura_max"
        return "temperatura"
    if "humedad" in d and "suelo" not in d and "hoja" not in d:
        return "humedad"
    if "precipitacion" in d or "lluvia" in d:
        return "precipitacion"
    if "viento" in d and ("velocidad" in d or "max" in d) and "direccion" not in d:
        return "viento"
    return None


def _numero(valor: str) -> float | None:
    valor = valor.strip().replace(",", ".")
    try:
        return float(valor)
    except ValueError:
        return None


def _fecha(valor: str) -> datetime | None:
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(valor.strip(), formato)
        except ValueError:
            continue
    return None


def interpretar(xml: str) -> list[Medicion]:
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError as e:
        raise ServicioExternoNoDisponible("Agromet respondió en un formato inesperado") from e

    variables = [re.sub(r"^\d{1,2}\||\|\d{1,2}$", "", (g.text or "")) for g in raiz.iter("gra")]
    if not variables:  # p. ej. la página HTML del firewall: no son datos de la estación
        raise ServicioExternoNoDisponible("Agromet respondió en un formato inesperado")
    campos = [campo_de_variable(v) for v in variables]
    mediciones = []
    for dato in raiz.iter("dato"):
        partes = (dato.text or "").split("|")
        valores = partes[1::2]  # fecha, variable 1, variable 2, ...
        if not valores:
            continue
        fecha = _fecha(valores[0])
        if fecha is None:
            continue
        lectura = {}
        for campo, valor in zip(campos, valores[1:]):
            if campo and campo not in lectura:
                lectura[campo] = _numero(valor)
        if lectura.get("temperatura") is None and lectura.get("temperatura_min") is not None and lectura.get("temperatura_max") is not None:
            lectura["temperatura"] = (lectura["temperatura_min"] + lectura["temperatura_max"]) / 2
        mediciones.append(Medicion(fecha_hora=fecha, **lectura))
    return sorted(mediciones, key=lambda m: m.fecha_hora)


class AgrometAdapter:
    def __init__(self, url: str, cache_minutos: int = 15, timeout: float = 20, nombre: str = "agromet"):
        self.nombre = nombre
        self.url = url
        self.cache_segundos = cache_minutos * 60
        self.timeout = timeout
        self._cache: dict[tuple, tuple[float, list[Medicion]]] = {}

    def mediciones(self, estacion_id: int, desde: datetime, hasta: datetime) -> list[Medicion]:
        # Se agrupa por hora para que varias consultas seguidas usen la misma respuesta.
        clave = (estacion_id, desde.replace(minute=0, second=0, microsecond=0), hasta.replace(minute=0, second=0, microsecond=0))
        guardado = self._cache.get(clave)
        if guardado and time.monotonic() - guardado[0] < self.cache_segundos:
            return guardado[1]
        resultado = interpretar(self._descargar(estacion_id, desde, hasta))
        self._cache[clave] = (time.monotonic(), resultado)
        return resultado

    def _descargar(self, estacion_id: int, desde: datetime, hasta: datetime) -> str:
        import httpx

        params = {
            "ema_ia_id": estacion_id,
            "dateFrom": desde.strftime("%Y-%m-%d %H:%M:%S"),
            "dateTo": hasta.strftime("%Y-%m-%d %H:%M:%S"),
            "portada": "false",
        }
        try:
            respuesta = httpx.get(self.url, params=params, timeout=self.timeout,
                                  headers={"User-Agent": "AgroTracker/1.0 (Cooperativa Newen al Sur)"})
        except httpx.RequestError as e:
            raise ServicioExternoNoDisponible("No se pudo conectar con Agromet. Intenta más tarde.") from e
        if respuesta.status_code == 403:
            raise ServicioExternoNoDisponible("Agromet rechazó la consulta (acceso no autorizado). Hay que solicitar acceso a la red.")
        if not respuesta.is_success:
            raise ServicioExternoNoDisponible(f"Agromet no está disponible ({respuesta.status_code}).")
        return respuesta.text
