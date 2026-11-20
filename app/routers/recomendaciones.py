from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import usuario_actual
from app.db import get_db
from app.models import Usuario
from app.schemas import RecomendacionOut
from app.services import recomendaciones as recomendaciones_service
from app.services.ia import ProveedorIA, crear_proveedor

router = APIRouter(tags=["recomendaciones"])


@router.get("/lotes/{codigo}/recomendacion", response_model=RecomendacionOut)
def recomendar(
    codigo: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
    proveedor: ProveedorIA = Depends(crear_proveedor),
):
    """Genera una sugerencia, la guarda en el historial y muestra los datos que se usaron."""
    return recomendaciones_service.recomendar(db, codigo, usuario, proveedor)


@router.get("/lotes/{codigo}/recomendaciones", response_model=list[RecomendacionOut])
def historial_lote(codigo: str, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return recomendaciones_service.historial(db, usuario, codigo)


@router.get("/recomendaciones", response_model=list[RecomendacionOut])
def historial(limite: int = 20, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Las propias (productor) o de toda la cooperativa (administrador), de la más reciente a la más antigua."""
    return recomendaciones_service.historial(db, usuario, limite=max(1, min(limite, 100)))
