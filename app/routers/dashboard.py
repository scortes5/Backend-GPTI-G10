from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import usuario_actual
from app.db import get_db
from app.models import Usuario
from app.schemas import FiltrosResumen, ResumenOut
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumen", response_model=ResumenOut)
def resumen(
    desde: date | None = None,
    hasta: date | None = None,
    usuario_id: int | None = None,
    cultivo: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """Indicadores del período. `usuario_id` (un socio) solo lo usa el administrador."""
    filtros = FiltrosResumen(desde=desde, hasta=hasta, usuario_id=usuario_id, cultivo=cultivo or None)
    return dashboard_service.resumen(db, usuario, filtros)
