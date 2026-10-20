"""Casos de uso de lotes: la lógica vive aquí y no en los routers.

Regla de acceso: el administrador ve todos los lotes; un productor solo los suyos.
"""
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import AccesoDenegado, RecursoNoEncontrado, ReglaDeNegocioInvalida
from app.models import Lote, Usuario
from app.schemas import LoteCreate, LoteUpdate, TrazabilidadOut


def visibles_para(consulta: Select, usuario: Usuario) -> Select:
    """Restringe una consulta sobre Lote a los lotes que el usuario puede ver."""
    return consulta if usuario.es_admin else consulta.where(Lote.usuario_id == usuario.id)


def listar(db: Session, usuario: Usuario) -> list[Lote]:
    return list(db.scalars(visibles_para(select(Lote), usuario).order_by(Lote.creado.desc())))


def obtener_publico(db: Session, codigo: str) -> Lote:
    lote = db.scalar(select(Lote).where(Lote.codigo == codigo))
    if lote is None:
        raise RecursoNoEncontrado("Lote no encontrado")
    return lote


def obtener(db: Session, codigo: str, usuario: Usuario) -> Lote:
    lote = obtener_publico(db, codigo)
    if not usuario.es_admin and lote.usuario_id != usuario.id:
        raise AccesoDenegado("Este lote pertenece a otro productor")
    return lote


def url_trazabilidad(codigo: str) -> str:
    """Página pública del frontend a la que lleva el QR del lote."""
    return f"{settings.frontend_url}/Trazabilidad?codigo={codigo}"


def crear(db: Session, data: LoteCreate, usuario: Usuario) -> Lote:
    lote = Lote(**data.model_dump(), usuario_id=usuario.id)
    if not usuario.es_admin:
        lote.productor = usuario.nombre
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return lote


def actualizar(db: Session, codigo: str, cambios: LoteUpdate, usuario: Usuario) -> Lote:
    lote = obtener(db, codigo, usuario)
    campos = cambios.model_dump(exclude_none=True)
    if not usuario.es_admin:
        campos.pop("productor", None)
    for campo, valor in campos.items():
        setattr(lote, campo, valor)
    if lote.kilos_disponibles < 0:
        db.rollback()
        raise ReglaDeNegocioInvalida("Los kilos del lote no pueden ser menores a los ya vendidos")
    db.commit()
    db.refresh(lote)
    return lote


def eliminar(db: Session, codigo: str, usuario: Usuario) -> None:
    db.delete(obtener(db, codigo, usuario))
    db.commit()


def trazabilidad(db: Session, codigo: str, usuario: Usuario) -> TrazabilidadOut:
    lote = obtener(db, codigo, usuario)
    return TrazabilidadOut(
        lote=lote,
        kilos_vendidos=lote.kilos_vendidos,
        kilos_disponibles=lote.kilos_disponibles,
        ingresos=lote.ingresos,
        ventas=lote.ventas,
    )
