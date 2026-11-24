"""Casos de uso de ventas: cada venta descuenta kilos de un lote. Se anulan, no se borran."""
from sqlalchemy.orm import Session

from app.exceptions import RecursoNoEncontrado, ReglaDeNegocioInvalida
from app.models import Estado, Lote, Usuario, Venta
from app.schemas import VentaCreate
from app.services import historial
from app.services import lotes as lotes_service


def listar(db: Session, codigo_lote: str, usuario: Usuario) -> list[Venta]:
    return lotes_service.obtener(db, codigo_lote, usuario).ventas


def registrar(db: Session, codigo_lote: str, data: VentaCreate, usuario: Usuario) -> Venta:
    lote = lotes_service.obtener_vigente(db, codigo_lote, usuario)
    _validar_venta(lote, data)
    venta = Venta(**data.model_dump(), lote=lote)
    db.add(venta)
    db.flush()
    historial.registrar(db, lote, "venta", venta.id, "creado", usuario, _resumen(venta))
    db.commit()
    db.refresh(venta)
    return venta


def anular(db: Session, codigo_lote: str, venta_id: int, motivo: str, usuario: Usuario) -> Venta:
    lote = lotes_service.obtener(db, codigo_lote, usuario)
    venta = next((v for v in lote.ventas if v.id == venta_id), None)
    if venta is None:
        raise RecursoNoEncontrado("Venta no encontrada")
    if venta.estado == Estado.ANULADO:
        raise ReglaDeNegocioInvalida("La venta ya estaba anulada")
    venta.estado = Estado.ANULADO
    venta.motivo_anulacion = motivo
    historial.registrar(db, lote, "venta", venta.id, "anulado", usuario, _resumen(venta), motivo)
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


def _resumen(venta: Venta) -> str:
    return f"{venta.kilos:g} kg a {venta.comprador} por ${venta.total:,.0f}".replace(",", ".")
