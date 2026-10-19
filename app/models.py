import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    ventas: Mapped[list["Venta"]] = relationship(
        back_populates="lote", cascade="all, delete-orphan", order_by="Venta.fecha"
    )

    @property
    def kilos_vendidos(self) -> float:
        return sum(venta.kilos for venta in self.ventas)

    @property
    def kilos_disponibles(self) -> float:
        return self.kilos - self.kilos_vendidos


class Venta(Base):
    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"))
    comprador: Mapped[str] = mapped_column(String(120))
    kilos: Mapped[float] = mapped_column(Float)
    precio_por_kilo: Mapped[float] = mapped_column(Float)
    fecha: Mapped[date] = mapped_column(Date)
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    lote: Mapped[Lote] = relationship(back_populates="ventas")
