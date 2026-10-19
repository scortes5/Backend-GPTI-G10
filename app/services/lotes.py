"""Casos de uso de lotes: la lógica vive aquí y no en los routers."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import RecursoNoEncontrado, ReglaDeNegocioInvalida
from app.models import Lote
from app.schemas import LoteCreate, LoteUpdate


def listar(db: Session) -> list[Lote]:
    return list(db.scalars(select(Lote).order_by(Lote.creado.desc())))


def obtener(db: Session, codigo: str) -> Lote:
    lote = db.scalar(select(Lote).where(Lote.codigo == codigo))
    if lote is None:
        raise RecursoNoEncontrado("Lote no encontrado")
    return lote


def crear(db: Session, data: LoteCreate) -> Lote:
    lote = Lote(**data.model_dump())
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return lote


def actualizar(db: Session, codigo: str, cambios: LoteUpdate) -> Lote:
    lote = obtener(db, codigo)
    for campo, valor in cambios.model_dump(exclude_none=True).items():
        setattr(lote, campo, valor)
    if lote.kilos_disponibles < 0:
        db.rollback()
        raise ReglaDeNegocioInvalida("Los kilos del lote no pueden ser menores a los ya vendidos")
    db.commit()
    db.refresh(lote)
    return lote


def eliminar(db: Session, codigo: str) -> None:
    db.delete(obtener(db, codigo))
    db.commit()
