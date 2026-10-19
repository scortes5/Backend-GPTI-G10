"""Indicadores generales de la cooperativa para el dashboard."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Lote, Venta
from app.schemas import ResumenOut


def resumen(db: Session) -> ResumenOut:
    kilos_cosechados = db.scalar(select(func.coalesce(func.sum(Lote.kilos), 0)))
    kilos_vendidos = db.scalar(select(func.coalesce(func.sum(Venta.kilos), 0)))
    ingresos = db.scalar(select(func.coalesce(func.sum(Venta.kilos * Venta.precio_por_kilo), 0)))
    return ResumenOut(
        total_lotes=db.scalar(select(func.count(Lote.id))),
        kilos_cosechados=kilos_cosechados,
        kilos_vendidos=kilos_vendidos,
        kilos_disponibles=kilos_cosechados - kilos_vendidos,
        ingresos=ingresos,
        kilos_por_cultivo=_kilos_por_cultivo(db),
    )


def _kilos_por_cultivo(db: Session) -> dict[str, float]:
    filas = db.execute(select(Lote.cultivo, func.sum(Lote.kilos)).group_by(Lote.cultivo))
    return {cultivo: kilos for cultivo, kilos in filas}
