"""Indicadores para el dashboard: de toda la cooperativa (admin) o solo del productor."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Lote, Usuario, Venta
from app.schemas import ResumenOut
from app.services.lotes import visibles_para


def resumen(db: Session, usuario: Usuario) -> ResumenOut:
    def total(columna, *joins) -> float:
        consulta = select(func.coalesce(func.sum(columna), 0)).select_from(Lote)
        for tabla in joins:
            consulta = consulta.join(tabla)
        return db.scalar(visibles_para(consulta, usuario))

    kilos_cosechados = total(Lote.kilos)
    kilos_vendidos = total(Venta.kilos, Lote.ventas)
    return ResumenOut(
        total_lotes=db.scalar(visibles_para(select(func.count(Lote.id)), usuario)),
        kilos_cosechados=kilos_cosechados,
        kilos_vendidos=kilos_vendidos,
        kilos_disponibles=kilos_cosechados - kilos_vendidos,
        ingresos=total(Venta.kilos * Venta.precio_por_kilo, Lote.ventas),
        kilos_por_cultivo=_kilos_por_cultivo(db, usuario),
    )


def _kilos_por_cultivo(db: Session, usuario: Usuario) -> dict[str, float]:
    consulta = visibles_para(select(Lote.cultivo, func.sum(Lote.kilos)), usuario).group_by(Lote.cultivo)
    return {cultivo: kilos for cultivo, kilos in db.execute(consulta)}
