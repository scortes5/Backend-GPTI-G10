from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ResumenOut
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumen", response_model=ResumenOut)
def resumen(db: Session = Depends(get_db)):
    return dashboard_service.resumen(db)
