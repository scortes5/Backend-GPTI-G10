"""Tokens de sesión (JWT firmados con SECRET_KEY)."""
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.exceptions import CredencialesInvalidas

_ALGORITMO = "HS256"
# Sin SECRET_KEY se usa una clave aleatoria: sirve en desarrollo, pero las sesiones se pierden al reiniciar.
_CLAVE = settings.secret_key or secrets.token_urlsafe(32)


def emitir(usuario_id: int) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=settings.token_minutos)
    return jwt.encode({"sub": str(usuario_id), "exp": expira}, _CLAVE, algorithm=_ALGORITMO)


def leer_usuario_id(token: str) -> int:
    try:
        datos = jwt.decode(token, _CLAVE, algorithms=[_ALGORITMO], options={"require": ["exp", "sub"]})
        return int(datos["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise CredencialesInvalidas("Sesión inválida o expirada") from error
