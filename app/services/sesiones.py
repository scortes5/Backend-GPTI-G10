"""Revocación de tokens: al cerrar sesión el token deja de servir aunque no haya expirado."""
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import TokenRevocado
from app.services.tokens import DatosToken


def revocar(db: Session, token: DatosToken) -> None:
    db.execute(delete(TokenRevocado).where(TokenRevocado.expira < _ahora_utc()))
    db.merge(TokenRevocado(jti=token.jti, expira=token.expira))
    db.commit()


def esta_revocado(db: Session, token: DatosToken) -> bool:
    return db.scalar(select(TokenRevocado.jti).where(TokenRevocado.jti == token.jti)) is not None


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
