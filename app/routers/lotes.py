from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.auth import usuario_actual
from app.db import get_db
from app.models import Estado, Usuario
from app.schemas import Anulacion, EntregaCreate, EntregaOut, LoteCreate, LoteOut, LoteUpdate, TrazabilidadOut
from app.services import cola
from app.services import lotes as lotes_service
from app.services import qr as qr_service
from app.services import reportes as reportes_service

router = APIRouter(prefix="/lotes", tags=["lotes"])


@router.get("", response_model=list[LoteOut])
def listar(
    desde: date | None = None,
    hasta: date | None = None,
    estado: Estado | None = None,
    cultivo: str | None = None,
    usuario_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """Filtros por fecha de cosecha, estado, cultivo y socio (este último, solo administrador)."""
    return lotes_service.listar(db, usuario, desde, hasta, estado, cultivo, usuario_id)


@router.post("", response_model=LoteOut, status_code=201)
def crear(
    data: LoteCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
    evento: cola.Evento | None = Depends(cola.evento_de_cabeceras),
):
    previo = cola.ya_recibido(db, evento, usuario)
    if previo:  # reintento de la cola: el lote ya existe
        return lotes_service.obtener(db, previo.recurso, usuario)
    lote = lotes_service.crear(db, data, usuario)
    cola.registrar(db, evento, "lote", lote.codigo, usuario)
    return lote


@router.get("/{codigo}", response_model=LoteOut)
def obtener(codigo: str, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return lotes_service.obtener(db, codigo, usuario)


@router.get("/{codigo}/trazabilidad", response_model=TrazabilidadOut)
def trazabilidad(codigo: str, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Lote con entregas, ventas e historial de cambios."""
    return lotes_service.trazabilidad(db, codigo, usuario)


@router.patch("/{codigo}", response_model=LoteOut)
def actualizar(
    codigo: str,
    cambios: LoteUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
    evento: cola.Evento | None = Depends(cola.evento_de_cabeceras),
):
    """Exige un motivo: queda en el historial con el usuario y la fecha."""
    if cola.ya_recibido(db, evento, usuario):
        return lotes_service.obtener(db, codigo, usuario)
    lote = lotes_service.actualizar(db, codigo, cambios, usuario)
    cola.registrar(db, evento, "lote-editar", lote.codigo, usuario)
    return lote


@router.post("/{codigo}/anular", response_model=LoteOut)
def anular(codigo: str, datos: Anulacion, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Los lotes no se eliminan: quedan anulados, con su motivo, y dejan de contar en los indicadores."""
    return lotes_service.anular(db, codigo, datos.motivo, usuario)


@router.post("/{codigo}/entregas", response_model=EntregaOut, status_code=201)
def agregar_entrega(
    codigo: str,
    data: EntregaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
    evento: cola.Evento | None = Depends(cola.evento_de_cabeceras),
):
    previo = cola.ya_recibido(db, evento, usuario)
    if previo:
        lote = lotes_service.obtener(db, codigo, usuario)
        return next(e for e in lote.entregas if str(e.id) == previo.recurso)
    entrega = lotes_service.agregar_entrega(db, codigo, data, usuario)
    cola.registrar(db, evento, "entrega", str(entrega.id), usuario)
    return entrega


@router.post("/{codigo}/entregas/{entrega_id}/anular", response_model=EntregaOut)
def anular_entrega(
    codigo: str, entrega_id: int, datos: Anulacion, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)
):
    return lotes_service.anular_entrega(db, codigo, entrega_id, datos.motivo, usuario)


@router.get("/{codigo}/reporte.pdf")
def reporte_pdf(codigo: str, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    traza = lotes_service.trazabilidad(db, codigo, usuario)
    return Response(
        reportes_service.pdf(traza),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="lote_{traza.lote.codigo}.pdf"'},
    )


@router.get("/{codigo}/reporte.csv")
def reporte_csv(codigo: str, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    traza = lotes_service.trazabilidad(db, codigo, usuario)
    return Response(
        reportes_service.csv_completo(traza),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="lote_{traza.lote.codigo}.csv"'},
    )


@router.get("/{codigo}/qr")
def qr(codigo: str, db: Session = Depends(get_db)):
    """Público: el QR solo contiene la URL de la ficha pública."""
    lote = lotes_service.obtener_publico(db, codigo)
    return StreamingResponse(qr_service.generar_png(lotes_service.url_trazabilidad(lote.codigo)), media_type="image/png")
