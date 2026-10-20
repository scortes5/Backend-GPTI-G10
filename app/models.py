import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Rol(str, enum.Enum):
    """Clases de usuario del documento de requerimientos."""

    ADMIN = "admin"  # directiva de la cooperativa: gestiona usuarios y ve todo
    PRODUCTOR = "productor"  # socio productor: gestiona solo sus lotes


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    clave_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[Rol] = mapped_column(Enum(Rol, native_enum=False, length=20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    @property
    def es_admin(self) -> bool:
        return self.rol == Rol.ADMIN


class Lote(Base):
    __tablename__ = "lotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(12), unique=True, default=lambda: uuid.uuid4().hex[:12])
    productor: Mapped[str] = mapped_column(String(120))
    cultivo: Mapped[str] = mapped_column(String(80))
    kilos: Mapped[float] = mapped_column(Float)
    fecha_cosecha: Mapped[date] = mapped_column(Date)
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))

    ventas: Mapped[list["Venta"]] = relationship(
        back_populates="lote", cascade="all, delete-orphan", order_by="Venta.fecha"
    )

    @property
    def kilos_vendidos(self) -> float:
        return sum(venta.kilos for venta in self.ventas)

    @property
    def kilos_disponibles(self) -> float:
        return self.kilos - self.kilos_vendidos

    @property
    def ingresos(self) -> float:
        return sum(venta.total for venta in self.ventas)


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

    @property
    def total(self) -> float:
        return self.kilos * self.precio_por_kilo
