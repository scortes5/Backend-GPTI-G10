"""Tokens de sesión (JWT firmados con SECRET_KEY)."""
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.exceptions import CredencialesInvalidas

_ALGORITMO = "HS256"
# Sin SECRET_KEY se usa una clave aleatoria: sirve en desarrollo, pero las sesiones se pierden al reiniciar.
_CLAVE = settings.secret_key or secrets.token_urlsafe(32)


@dataclass(frozen=True)
class DatosToken:
    usuario_id: int
    jti: str  # identificador único del token, para poder revocarlo al cerrar sesión
    expira: datetime  # UTC sin zona horaria, como se guarda en la base


def emitir(usuario_id: int) -> str:
    ahora = datetime.now(timezone.utc)
    datos = {
        "sub": str(usuario_id),
        "jti": secrets.token_urlsafe(16),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.token_minutos),
    }
    return jwt.encode(datos, _CLAVE, algorithm=_ALGORITMO)


def leer(token: str) -> DatosToken:
    try:
        datos = jwt.decode(token, _CLAVE, algorithms=[_ALGORITMO], options={"require": ["exp", "sub", "jti"]})
        return DatosToken(
            usuario_id=int(datos["sub"]),
            jti=datos["jti"],
            expira=datetime.fromtimestamp(datos["exp"], timezone.utc).replace(tzinfo=None),
        )
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise CredencialesInvalidas("Sesión inválida o expirada") from error
