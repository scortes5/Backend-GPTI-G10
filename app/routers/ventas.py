from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import usuario_actual
from app.db import get_db
from app.models import Usuario
from app.schemas import Anulacion, VentaCreate, VentaOut
from app.services import cola
from app.services import lotes as lotes_service
from app.services import ventas as ventas_service

router = APIRouter(prefix="/lotes/{codigo}/ventas", tags=["ventas"])


@router.get("", response_model=list[VentaOut])
def listar(codigo: str, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return ventas_service.listar(db, codigo, usuario)


@router.post("", response_model=VentaOut, status_code=201)
def registrar(
    codigo: str,
    data: VentaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
    evento: cola.Evento | None = Depends(cola.evento_de_cabeceras),
):
    previo = cola.ya_recibido(db, evento, usuario)
    if previo:  # reintento de la cola: la venta ya se registró, no se descuenta dos veces
        lote = lotes_service.obtener(db, codigo, usuario)
        return next(v for v in lote.ventas if str(v.id) == previo.recurso)
    venta = ventas_service.registrar(db, codigo, data, usuario)
    cola.registrar(db, evento, "venta", str(venta.id), usuario)
    return venta


@router.post("/{venta_id}/anular", response_model=VentaOut)
def anular(
    codigo: str, venta_id: int, datos: Anulacion, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)
):
    """Las ventas no se eliminan: se anulan con un motivo y sus kilos vuelven a estar disponibles."""
    return ventas_service.anular(db, codigo, venta_id, datos.motivo, usuario)
