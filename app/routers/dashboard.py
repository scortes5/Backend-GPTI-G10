from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import usuario_actual
from app.db import get_db
from app.models import Usuario
from app.schemas import ResumenOut
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumen", response_model=ResumenOut)
def resumen(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return dashboard_service.resumen(db, usuario)
