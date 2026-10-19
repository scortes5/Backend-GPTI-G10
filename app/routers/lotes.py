from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import LoteCreate, LoteOut, LoteUpdate
from app.services import lotes as lotes_service
from app.services import qr as qr_service

router = APIRouter(prefix="/lotes", tags=["lotes"])


@router.get("", response_model=list[LoteOut])
def listar(db: Session = Depends(get_db)):
    return lotes_service.listar(db)


@router.post("", response_model=LoteOut, status_code=201)
def crear(data: LoteCreate, db: Session = Depends(get_db)):
    return lotes_service.crear(db, data)


@router.get("/{codigo}", response_model=LoteOut)
def obtener(codigo: str, db: Session = Depends(get_db)):
    return lotes_service.obtener(db, codigo)


@router.patch("/{codigo}", response_model=LoteOut)
def actualizar(codigo: str, cambios: LoteUpdate, db: Session = Depends(get_db)):
    return lotes_service.actualizar(db, codigo, cambios)


@router.delete("/{codigo}", status_code=204)
def eliminar(codigo: str, db: Session = Depends(get_db)):
    lotes_service.eliminar(db, codigo)
    return Response(status_code=204)


@router.get("/{codigo}/qr")
def qr(codigo: str, db: Session = Depends(get_db)):
    lote = lotes_service.obtener(db, codigo)
    return StreamingResponse(qr_service.generar_png(lote.codigo), media_type="image/png")
