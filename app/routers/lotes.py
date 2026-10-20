from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import solo_admin, usuario_actual
from app.db import get_db
from app.models import Usuario
from app.schemas import LoteCreate, LoteOut, LoteUpdate, TrazabilidadOut
from app.services import lotes as lotes_service
from app.services import qr as qr_service

router = APIRouter(prefix="/lotes", tags=["lotes"])


@router.get("", response_model=list[LoteOut])
def listar(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return lotes_service.listar(db, usuario)


@router.post("", response_model=LoteOut, status_code=201)
def crear(data: LoteCreate, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return lotes_service.crear(db, data, usuario)


@router.get("/{codigo}", response_model=LoteOut)
def obtener(codigo: str, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return lotes_service.obtener(db, codigo, usuario)


@router.get("/{codigo}/trazabilidad", response_model=TrazabilidadOut)
def trazabilidad(codigo: str, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return lotes_service.trazabilidad(db, codigo, usuario)


@router.patch("/{codigo}", response_model=LoteOut)
def actualizar(
    codigo: str, cambios: LoteUpdate, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)
):
    return lotes_service.actualizar(db, codigo, cambios, usuario)


@router.delete("/{codigo}", status_code=204)
def eliminar(codigo: str, db: Session = Depends(get_db), admin: Usuario = Depends(solo_admin)):
    lotes_service.eliminar(db, codigo, admin)
    return Response(status_code=204)


@router.get("/{codigo}/qr")
def qr(codigo: str, db: Session = Depends(get_db)):
    """Público: el QR solo contiene la URL de la ficha pública."""
    lote = lotes_service.obtener_publico(db, codigo)
    return StreamingResponse(qr_service.generar_png(lotes_service.url_trazabilidad(lote.codigo)), media_type="image/png")
