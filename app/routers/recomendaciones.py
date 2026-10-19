from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import RecomendacionOut
from app.services import recomendaciones as recomendaciones_service
from app.services.ia import ProveedorIA, crear_proveedor

router = APIRouter(prefix="/lotes/{codigo}/recomendacion", tags=["recomendaciones"])


@router.get("", response_model=RecomendacionOut)
def recomendar(
    codigo: str,
    db: Session = Depends(get_db),
    proveedor: ProveedorIA = Depends(crear_proveedor),
):
    return RecomendacionOut(texto=recomendaciones_service.recomendar(db, codigo, proveedor))
