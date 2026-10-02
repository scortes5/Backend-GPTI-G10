from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Lote
from app.schemas import LoteCreate, LoteOut

router = APIRouter(prefix="/lotes", tags=["lotes"])


def _get_or_404(db: Session, codigo: str) -> Lote:
    lote = db.scalar(select(Lote).where(Lote.codigo == codigo))
    if lote is None:
        raise HTTPException(404, "Lote no encontrado")
    return lote


@router.get("", response_model=list[LoteOut])
def listar(db: Session = Depends(get_db)):
    return db.scalars(select(Lote).order_by(Lote.creado.desc())).all()


@router.post("", response_model=LoteOut, status_code=201)
def crear(data: LoteCreate, db: Session = Depends(get_db)):
    lote = Lote(**data.model_dump())
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return lote


@router.get("/{codigo}", response_model=LoteOut)
def obtener(codigo: str, db: Session = Depends(get_db)):
    return _get_or_404(db, codigo)


@router.get("/{codigo}/qr")
def qr(codigo: str, db: Session = Depends(get_db)):
    import io

    import qrcode

    lote = _get_or_404(db, codigo)
    buffer = io.BytesIO()
    qrcode.make(lote.codigo).save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/png")
