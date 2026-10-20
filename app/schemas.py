from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.models import Rol

Productor = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Comprador = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Cultivo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


def validar_fecha_no_futura(fecha: date | None) -> date | None:
    if fecha is not None and fecha > date.today():
        raise ValueError("La fecha no puede ser futura")
    return fecha


class LoteCreate(BaseModel):
    productor: Productor
    cultivo: Cultivo
    kilos: float = Field(gt=0)
    fecha_cosecha: date

    _fecha_no_futura = field_validator("fecha_cosecha")(validar_fecha_no_futura)


class LoteUpdate(BaseModel):
    productor: Productor | None = None
    cultivo: Cultivo | None = None
    kilos: float | None = Field(default=None, gt=0)
    fecha_cosecha: date | None = None

    _fecha_no_futura = field_validator("fecha_cosecha")(validar_fecha_no_futura)


class LoteOut(LoteCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    creado: datetime


class LotePublicoOut(BaseModel):
    """Lo que ve cualquiera que escanee el QR: origen del lote, sin ventas ni precios."""

    model_config = ConfigDict(from_attributes=True)

    codigo: str
    productor: str
    cultivo: str
    kilos: float
    fecha_cosecha: date


class VentaCreate(BaseModel):
    comprador: Comprador
    kilos: float = Field(gt=0)
    precio_por_kilo: float = Field(gt=0)
    fecha: date

    _fecha_no_futura = field_validator("fecha")(validar_fecha_no_futura)


class VentaOut(VentaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    creado: datetime


class TrazabilidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lote: LoteOut
    kilos_vendidos: float
    kilos_disponibles: float
    ingresos: float
    ventas: list[VentaOut]


class RecomendacionOut(BaseModel):
    texto: str


class SolicitudReporte(BaseModel):
    destinatario: EmailStr


class ReporteEnviadoOut(BaseModel):
    enviado_a: EmailStr


class ResumenOut(BaseModel):
    total_lotes: int
    kilos_cosechados: float
    kilos_vendidos: float
    kilos_disponibles: float
    ingresos: float
    kilos_por_cultivo: dict[str, float]


class Credenciales(BaseModel):
    email: EmailStr
    clave: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: EmailStr
    rol: Rol
    activo: bool


class SesionOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
