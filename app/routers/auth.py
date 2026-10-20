from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth import token_actual, usuario_actual
from app.db import get_db
from app.models import Usuario
from app.schemas import Credenciales, Mensaje, Restablecimiento, SesionOut, SolicitudRecuperacion, UsuarioOut
from app.services import recuperacion, sesiones, tokens
from app.services import usuarios as usuarios_service
from app.services.correo import ServicioCorreo, crear_servicio_correo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SesionOut)
def login(credenciales: Credenciales, db: Session = Depends(get_db)):
    usuario = usuarios_service.autenticar(db, credenciales.email, credenciales.clave)
    return SesionOut(access_token=tokens.emitir(usuario.id), usuario=usuario)


@router.get("/yo", response_model=UsuarioOut)
def yo(usuario: Usuario = Depends(usuario_actual)):
    return usuario


@router.post("/logout", status_code=204)
def logout(token: tokens.DatosToken = Depends(token_actual), db: Session = Depends(get_db)):
    sesiones.revocar(db, token)
    return Response(status_code=204)


@router.post("/recuperar", response_model=Mensaje, status_code=202)
def recuperar(
    solicitud: SolicitudRecuperacion,
    db: Session = Depends(get_db),
    servicio: ServicioCorreo = Depends(crear_servicio_correo),
):
    recuperacion.solicitar(db, solicitud.email, servicio)
    return Mensaje(detail="Si el correo está registrado, te enviamos un código de 6 dígitos.")


@router.post("/restablecer", status_code=204)
def restablecer(datos: Restablecimiento, db: Session = Depends(get_db)):
    recuperacion.restablecer(db, datos.email, datos.codigo, datos.clave_nueva)
    return Response(status_code=204)
