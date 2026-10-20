from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import solo_admin
from app.db import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.services import usuarios as usuarios_service

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioOut])
def listar(db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    return usuarios_service.listar(db)


@router.post("", response_model=UsuarioOut, status_code=201)
def crear(data: UsuarioCreate, db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    return usuarios_service.crear(db, data.nombre, data.email, data.clave, data.rol)


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def actualizar(
    usuario_id: int, cambios: UsuarioUpdate, db: Session = Depends(get_db), admin: Usuario = Depends(solo_admin)
):
    return usuarios_service.actualizar(db, usuario_id, cambios, admin)
