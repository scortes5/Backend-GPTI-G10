"""Indicadores para el dashboard: de toda la cooperativa (admin) o solo del productor.

Filtros: período (desde/hasta), socio (solo administrador) y cultivo. Las cosechas se filtran por
la fecha de cada entrega y las ventas por su fecha; lo anulado no cuenta.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Entrega, Estado, Lote, Recomendacion, Usuario, Venta
from app.schemas import FiltrosResumen, ResumenOut, ResumenRecomendaciones
from app.services import cola
from app.services import recomendaciones as recomendaciones_service
from app.services.lotes import visibles_para


def resumen(db: Session, usuario: Usuario, filtros: FiltrosResumen | None = None) -> ResumenOut:
    filtros = filtros or FiltrosResumen()
    if not usuario.es_admin:
        filtros.usuario_id = None

    def lotes(consulta):
        consulta = visibles_para(consulta, usuario).where(Lote.estado == Estado.VIGENTE)
        if filtros.usuario_id:
            consulta = consulta.where(Lote.usuario_id == filtros.usuario_id)
        if filtros.cultivo:
            consulta = consulta.where(Lote.cultivo.ilike(filtros.cultivo.strip()))
        return consulta

    def entregas(consulta):
        consulta = lotes(consulta.join(Lote, Entrega.lote_id == Lote.id)).where(Entrega.estado == Estado.VIGENTE)
        if filtros.desde:
            consulta = consulta.where(Entrega.fecha >= filtros.desde)
        if filtros.hasta:
            consulta = consulta.where(Entrega.fecha <= filtros.hasta)
        return consulta

    def ventas(consulta):
        consulta = lotes(consulta.join(Lote, Venta.lote_id == Lote.id)).where(Venta.estado == Estado.VIGENTE)
        if filtros.desde:
            consulta = consulta.where(Venta.fecha >= filtros.desde)
        if filtros.hasta:
            consulta = consulta.where(Venta.fecha <= filtros.hasta)
        return consulta

    kilos_cosechados = db.scalar(entregas(select(func.coalesce(func.sum(Entrega.kilos), 0)).select_from(Entrega)))
    kilos_vendidos = db.scalar(ventas(select(func.coalesce(func.sum(Venta.kilos), 0)).select_from(Venta)))
    por_cultivo = entregas(select(Lote.cultivo, func.sum(Entrega.kilos)).select_from(Entrega)).group_by(Lote.cultivo)
    con_periodo = filtros.desde or filtros.hasta
    total_lotes = (
        db.scalar(entregas(select(func.count(func.distinct(Lote.id))).select_from(Entrega)))
        if con_periodo else db.scalar(lotes(select(func.count(Lote.id))))
    )
    return ResumenOut(
        filtros=filtros,
        total_lotes=total_lotes,
        total_entregas=db.scalar(entregas(select(func.count(Entrega.id)).select_from(Entrega))),
        total_ventas=db.scalar(ventas(select(func.count(Venta.id)).select_from(Venta))),
        kilos_cosechados=kilos_cosechados,
        kilos_vendidos=kilos_vendidos,
        kilos_disponibles=kilos_cosechados - kilos_vendidos,
        ingresos=db.scalar(ventas(select(func.coalesce(func.sum(Venta.kilos * Venta.precio_por_kilo), 0)).select_from(Venta))),
        kilos_por_cultivo={cultivo: kilos for cultivo, kilos in db.execute(por_cultivo)},
        recomendaciones=_recomendaciones(db, usuario, filtros),
        cola=cola.resumen(db, usuario, filtros.usuario_id, filtros.desde, filtros.hasta),
    )


def _recomendaciones(db: Session, usuario: Usuario, filtros: FiltrosResumen) -> ResumenRecomendaciones:
    consulta = select(Recomendacion)
    if not usuario.es_admin:
        consulta = consulta.where(Recomendacion.usuario_id == usuario.id)
    elif filtros.usuario_id:
        consulta = consulta.where(Recomendacion.usuario_id == filtros.usuario_id)
    total = db.scalar(select(func.count()).select_from(consulta.subquery()))
    ultima = db.scalar(consulta.order_by(Recomendacion.creado.desc(), Recomendacion.id.desc()).limit(1))
    return ResumenRecomendaciones(total=total, ultima=recomendaciones_service.a_salida(ultima) if ultima else None)
