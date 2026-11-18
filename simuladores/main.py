"""APIs simuladas de Agromet e Instacrops para desarrollo y demos. No usar con datos reales.

- Agromet: imita getGraphData.php, con el mismo XML que lee el adapter real.
- Instacrops: no tenemos su especificación, así que este contrato JSON es una propuesta nuestra.
- /escenario: cambia las condiciones de ambas APIs. No tiene clave: este servicio no debe publicarse.

Local: uvicorn simuladores.main:app --port 9000
"""
import os
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

from fastapi import FastAPI, Header, HTTPException, Query, Response

from simuladores import datos

MAX_HORAS = 24 * 31
TOKEN_INSTACROPS = os.getenv("INSTACROPS_TOKEN", "demo")
VARIABLES_AGROMET = (
    ("Temperatura del Aire Mínima (°C)", "temperatura_min"),
    ("Temperatura del Aire Promedio (°C)", "temperatura"),
    ("Temperatura del Aire Máxima (°C)", "temperatura_max"),
    ("Humedad Relativa Promedio (%)", "humedad"),
    ("Precipitación Horaria (mm)", "precipitacion"),
    ("Dirección del Viento (°)", "direccion_viento"),
    ("Velocidad de Viento Máxima (km/h)", "viento"),
)

inicial = os.getenv("ESCENARIO", "normal")
estado = {"escenario": inicial if inicial in datos.ESCENARIOS else "normal"}

app = FastAPI(title="Simuladores AgroTracker")


def _hora_exacta(momento: datetime) -> datetime:
    return momento.replace(minute=0, second=0, microsecond=0)


def _fecha(valor: str) -> datetime:
    try:
        return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        raise HTTPException(400, "Fecha inválida") from e


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/escenario")
def ver_escenario():
    return {"escenario": estado["escenario"], "disponibles": datos.ESCENARIOS}


@app.put("/escenario/{nombre}")
def cambiar_escenario(nombre: str):
    if nombre not in datos.ESCENARIOS:
        raise HTTPException(404, f"Escenarios disponibles: {', '.join(datos.ESCENARIOS)}")
    estado["escenario"] = nombre
    return {"escenario": nombre}


@app.get("/agromet/getGraphData.php")
def agromet(ema_ia_id: int, dateFrom: str, dateTo: str, portada: str = "false"):  # noqa: N803 (nombres de Agromet)
    if estado["escenario"] == "sin_agromet":
        raise HTTPException(503, "Agromet simulado fuera de servicio")
    desde, hasta = _hora_exacta(_fecha(dateFrom)), _fecha(dateTo)
    if hasta < desde or hasta - desde > timedelta(hours=MAX_HORAS):
        raise HTTPException(400, "Rango de fechas inválido")

    filas = [f"<gra>{i}|{escape(nombre)}|{i}</gra>" for i, (nombre, _) in enumerate(VARIABLES_AGROMET, 1)]
    hora = desde
    while hora <= hasta:
        lectura = datos.clima(ema_ia_id, hora, estado["escenario"])
        valores = "|".join(f"{i}|{getattr(lectura, campo)}" for i, (_, campo) in enumerate(VARIABLES_AGROMET, 1))
        filas.append(f"<dato>0|{hora:%Y-%m-%d %H:%M:%S}|{valores}</dato>")
        hora += timedelta(hours=1)
    xml = '<?xml version="1.0" encoding="UTF-8"?><datos>' + "".join(filas) + "</datos>"
    return Response(xml, media_type="text/xml; charset=utf-8")


@app.get("/instacrops/v1/lecturas")
def instacrops(
    latitud: float = Query(ge=-90, le=90),
    longitud: float = Query(ge=-180, le=180),
    horas: int = Query(default=24, ge=1, le=MAX_HORAS),
    authorization: str = Header(default=""),
):
    if authorization != f"Bearer {TOKEN_INSTACROPS}":
        raise HTTPException(401, "Token inválido")
    if estado["escenario"] == "sin_instacrops":
        raise HTTPException(503, "Instacrops simulado fuera de servicio")
    ahora = _hora_exacta(datetime.now())
    lecturas = []
    for atras in range(horas - 1, -1, -1):
        hora = ahora - timedelta(hours=atras)
        suelo = datos.suelo(latitud, longitud, hora, estado["escenario"])
        lecturas.append({
            "fecha_hora": hora.isoformat(),
            "humedad_suelo": suelo.humedad,
            "temperatura_suelo": suelo.temperatura,
        })
    return {"dispositivo": datos.dispositivo(latitud, longitud), "lecturas": lecturas}
