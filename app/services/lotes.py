"""Casos de uso de lotes y entregas: la lógica vive aquí y no en los routers.

Regla de acceso: el administrador ve todos los lotes; un productor solo los suyos.
Nada se borra: lotes, entregas y ventas se anulan con un motivo y quedan en el historial.
"""
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import AccesoDenegado, RecursoNoEncontrado, ReglaDeNegocioInvalida
from app.models import Entrega, Estado, Lote, Usuario
from app.schemas import EntregaCreate, LoteCreate, LoteUpdate, TrazabilidadOut
from app.services import historial

CAMPOS_EDITABLES = ("productor", "cultivo", "predio", "superficie_ha", "fecha_cosecha")


def visibles_para(consulta: Select, usuario: Usuario) -> Select:
    """Restringe una consulta sobre Lote a los lotes que el usuario puede ver."""
    return consulta if usuario.es_admin else consulta.where(Lote.usuario_id == usuario.id)


def listar(
    db: Session,
    usuario: Usuario,
    desde: date | None = None,
    hasta: date | None = None,
    estado: Estado | None = None,
    cultivo: str | None = None,
    usuario_id: int | None = None,
) -> list[Lote]:
    consulta = visibles_para(select(Lote), usuario)
    if desde:
        consulta = consulta.where(Lote.fecha_cosecha >= desde)
    if hasta:
        consulta = consulta.where(Lote.fecha_cosecha <= hasta)
    if estado:
        consulta = consulta.where(Lote.estado == estado)
    if cultivo:
        consulta = consulta.where(Lote.cultivo.ilike(cultivo.strip()))
    if usuario_id and usuario.es_admin:
        consulta = consulta.where(Lote.usuario_id == usuario_id)
    return list(db.scalars(consulta.order_by(Lote.creado.desc())))


def obtener_publico(db: Session, codigo: str) -> Lote:
    lote = db.scalar(select(Lote).where(Lote.codigo == codigo))
    if lote is None:
        raise RecursoNoEncontrado("Lote no encontrado")
    return lote


def obtener(db: Session, codigo: str, usuario: Usuario) -> Lote:
    lote = obtener_publico(db, codigo)
    if not usuario.es_admin and lote.usuario_id != usuario.id:
        raise AccesoDenegado("Este lote pertenece a otro productor")
    return lote


def obtener_vigente(db: Session, codigo: str, usuario: Usuario) -> Lote:
    lote = obtener(db, codigo, usuario)
    if lote.anulado:
        raise ReglaDeNegocioInvalida("El lote está anulado: no admite cambios")
    return lote


def url_trazabilidad(codigo: str) -> str:
    """Página pública del frontend a la que lleva el QR del lote."""
    return f"{settings.frontend_url}/Trazabilidad?codigo={codigo}"


def crear(db: Session, data: LoteCreate, usuario: Usuario) -> Lote:
    datos = data.model_dump()
    entrega = Entrega(fecha=datos.pop("fecha_cosecha"), kilos=datos.pop("kilos"), calidad=datos.pop("calidad"))
    lote = Lote(**datos, usuario_id=usuario.id, fecha_cosecha=entrega.fecha, kilos=entrega.kilos)
    if not usuario.es_admin:
        lote.productor = usuario.nombre
    lote.entregas.append(entrega)
    db.add(lote)
    db.flush()
    historial.registrar(db, lote, "lote", lote.id, "creado", usuario, _resumen_lote(lote))
    historial.registrar(db, lote, "entrega", entrega.id, "creado", usuario, _resumen_entrega(entrega))
    db.commit()
    db.refresh(lote)
    return lote


def actualizar(db: Session, codigo: str, cambios: LoteUpdate, usuario: Usuario) -> Lote:
    lote = obtener_vigente(db, codigo, usuario)
    campos = cambios.model_dump(exclude_unset=True, exclude={"motivo"})
    campos = {c: v for c, v in campos.items() if c in CAMPOS_EDITABLES and (v is not None or c in ("predio", "superficie_ha"))}
    if not usuario.es_admin:
        campos.pop("productor", None)
    antes = {campo: getattr(lote, campo) for campo in campos}
    for campo, valor in campos.items():
        setattr(lote, campo, valor)
    detalle = historial.diferencias(antes, campos)
    if detalle:
        historial.registrar(db, lote, "lote", lote.id, "editado", usuario, detalle, cambios.motivo)
    db.commit()
    db.refresh(lote)
    return lote


def anular(db: Session, codigo: str, motivo: str, usuario: Usuario) -> Lote:
    lote = obtener_vigente(db, codigo, usuario)
    if lote.ventas_vigentes:
        raise ReglaDeNegocioInvalida("El lote tiene ventas vigentes: anúlalas antes de anular el lote")
    lote.estado = Estado.ANULADO
    lote.motivo_anulacion = motivo
    historial.registrar(db, lote, "lote", lote.id, "anulado", usuario, motivo=motivo)
    db.commit()
    db.refresh(lote)
    return lote


def agregar_entrega(db: Session, codigo: str, data: EntregaCreate, usuario: Usuario) -> Entrega:
    lote = obtener_vigente(db, codigo, usuario)
    entrega = Entrega(**data.model_dump())
    lote.entregas.append(entrega)
    db.flush()
    _recalcular(lote)
    historial.registrar(db, lote, "entrega", entrega.id, "creado", usuario, _resumen_entrega(entrega))
    db.commit()
    db.refresh(entrega)
    return entrega


def anular_entrega(db: Session, codigo: str, entrega_id: int, motivo: str, usuario: Usuario) -> Entrega:
    lote = obtener_vigente(db, codigo, usuario)
    entrega = next((e for e in lote.entregas if e.id == entrega_id), None)
    if entrega is None:
        raise RecursoNoEncontrado("Entrega no encontrada")
    if entrega.estado == Estado.ANULADO:
        raise ReglaDeNegocioInvalida("La entrega ya estaba anulada")
    if len(lote.entregas_vigentes) == 1:
        raise ReglaDeNegocioInvalida("Es la única entrega del lote: registra la correcta antes de anularla, o anula el lote")
    if lote.kilos - entrega.kilos < lote.kilos_vendidos:
        raise ReglaDeNegocioInvalida("Sin esta entrega quedarían menos kilos que los ya vendidos")
    entrega.estado = Estado.ANULADO
    entrega.motivo_anulacion = motivo
    _recalcular(lote)
    historial.registrar(db, lote, "entrega", entrega.id, "anulado", usuario, _resumen_entrega(entrega), motivo)
    db.commit()
    db.refresh(entrega)
    return entrega


def trazabilidad(db: Session, codigo: str, usuario: Usuario) -> TrazabilidadOut:
    lote = obtener(db, codigo, usuario)
    return TrazabilidadOut(
        lote=lote,
        kilos_vendidos=lote.kilos_vendidos,
        kilos_disponibles=lote.kilos_disponibles,
        ingresos=lote.ingresos,
        entregas=lote.entregas,
        ventas=lote.ventas,
        historial=historial.del_lote(db, lote),
    )


def publico(db: Session, codigo: str) -> dict:
    lote = obtener_publico(db, codigo)
    return {
        "codigo": lote.codigo,
        "productor": lote.productor,
        "cultivo": lote.cultivo,
        "predio": lote.predio,
        "kilos": lote.kilos,
        "fecha_cosecha": lote.fecha_cosecha,
        "estado": lote.estado,
        "entregas": lote.entregas_vigentes,
    }


def _recalcular(lote: Lote) -> None:
    vigentes = lote.entregas_vigentes
    lote.kilos = sum(e.kilos for e in vigentes)
    if vigentes:
        lote.fecha_cosecha = min(e.fecha for e in vigentes)


def _resumen_lote(lote: Lote) -> str:
    partes = [lote.cultivo, lote.productor]
    if lote.predio:
        partes.append(f"predio {lote.predio}")
    if lote.superficie_ha:
        partes.append(f"{lote.superficie_ha:g} ha")
    return " · ".join(partes)


def _resumen_entrega(entrega: Entrega) -> str:
    return f"{entrega.kilos:g} kg, calidad {entrega.calidad.value}, {entrega.fecha:%d-%m-%Y}"
