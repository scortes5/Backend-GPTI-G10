from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import LotePublicoOut
from app.services import lotes as lotes_service

router = APIRouter(prefix="/publico", tags=["público"])


@router.get("/lotes/{codigo}", response_model=LotePublicoOut)
def lote_publico(codigo: str, db: Session = Depends(get_db)):
    """Ficha de origen que se abre al escanear el QR, sin iniciar sesión."""
    return lotes_service.obtener_publico(db, codigo)
