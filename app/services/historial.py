"""Registro de cambios de un lote y de sus entregas y ventas (auditoría, sin borrado físico)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Cambio, Lote, Usuario


def registrar(
    db: Session,
    lote: Lote,
    entidad: str,
    entidad_id: int,
    accion: str,
    usuario: Usuario,
    detalle: str = "",
    motivo: str | None = None,
) -> None:
    db.add(
        Cambio(
            lote_id=lote.id,
            entidad=entidad,
            entidad_id=entidad_id,
            accion=accion,
            detalle=detalle,
            motivo=motivo,
            usuario_id=usuario.id,
            usuario_nombre=usuario.nombre,
        )
    )


NOMBRES = {"superficie_ha": "superficie (ha)", "fecha_cosecha": "fecha de cosecha"}
ACCIONES = {"creado": "registrad", "editado": "editad", "anulado": "anulad"}


def titulo(entidad: str, accion: str) -> str:
    """'Entrega registrada', 'Lote editado', 'Venta anulada'."""
    final = "o" if entidad == "lote" else "a"
    return f"{entidad.capitalize()} {ACCIONES.get(accion, accion)}{final}" if accion in ACCIONES else f"{entidad.capitalize()} {accion}"


def diferencias(antes: dict, despues: dict) -> str:
    """'cultivo: Papa → Ajo; predio: — → El Roble' con solo los campos que cambiaron."""
    partes = []
    for campo, nuevo in despues.items():
        viejo = antes.get(campo)
        if viejo != nuevo:
            partes.append(f"{NOMBRES.get(campo, campo)}: {_texto(viejo)} → {_texto(nuevo)}")
    return "; ".join(partes)


def del_lote(db: Session, lote: Lote) -> list[Cambio]:
    return list(db.scalars(select(Cambio).where(Cambio.lote_id == lote.id).order_by(Cambio.fecha, Cambio.id)))


def _texto(valor) -> str:
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, date):
        return valor.strftime("%d-%m-%Y")
    if isinstance(valor, float):
        return f"{valor:g}"
    return str(getattr(valor, "value", valor))
