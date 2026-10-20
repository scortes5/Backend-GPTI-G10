"""Dependencias de FastAPI para autenticación y autorización por rol."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.exceptions import AccesoDenegado, CredencialesInvalidas
from app.models import Usuario
from app.services import sesiones, tokens

_bearer = HTTPBearer(auto_error=False)


def token_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> tokens.DatosToken:
    if credenciales is None:
        raise CredencialesInvalidas("Debes iniciar sesión")
    token = tokens.leer(credenciales.credentials)
    if sesiones.esta_revocado(db, token):
        raise CredencialesInvalidas("Sesión cerrada. Vuelve a iniciar sesión")
    return token


def usuario_actual(token: tokens.DatosToken = Depends(token_actual), db: Session = Depends(get_db)) -> Usuario:
    usuario = db.get(Usuario, token.usuario_id)
    if usuario is None or not usuario.activo:
        raise CredencialesInvalidas("Sesión inválida o expirada")
    if usuario.sesiones_desde and token.emitido < usuario.sesiones_desde:
        raise CredencialesInvalidas("Tu contraseña cambió. Vuelve a iniciar sesión")
    return usuario


def solo_admin(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    if not usuario.es_admin:
        raise AccesoDenegado("Solo un administrador puede realizar esta acción")
    return usuario
