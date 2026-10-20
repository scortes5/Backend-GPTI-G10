"""Dependencias de FastAPI para autenticación y autorización por rol."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.exceptions import AccesoDenegado, CredencialesInvalidas
from app.models import Usuario
from app.services import tokens

_bearer = HTTPBearer(auto_error=False)


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credenciales is None:
        raise CredencialesInvalidas("Debes iniciar sesión")
    usuario = db.get(Usuario, tokens.leer_usuario_id(credenciales.credentials))
    if usuario is None or not usuario.activo:
        raise CredencialesInvalidas("Sesión inválida o expirada")
    return usuario


def solo_admin(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    if not usuario.es_admin:
        raise AccesoDenegado("Solo un administrador puede realizar esta acción")
    return usuario
