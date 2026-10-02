import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Lote(Base):
    __tablename__ = "lotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(12), unique=True, default=lambda: uuid.uuid4().hex[:12])
    productor: Mapped[str] = mapped_column(String(120))
    cultivo: Mapped[str] = mapped_column(String(80))
    kilos: Mapped[float] = mapped_column(Float)
    fecha_cosecha: Mapped[date] = mapped_column(Date)
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
