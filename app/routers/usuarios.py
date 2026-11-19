from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import solo_admin
from app.db import get_db
from app.models import Usuario
from app.schemas import UsuarioCreadoOut, UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.services import usuarios as usuarios_service
from app.services.correo import ServicioCorreo, crear_servicio_correo

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioOut])
def listar(db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    return usuarios_service.listar(db)


@router.post("", response_model=UsuarioCreadoOut, status_code=201)
def crear(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(solo_admin),
    servicio: ServicioCorreo = Depends(crear_servicio_correo),
):
    """Crea el usuario (RUT validado) y le envía sus credenciales por correo."""
    usuario, enviado = usuarios_service.crear_y_avisar(db, data, servicio)
    return UsuarioCreadoOut.model_validate({**UsuarioOut.model_validate(usuario).model_dump(), "credenciales_enviadas": enviado})


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def actualizar(
    usuario_id: int, cambios: UsuarioUpdate, db: Session = Depends(get_db), admin: Usuario = Depends(solo_admin)
):
    """Nombre, correo, RUT, rol o acceso. El administrador no puede quitarse su propio rol ni acceso."""
    return usuarios_service.actualizar(db, usuario_id, cambios, admin)
