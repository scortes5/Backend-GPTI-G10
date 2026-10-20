from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import usuario_actual
from app.db import get_db
from app.models import Usuario
from app.schemas import Credenciales, SesionOut, UsuarioOut
from app.services import tokens
from app.services import usuarios as usuarios_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SesionOut)
def login(credenciales: Credenciales, db: Session = Depends(get_db)):
    usuario = usuarios_service.autenticar(db, credenciales.email, credenciales.clave)
    return SesionOut(access_token=tokens.emitir(usuario.id), usuario=usuario)


@router.get("/yo", response_model=UsuarioOut)
def yo(usuario: Usuario = Depends(usuario_actual)):
    return usuario
