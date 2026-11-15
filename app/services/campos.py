"""Campo (ubicación) de cada usuario. Un usuario tiene a lo más un campo."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import AccesoDenegado, RecursoNoEncontrado
from app.models import Campo, Usuario
from app.schemas import CampoIn, CampoOut


def a_salida(campo: Campo) -> CampoOut:
    return CampoOut(
        usuario_id=campo.usuario_id,
        productor=campo.usuario.nombre,
        nombre=campo.nombre,
        latitud=campo.latitud,
        longitud=campo.longitud,
        actualizado=campo.actualizado,
    )


def obtener(db: Session, usuario: Usuario, usuario_id: int | None = None) -> Campo:
    """El campo propio; un administrador puede pedir el de otro usuario con usuario_id."""
    objetivo = usuario.id if usuario_id is None else usuario_id
    if objetivo != usuario.id and not usuario.es_admin:
        raise AccesoDenegado("Solo puedes ver tu propio campo")
    campo = db.scalar(select(Campo).where(Campo.usuario_id == objetivo))
    if campo is None:
        raise RecursoNoEncontrado("Aún no hay un campo registrado")
    return campo


def guardar(db: Session, usuario: Usuario, datos: CampoIn) -> Campo:
    campo = db.scalar(select(Campo).where(Campo.usuario_id == usuario.id))
    if campo is None:
        campo = Campo(usuario_id=usuario.id)
        db.add(campo)
    campo.nombre = datos.nombre
    campo.latitud = datos.latitud
    campo.longitud = datos.longitud
    db.commit()
    db.refresh(campo)
    return campo


def listar(db: Session) -> list[Campo]:
    return list(db.scalars(select(Campo).join(Campo.usuario).order_by(Usuario.nombre)))
