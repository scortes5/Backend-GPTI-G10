"""Recuperación de contraseña con un código de 6 dígitos enviado por correo.

Las respuestas nunca revelan si un correo está registrado. El código vence a los 15 minutos,
sirve una sola vez, se guarda hasheado y se anula tras 5 intentos fallidos.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.exceptions import CodigoInvalido, ServicioExternoNoDisponible
from app.models import CodigoRecuperacion, Usuario
from app.services import claves
from app.services import usuarios as usuarios_service
from app.services.correo import Correo, ServicioCorreo
from app.services.intentos import LimitadorIntentos, limitador_login

MINUTOS_VIGENCIA = 15
MAX_INTENTOS_POR_CODIGO = 5
logger = logging.getLogger("agrotracker.recuperacion")
# Máximo 3 correos de recuperación por dirección cada 15 minutos (evita usar la API para hacer spam).
limitador_solicitudes = LimitadorIntentos(max_fallos=3)


def solicitar(db: Session, email: str, servicio: ServicioCorreo) -> None:
    email = email.lower()
    if limitador_solicitudes.bloqueado(email):
        return
    limitador_solicitudes.registrar_fallo(email)
    usuario = usuarios_service.obtener_por_email(db, email)
    if usuario is None or not usuario.activo:
        return

    codigo = f"{secrets.randbelow(10**6):06d}"
    _anular_codigos_anteriores(db, usuario)
    db.add(
        CodigoRecuperacion(
            usuario_id=usuario.id,
            codigo_hash=claves.hashear(codigo),
            expira=_ahora_utc() + timedelta(minutes=MINUTOS_VIGENCIA),
        )
    )
    db.commit()
    try:
        servicio.enviar(_correo_con_codigo(usuario, codigo))
    except ServicioExternoNoDisponible:
        # Se registra pero no se informa al cliente: un error solo para correos existentes los delataría.
        logger.exception("No se pudo enviar el código de recuperación a %s", email)


def restablecer(db: Session, email: str, codigo: str, clave_nueva: str) -> None:
    usuario = usuarios_service.obtener_por_email(db, email)
    vigente = _codigo_vigente(db, usuario) if usuario else None
    codigo_valido = claves.verificar(codigo, vigente.codigo_hash if vigente else claves.HASH_SENUELO)

    if vigente is None:
        raise CodigoInvalido("Código inválido o vencido")
    if not codigo_valido:
        vigente.intentos += 1
        vigente.usado = vigente.intentos >= MAX_INTENTOS_POR_CODIGO
        db.commit()
        raise CodigoInvalido("Código inválido o vencido")

    usuario.clave_hash = claves.hashear(clave_nueva)
    usuario.sesiones_desde = _ahora_utc().replace(microsecond=0)
    vigente.usado = True
    db.commit()
    limitador_login.limpiar(usuario.email)


def _codigo_vigente(db: Session, usuario: Usuario) -> CodigoRecuperacion | None:
    return db.scalar(
        select(CodigoRecuperacion)
        .where(
            CodigoRecuperacion.usuario_id == usuario.id,
            CodigoRecuperacion.usado.is_(False),
            CodigoRecuperacion.expira > _ahora_utc(),
        )
        .order_by(CodigoRecuperacion.id.desc())
    )


def _anular_codigos_anteriores(db: Session, usuario: Usuario) -> None:
    db.execute(
        update(CodigoRecuperacion)
        .where(CodigoRecuperacion.usuario_id == usuario.id, CodigoRecuperacion.usado.is_(False))
        .values(usado=True)
    )


def _correo_con_codigo(usuario: Usuario, codigo: str) -> Correo:
    return Correo(
        destinatario=usuario.email,
        asunto="Código para recuperar tu contraseña de AgroTracker",
        cuerpo=(
            f"Hola {usuario.nombre}:\n\n"
            f"Tu código para crear una nueva contraseña es: {codigo}\n\n"
            f"Vence en {MINUTOS_VIGENCIA} minutos y sirve una sola vez. "
            "Si no lo pediste, ignora este correo: tu contraseña no cambia.\n"
        ),
    )


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
