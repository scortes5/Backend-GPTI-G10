"""Registros que llegan desde la cola sin conexión del frontend (solicitud de cambio N°2).

El navegador manda en cada registro su identificador y el momento en que se guardó:

- `X-Evento-Id`: si ya se recibió, no se vuelve a aplicar (un reintento tras un corte no duplica
  un lote ni una venta).
- `X-Evento-Creado`: milisegundos desde 1970 (UTC). Con la hora de llegada se calcula la demora.
- `X-Cola: 1`: el registro esperó en el equipo porque no había conexión.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from fastapi import Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EventoCola, Usuario
from app.schemas import ResumenCola

# Relojes de celulares desajustados: una fecha de creación absurda no se usa para medir.
MAXIMA_DEMORA = timedelta(days=30)


@dataclass(frozen=True)
class Evento:
    id_cliente: str
    creado: datetime  # UTC sin zona
    en_cola: bool


def evento_de_cabeceras(
    x_evento_id: str | None = Header(default=None, max_length=64),
    x_evento_creado: str | None = Header(default=None, max_length=20),
    x_cola: str | None = Header(default=None, max_length=2),
) -> Evento | None:
    """Dependencia de FastAPI: None si la solicitud no viene de la cola del frontend."""
    if not x_evento_id:
        return None
    ahora = _ahora_utc()
    creado = ahora
    if x_evento_creado and x_evento_creado.isdigit():
        leido = datetime.fromtimestamp(int(x_evento_creado) / 1000, timezone.utc).replace(tzinfo=None)
        if ahora - MAXIMA_DEMORA <= leido <= ahora + timedelta(minutes=5):
            creado = min(leido, ahora)
    return Evento(x_evento_id, creado, x_cola == "1")


def ya_recibido(db: Session, evento: Evento | None, usuario: Usuario) -> EventoCola | None:
    if evento is None:
        return None
    previo = db.get(EventoCola, evento.id_cliente)
    return previo if previo and previo.usuario_id == usuario.id else None


def registrar(db: Session, evento: Evento | None, tipo: str, recurso: str, usuario: Usuario) -> None:
    if evento is None or db.get(EventoCola, evento.id_cliente):
        return
    db.add(
        EventoCola(
            id_cliente=evento.id_cliente,
            tipo=tipo,
            recurso=recurso,
            usuario_id=usuario.id,
            en_cola=evento.en_cola,
            creado_cliente=evento.creado,
            recibido=_ahora_utc(),
        )
    )
    db.commit()


def resumen(
    db: Session, usuario: Usuario, usuario_id: int | None = None, desde: date | None = None, hasta: date | None = None
) -> ResumenCola:
    consulta = select(EventoCola)
    if not usuario.es_admin:
        consulta = consulta.where(EventoCola.usuario_id == usuario.id)
    elif usuario_id:
        consulta = consulta.where(EventoCola.usuario_id == usuario_id)
    if desde:
        consulta = consulta.where(EventoCola.recibido >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        consulta = consulta.where(EventoCola.recibido < datetime.combine(hasta + timedelta(days=1), datetime.min.time()))
    eventos = list(db.scalars(consulta))
    demoras = [e.segundos for e in eventos]
    en_cola = [e.segundos for e in eventos if e.en_cola]
    return ResumenCola(
        eventos=len(eventos),
        en_cola=len(en_cola),
        promedio_segundos=_promedio(demoras),
        promedio_cola_segundos=_promedio(en_cola),
        maximo_segundos=max(demoras) if demoras else None,
    )


def _promedio(valores: list[float]) -> float | None:
    return round(sum(valores) / len(valores), 1) if valores else None


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
