"""Clima del campo: estación más cercana, resumen de las últimas 24 horas y alertas agronómicas.

Las alertas son reglas fijas (no IA), para que sean predecibles y funcionen sin conexión al
proveedor de IA. La recomendación con IA las usa como contexto (services/recomendaciones.py).
"""
from datetime import datetime, timedelta
from statistics import mean

from sqlalchemy.orm import Session

from app.models import Usuario
from app.schemas import AlertaOut, ClimaOut, EstacionOut, MedicionOut, ResumenClimaOut
from app.services import campos as campos_service
from app.services.clima import estaciones
from app.services.clima.proveedor import Medicion, ProveedorClima

HORAS_SERIE = 48
ESTACION_LEJANA_KM = 30


def clima_del_campo(db: Session, usuario: Usuario, proveedor: ProveedorClima, usuario_id: int | None = None,
                    ahora: datetime | None = None) -> ClimaOut:
    campo = campos_service.obtener(db, usuario, usuario_id)
    estacion, distancia = estaciones.mas_cercana(campo.latitud, campo.longitud)
    ahora = (ahora or datetime.now()).replace(minute=0, second=0, microsecond=0)
    serie = proveedor.mediciones(estacion.id, ahora - timedelta(hours=HORAS_SERIE - 1), ahora)
    serie = [m for m in serie if m.fecha_hora <= ahora]
    ultimas_24 = [m for m in serie if m.fecha_hora > ahora - timedelta(hours=24)]
    resumen = resumir(ultimas_24)
    actual = serie[-1] if serie else None
    return ClimaOut(
        campo=campos_service.a_salida(campo),
        estacion=EstacionOut(**estacion.__dict__, distancia_km=round(distancia, 1)),
        fuente=proveedor.nombre,
        actual=_salida(actual) if actual else None,
        resumen_24h=resumen,
        serie=[_salida(m) for m in serie],
        alertas=alertas(resumen, actual, distancia, ahora),
    )


def _salida(m: Medicion) -> MedicionOut:
    return MedicionOut(fecha_hora=m.fecha_hora, temperatura=m.temperatura, humedad=m.humedad,
                       precipitacion=m.precipitacion, viento=m.viento)


def _valores(mediciones: list[Medicion], campo: str) -> list[float]:
    return [getattr(m, campo) for m in mediciones if getattr(m, campo) is not None]


def resumir(mediciones: list[Medicion]) -> ResumenClimaOut:
    minimas = _valores(mediciones, "temperatura_min") or _valores(mediciones, "temperatura")
    maximas = _valores(mediciones, "temperatura_max") or _valores(mediciones, "temperatura")
    humedad = _valores(mediciones, "humedad")
    viento = _valores(mediciones, "viento")
    return ResumenClimaOut(
        temperatura_min=round(min(minimas), 1) if minimas else None,
        temperatura_max=round(max(maximas), 1) if maximas else None,
        precipitacion=round(sum(_valores(mediciones, "precipitacion")), 1),
        humedad_media=round(mean(humedad)) if humedad else None,
        viento_max=round(max(viento), 1) if viento else None,
    )


def _n(valor: float) -> str:
    """Número en formato chileno para los textos de las alertas: 16,9."""
    return f"{valor:g}".replace(".", ",")


def alertas(resumen: ResumenClimaOut, actual: Medicion | None, distancia_km: float, ahora: datetime) -> list[AlertaOut]:
    lista: list[AlertaOut] = []

    def agregar(nivel, titulo, detalle):
        lista.append(AlertaOut(nivel=nivel, titulo=titulo, detalle=detalle))

    tmin, tmax = resumen.temperatura_min, resumen.temperatura_max
    if tmin is not None and tmin <= 0:
        agregar("alta", "Helada", f"La mínima llegó a {_n(tmin)} °C. Revisa daños en brotes y flores, y protege lo cosechado del frío.")
    elif tmin is not None and tmin <= 3:
        agregar("media", "Riesgo de helada", f"La mínima fue de {_n(tmin)} °C. Si la noche viene despejada, prepara riego o cubiertas antiheladas.")
    if tmax is not None and tmax >= 32:
        agregar("media", "Calor intenso", f"La máxima llegó a {_n(tmax)} °C. Riega temprano, evita cosechar al mediodía y guarda la cosecha a la sombra.")
    if resumen.precipitacion >= 20:
        agregar("alta", "Lluvia intensa", f"Cayeron {_n(resumen.precipitacion)} mm en 24 h. Revisa drenajes y no entres con maquinaria a suelo saturado.")
    elif resumen.precipitacion >= 5:
        agregar("info", "Lluvia", f"Cayeron {_n(resumen.precipitacion)} mm en 24 h. Puedes ajustar o suspender el riego.")
    if resumen.viento_max is not None and resumen.viento_max >= 40:
        agregar("media", "Viento fuerte", f"Ráfagas de hasta {_n(resumen.viento_max)} km/h. Evita aplicar productos y revisa amarras y mallas.")
    hum, temps = resumen.humedad_media, [t for t in (tmin, tmax) if t is not None]
    if hum is not None and hum >= 85 and temps and 10 <= mean(temps) <= 25:
        agregar("media", "Condiciones para hongos", f"Humedad media de {_n(hum)} % con temperaturas templadas. Vigila botritis y oídio, y ventila la bodega.")
    if actual is None or ahora - actual.fecha_hora > timedelta(hours=3):
        agregar("info", "Sin datos recientes", "La estación no ha enviado lecturas en las últimas horas. Los valores pueden estar desactualizados.")
    if distancia_km > ESTACION_LEJANA_KM:
        agregar("info", "Estación lejana", f"La estación más cercana está a {distancia_km:.0f} km: el clima de tu campo puede ser distinto.")
    return lista


def describir(clima: ClimaOut) -> str:
    """Texto para la IA (y para los registros): ubicación, condiciones y alertas."""
    r, a = clima.resumen_24h, clima.actual
    partes = [
        f"Campo «{clima.campo.nombre}» de {clima.campo.productor} en latitud {clima.campo.latitud:.3f}, longitud {clima.campo.longitud:.3f}.",
        f"Estación {clima.estacion.nombre} ({clima.estacion.comuna}, {clima.estacion.region}) a {clima.estacion.distancia_km:g} km.",
    ]
    if a:
        partes.append(f"Ahora ({a.fecha_hora:%d-%m %H:%M}): {a.temperatura} °C, humedad {a.humedad} %, viento {a.viento} km/h.")
    partes.append(
        f"Últimas 24 h: mínima {r.temperatura_min} °C, máxima {r.temperatura_max} °C, lluvia {r.precipitacion} mm, "
        f"humedad media {r.humedad_media} %, viento máximo {r.viento_max} km/h."
    )
    if clima.alertas:
        partes.append("Alertas: " + "; ".join(f"{x.titulo} ({x.detalle})" for x in clima.alertas))
    return " ".join(partes)
