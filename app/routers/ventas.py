from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import usuario_actual
from app.db import get_db
from app.models import Usuario
from app.schemas import VentaCreate, VentaOut
from app.services import ventas as ventas_service

router = APIRouter(prefix="/lotes/{codigo}/ventas", tags=["ventas"])


@router.get("", response_model=list[VentaOut])
def listar(codigo: str, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return ventas_service.listar(db, codigo, usuario)


@router.post("", response_model=VentaOut, status_code=201)
def registrar(
    codigo: str, data: VentaCreate, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)
):
    return ventas_service.registrar(db, codigo, data, usuario)
