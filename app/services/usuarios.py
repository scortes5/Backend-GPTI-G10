"""Casos de uso de usuarios."""
import logging
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import CredencialesInvalidas, DemasiadosIntentos, RecursoNoEncontrado, ReglaDeNegocioInvalida
from app.models import Rol, Usuario
from app.schemas import UsuarioCreate, UsuarioUpdate
from app.services import claves
from app.services.correo import Correo, ServicioCorreo
from app.exceptions import ServicioExternoNoDisponible
from app.services.intentos import limitador_login

CLAVE_ADMIN_MINIMA = 12
logger = logging.getLogger("agrotracker.usuarios")


def crear(db: Session, nombre: str, email: str, clave: str, rol: Rol, rut: str | None = None) -> Usuario:
    email = email.lower()
    if obtener_por_email(db, email) is not None:
        raise ReglaDeNegocioInvalida("Ya existe un usuario con ese correo")
    _rut_disponible(db, rut)
    usuario = Usuario(nombre=nombre, email=email, rut=rut, clave_hash=claves.hashear(clave), rol=rol)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def crear_y_avisar(db: Session, data: UsuarioCreate, servicio: ServicioCorreo) -> tuple[Usuario, bool]:
    """Crea el usuario y le envía sus credenciales. Si el correo falla, el usuario igual queda creado."""
    clave = data.clave or _clave_aleatoria()
    usuario = crear(db, data.nombre, data.email, clave, data.rol, data.rut)
    try:
        servicio.enviar(_correo_bienvenida(usuario, clave))
    except ServicioExternoNoDisponible:
        logger.exception("No se pudieron enviar las credenciales a %s", usuario.email)
        return usuario, False
    return usuario, True


def listar(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.nombre)))


def actualizar(db: Session, usuario_id: int, cambios: UsuarioUpdate, admin: Usuario) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise RecursoNoEncontrado("Usuario no encontrado")
    campos = cambios.model_dump(exclude_none=True)
    if usuario.id == admin.id and (campos.get("rol", usuario.rol) != usuario.rol or campos.get("activo") is False):
        raise ReglaDeNegocioInvalida("No puedes cambiar tu propio rol ni desactivarte")
    if "email" in campos:
        campos["email"] = campos["email"].lower()
        otro = obtener_por_email(db, campos["email"])
        if otro is not None and otro.id != usuario.id:
            raise ReglaDeNegocioInvalida("Ya existe un usuario con ese correo")
    if campos.get("rut") and campos["rut"] != usuario.rut:
        _rut_disponible(db, campos["rut"])
    for campo, valor in campos.items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario


def obtener_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == email.lower()))


def autenticar(db: Session, email: str, clave: str) -> Usuario:
    email = email.lower()
    if limitador_login.bloqueado(email):
        raise DemasiadosIntentos("Demasiados intentos fallidos. Espera 15 minutos e inténtalo de nuevo.")
    usuario = obtener_por_email(db, email)
    clave_valida = claves.verificar(clave, usuario.clave_hash if usuario else claves.HASH_SENUELO)
    if usuario is None or not usuario.activo or not clave_valida:
        limitador_login.registrar_fallo(email)
        raise CredencialesInvalidas("Correo o contraseña incorrectos")
    limitador_login.limpiar(email)
    return usuario


def asegurar_admin_inicial(db: Session) -> None:
    """Crea el primer administrador desde ADMIN_EMAIL/ADMIN_CLAVE si la base no tiene usuarios."""
    hay_usuarios = db.scalar(select(func.count(Usuario.id))) > 0
    if hay_usuarios or not (settings.admin_email and settings.admin_clave):
        return
    if len(settings.admin_clave) < CLAVE_ADMIN_MINIMA:
        logger.warning("ADMIN_CLAVE tiene menos de %d caracteres: no se crea el administrador", CLAVE_ADMIN_MINIMA)
        return
    crear(db, settings.admin_nombre, settings.admin_email, settings.admin_clave, Rol.ADMIN)


def _rut_disponible(db: Session, rut: str | None) -> None:
    if rut and db.scalar(select(Usuario.id).where(Usuario.rut == rut)) is not None:
        raise ReglaDeNegocioInvalida("Ya existe un usuario con ese RUT")


def _clave_aleatoria() -> str:
    # Sin caracteres que se confunden al leerlos (0/O, 1/l/I).
    alfabeto = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(10))


def _correo_bienvenida(usuario: Usuario, clave: str) -> Correo:
    return Correo(
        destinatario=usuario.email,
        asunto="Tu cuenta de AgroTracker",
        cuerpo=(
            f"Hola {usuario.nombre}:\n\n"
            "La Cooperativa Newen al Sur creó tu cuenta en AgroTracker.\n\n"
            f"Correo: {usuario.email}\n"
            f"Contraseña inicial: {clave}\n\n"
            f"Entra en {settings.frontend_url}/login. Te recomendamos cambiar la contraseña con la opción "
            "«¿Olvidaste tu contraseña?» la primera vez que entres.\n"
        ),
    )
