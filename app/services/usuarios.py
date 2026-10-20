"""Casos de uso de usuarios."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import CredencialesInvalidas, RecursoNoEncontrado, ReglaDeNegocioInvalida
from app.models import Rol, Usuario
from app.schemas import UsuarioUpdate
from app.services import claves


def crear(db: Session, nombre: str, email: str, clave: str, rol: Rol) -> Usuario:
    email = email.lower()
    if obtener_por_email(db, email) is not None:
        raise ReglaDeNegocioInvalida("Ya existe un usuario con ese correo")
    usuario = Usuario(nombre=nombre, email=email, clave_hash=claves.hashear(clave), rol=rol)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def listar(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.nombre)))


def actualizar(db: Session, usuario_id: int, cambios: UsuarioUpdate, admin: Usuario) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise RecursoNoEncontrado("Usuario no encontrado")
    if usuario.id == admin.id:
        raise ReglaDeNegocioInvalida("No puedes cambiar tu propio rol ni desactivarte")
    for campo, valor in cambios.model_dump(exclude_none=True).items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario


def obtener_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == email.lower()))


def autenticar(db: Session, email: str, clave: str) -> Usuario:
    usuario = obtener_por_email(db, email)
    if usuario is None or not usuario.activo or not claves.verificar(clave, usuario.clave_hash):
        raise CredencialesInvalidas("Correo o contraseña incorrectos")
    return usuario


def asegurar_admin_inicial(db: Session) -> None:
    """Crea el primer administrador desde ADMIN_EMAIL/ADMIN_CLAVE si la base no tiene usuarios."""
    hay_usuarios = db.scalar(select(func.count(Usuario.id))) > 0
    if hay_usuarios or not (settings.admin_email and settings.admin_clave):
        return
    crear(db, settings.admin_nombre, settings.admin_email, settings.admin_clave, Rol.ADMIN)
