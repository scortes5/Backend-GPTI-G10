"""Casos de uso de ventas: cada venta descuenta kilos de un lote."""
from sqlalchemy.orm import Session

from app.exceptions import ReglaDeNegocioInvalida
from app.models import Lote, Venta
from app.schemas import VentaCreate
from app.services import lotes as lotes_service


def listar(db: Session, codigo_lote: str) -> list[Venta]:
    return lotes_service.obtener(db, codigo_lote).ventas


def registrar(db: Session, codigo_lote: str, data: VentaCreate) -> Venta:
    lote = lotes_service.obtener(db, codigo_lote)
    _validar_venta(lote, data)
    venta = Venta(**data.model_dump(), lote=lote)
    db.add(venta)
    db.commit()
    db.refresh(venta)
    return venta


def _validar_venta(lote: Lote, data: VentaCreate) -> None:
    if data.fecha < lote.fecha_cosecha:
        raise ReglaDeNegocioInvalida("La venta no puede ser anterior a la cosecha")
    if data.kilos > lote.kilos_disponibles:
        raise ReglaDeNegocioInvalida(
            f"Solo quedan {lote.kilos_disponibles:g} kg disponibles en el lote"
        )
