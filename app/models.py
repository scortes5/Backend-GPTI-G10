import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
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
    rut: Mapped[str | None] = mapped_column(String(12), unique=True)  # normalizado: 12345678-K
    clave_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[Rol] = mapped_column(Enum(Rol, native_enum=False, length=20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # Tokens emitidos antes de este momento (UTC) ya no valen: se actualiza al cambiar la clave.
    sesiones_desde: Mapped[datetime | None] = mapped_column(DateTime)

    @property
    def es_admin(self) -> bool:
        return self.rol == Rol.ADMIN


class CodigoRecuperacion(Base):
    """Código de un solo uso enviado por correo para restablecer la contraseña."""

    __tablename__ = "codigos_recuperacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    codigo_hash: Mapped[str] = mapped_column(String(255))
    expira: Mapped[datetime] = mapped_column(DateTime)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    usado: Mapped[bool] = mapped_column(Boolean, default=False)


class TokenRevocado(Base):
    """Tokens de sesiones cerradas. Se borran cuando ya habrían expirado de todas formas."""

    __tablename__ = "tokens_revocados"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expira: Mapped[datetime] = mapped_column(DateTime)


class Estado(str, enum.Enum):
    """Los registros no se borran: se anulan con un motivo y dejan de contar."""

    VIGENTE = "vigente"
    ANULADO = "anulado"


class Calidad(str, enum.Enum):
    EXTRA = "extra"
    PRIMERA = "primera"
    SEGUNDA = "segunda"
    DESCARTE = "descarte"


class Lote(Base):
    __tablename__ = "lotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(12), unique=True, default=lambda: uuid.uuid4().hex[:12])
    productor: Mapped[str] = mapped_column(String(120))
    cultivo: Mapped[str] = mapped_column(String(80))
    predio: Mapped[str | None] = mapped_column(String(120))
    superficie_ha: Mapped[float | None] = mapped_column(Float)
    # Suma de las entregas vigentes. Se recalcula en services/lotes.py cada vez que cambian.
    kilos: Mapped[float] = mapped_column(Float, default=0)
    fecha_cosecha: Mapped[date] = mapped_column(Date)  # fecha de la primera entrega
    estado: Mapped[Estado] = mapped_column(Enum(Estado, native_enum=False, length=10), default=Estado.VIGENTE)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(300))
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))

    entregas: Mapped[list["Entrega"]] = relationship(
        back_populates="lote", cascade="all, delete-orphan", order_by="Entrega.fecha"
    )
    ventas: Mapped[list["Venta"]] = relationship(
        back_populates="lote", cascade="all, delete-orphan", order_by="Venta.fecha"
    )

    @property
    def anulado(self) -> bool:
        return self.estado == Estado.ANULADO

    @property
    def entregas_vigentes(self) -> list["Entrega"]:
        return [e for e in self.entregas if e.estado == Estado.VIGENTE]

    @property
    def ventas_vigentes(self) -> list["Venta"]:
        return [v for v in self.ventas if v.estado == Estado.VIGENTE]

    @property
    def kilos_vendidos(self) -> float:
        return sum(venta.kilos for venta in self.ventas_vigentes)

    @property
    def kilos_disponibles(self) -> float:
        return self.kilos - self.kilos_vendidos

    @property
    def ingresos(self) -> float:
        return sum(venta.total for venta in self.ventas_vigentes)


class Entrega(Base):
    """Cada vez que el socio entrega cosecha de un lote (un lote puede tener varias)."""

    __tablename__ = "entregas"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"))
    fecha: Mapped[date] = mapped_column(Date)
    kilos: Mapped[float] = mapped_column(Float)
    calidad: Mapped[Calidad] = mapped_column(Enum(Calidad, native_enum=False, length=10), default=Calidad.PRIMERA)
    estado: Mapped[Estado] = mapped_column(Enum(Estado, native_enum=False, length=10), default=Estado.VIGENTE)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(300))
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    lote: Mapped[Lote] = relationship(back_populates="entregas")


class Venta(Base):
    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"))
    comprador: Mapped[str] = mapped_column(String(120))
    kilos: Mapped[float] = mapped_column(Float)
    precio_por_kilo: Mapped[float] = mapped_column(Float)
    fecha: Mapped[date] = mapped_column(Date)
    estado: Mapped[Estado] = mapped_column(Enum(Estado, native_enum=False, length=10), default=Estado.VIGENTE)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(300))
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    lote: Mapped[Lote] = relationship(back_populates="ventas")

    @property
    def total(self) -> float:
        return self.kilos * self.precio_por_kilo


class Cambio(Base):
    """Registro de auditoría: quién cambió qué, cuándo y por qué. Nunca se edita ni se borra."""

    __tablename__ = "cambios"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes.id"), index=True)
    entidad: Mapped[str] = mapped_column(String(10))  # lote | entrega | venta
    entidad_id: Mapped[int] = mapped_column(Integer)
    accion: Mapped[str] = mapped_column(String(10))  # creado | editado | anulado
    detalle: Mapped[str] = mapped_column(Text, default="")  # "campo: antes → después; ..."
    motivo: Mapped[str | None] = mapped_column(String(300))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    usuario_nombre: Mapped[str] = mapped_column(String(120))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Recomendacion(Base):
    """Historial de recomendaciones de IA con los datos que se le entregaron."""

    __tablename__ = "recomendaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10))  # lote | clima
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    proveedor: Mapped[str] = mapped_column(String(20))
    texto: Mapped[str] = mapped_column(Text)
    datos_usados: Mapped[str] = mapped_column(Text)  # JSON: lista de {"dato", "valor"}
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    lote: Mapped[Lote | None] = relationship()


class EventoCola(Base):
    """Registros que el frontend envió desde la cola sin conexión (solicitud de cambio N°2).

    `id_cliente` lo genera el navegador al guardar el registro: si llega dos veces (un reintento
    tras un corte), la segunda no se vuelve a aplicar. Con `creado_cliente` y `recibido` se mide
    cuánto tarda un dato en llegar al servidor.
    """

    __tablename__ = "eventos_cola"

    id_cliente: Mapped[str] = mapped_column(String(64), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))
    recurso: Mapped[str] = mapped_column(String(40))  # código del lote o id de la venta/entrega
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    en_cola: Mapped[bool] = mapped_column(Boolean, default=False)  # False: se envió apenas se guardó
    creado_cliente: Mapped[datetime] = mapped_column(DateTime)
    recibido: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    @property
    def segundos(self) -> float:
        return max(0.0, (self.recibido - self.creado_cliente).total_seconds())


class Campo(Base):
    """Ubicación del campo de un usuario: con ella se busca la estación agroclimática más cercana."""

    __tablename__ = "campos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    latitud: Mapped[float] = mapped_column(Float)
    longitud: Mapped[float] = mapped_column(Float)
    actualizado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    usuario: Mapped[Usuario] = relationship()
