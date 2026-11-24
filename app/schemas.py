from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.models import Calidad, Estado, Rol

# Una línea de texto sin caracteres de control (saltos de línea, tabs, etc.). Estos campos
# terminan en asuntos de correo, CSV y prompts, donde un salto de línea rompe o inyecta contenido.
SIN_CONTROL = r"^[^\x00-\x1f\x7f]*$"

Productor = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120, pattern=SIN_CONTROL)]
Comprador = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120, pattern=SIN_CONTROL)]
Cultivo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80, pattern=SIN_CONTROL)]
Predio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120, pattern=SIN_CONTROL)]
Motivo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300, pattern=SIN_CONTROL)]
Hectareas = Annotated[float, Field(gt=0, le=10_000)]


def normalizar_rut(valor: str) -> str:
    """Valida el dígito verificador (módulo 11) y deja el RUT como 12345678-K."""
    limpio = valor.replace(".", "").replace("-", "").replace(" ", "").upper()
    cuerpo, dv = limpio[:-1], limpio[-1:]
    if not (cuerpo.isdigit() and 6 <= len(cuerpo) <= 8 and dv):
        raise ValueError("RUT inválido: usa el formato 12.345.678-5")
    suma, factor = 0, 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    esperado = {10: "K", 11: "0"}.get(11 - suma % 11, str(11 - suma % 11))
    if dv != esperado:
        raise ValueError("RUT inválido: el dígito verificador no corresponde")
    return f"{int(cuerpo)}-{dv}"


Rut = Annotated[str, StringConstraints(strip_whitespace=True, max_length=14)]


def validar_fecha_no_futura(fecha: date | None) -> date | None:
    if fecha is not None and fecha > date.today():
        raise ValueError("La fecha no puede ser futura")
    return fecha


class LoteCreate(BaseModel):
    productor: Productor
    cultivo: Cultivo
    predio: Predio | None = None
    superficie_ha: Hectareas | None = None
    # Primera entrega del lote
    kilos: float = Field(gt=0)
    fecha_cosecha: date
    calidad: Calidad = Calidad.PRIMERA

    _fecha_no_futura = field_validator("fecha_cosecha")(validar_fecha_no_futura)


class LoteUpdate(BaseModel):
    """Los kilos no se editan aquí: se corrigen anulando o agregando entregas."""

    productor: Productor | None = None
    cultivo: Cultivo | None = None
    predio: Predio | None = None
    superficie_ha: Hectareas | None = None
    fecha_cosecha: date | None = None
    motivo: Motivo

    _fecha_no_futura = field_validator("fecha_cosecha")(validar_fecha_no_futura)


class Anulacion(BaseModel):
    motivo: Motivo


class EntregaCreate(BaseModel):
    fecha: date
    kilos: float = Field(gt=0)
    calidad: Calidad = Calidad.PRIMERA

    _fecha_no_futura = field_validator("fecha")(validar_fecha_no_futura)


class EntregaOut(EntregaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: Estado
    motivo_anulacion: str | None
    creado: datetime


class LoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    productor: str
    cultivo: str
    predio: str | None
    superficie_ha: float | None
    kilos: float
    fecha_cosecha: date
    estado: Estado
    motivo_anulacion: str | None
    creado: datetime


class EntregaPublicaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha: date
    kilos: float
    calidad: Calidad


class LotePublicoOut(BaseModel):
    """Lo que ve cualquiera que escanee el QR: origen, entregas y estado, sin ventas ni precios."""

    model_config = ConfigDict(from_attributes=True)

    codigo: str
    productor: str
    cultivo: str
    predio: str | None
    kilos: float
    fecha_cosecha: date
    estado: Estado
    entregas: list[EntregaPublicaOut]


class VentaCreate(BaseModel):
    comprador: Comprador
    kilos: float = Field(gt=0)
    precio_por_kilo: float = Field(gt=0)
    fecha: date

    _fecha_no_futura = field_validator("fecha")(validar_fecha_no_futura)


class VentaOut(VentaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: Estado
    motivo_anulacion: str | None
    creado: datetime


class CambioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entidad: str
    entidad_id: int
    accion: str
    detalle: str
    motivo: str | None
    usuario_nombre: str
    fecha: datetime


class TrazabilidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lote: LoteOut
    kilos_vendidos: float
    kilos_disponibles: float
    ingresos: float
    entregas: list[EntregaOut]
    ventas: list[VentaOut]
    historial: list[CambioOut]


class DatoUsado(BaseModel):
    dato: str
    valor: str


class RecomendacionOut(BaseModel):
    id: int
    tipo: str
    lote_codigo: str | None
    proveedor: str
    texto: str
    datos_usados: list[DatoUsado]
    creado: datetime
    consultas_restantes: int | None = None  # del día, para el usuario


class SolicitudReporte(BaseModel):
    destinatario: EmailStr


class ReporteEnviadoOut(BaseModel):
    enviado_a: EmailStr


class FiltrosResumen(BaseModel):
    desde: date | None = None
    hasta: date | None = None
    usuario_id: int | None = None  # socio (solo administrador)
    cultivo: str | None = None


class ResumenCola(BaseModel):
    """Solicitud de cambio N°2: cuánto tarda un registro en llegar al servidor."""

    eventos: int
    en_cola: int  # los que esperaron sin conexión
    promedio_segundos: float | None
    promedio_cola_segundos: float | None
    maximo_segundos: float | None


class ResumenRecomendaciones(BaseModel):
    total: int
    ultima: RecomendacionOut | None


class ResumenOut(BaseModel):
    filtros: FiltrosResumen
    total_lotes: int
    total_entregas: int
    total_ventas: int
    kilos_cosechados: float
    kilos_vendidos: float
    kilos_disponibles: float
    ingresos: float
    kilos_por_cultivo: dict[str, float]
    recomendaciones: ResumenRecomendaciones
    cola: ResumenCola


class Credenciales(BaseModel):
    email: EmailStr
    clave: str = Field(max_length=128)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: EmailStr
    rut: str | None
    rol: Rol
    activo: bool


class UsuarioCreate(BaseModel):
    nombre: Productor
    email: EmailStr
    rut: Rut
    # Sin clave, se genera una aleatoria. En ambos casos se envía por correo al usuario.
    clave: str | None = Field(default=None, min_length=8, max_length=128)
    rol: Rol = Rol.PRODUCTOR

    _rut = field_validator("rut")(normalizar_rut)


class UsuarioCreadoOut(UsuarioOut):
    credenciales_enviadas: bool


class UsuarioUpdate(BaseModel):
    nombre: Productor | None = None
    email: EmailStr | None = None
    rut: Rut | None = None
    rol: Rol | None = None
    activo: bool | None = None

    @field_validator("rut")
    @classmethod
    def _rut(cls, valor: str | None) -> str | None:
        return normalizar_rut(valor) if valor is not None else None


class SesionOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


class SolicitudRecuperacion(BaseModel):
    email: EmailStr


class Restablecimiento(BaseModel):
    email: EmailStr
    codigo: str = Field(pattern=r"^\d{6}$")
    clave_nueva: str = Field(min_length=8, max_length=128)


class Mensaje(BaseModel):
    detail: str


# ---------- Campo y clima ----------

# Chile continental e insular cercana: la Red Agroclimática Nacional solo cubre el país.
Latitud = Annotated[float, Field(ge=-56, le=-17)]
Longitud = Annotated[float, Field(ge=-76, le=-66)]
NombreCampo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120, pattern=SIN_CONTROL)]


class CampoIn(BaseModel):
    nombre: NombreCampo
    latitud: Latitud
    longitud: Longitud


class CampoOut(CampoIn):
    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    productor: str
    actualizado: datetime


class EstacionOut(BaseModel):
    id: int
    nombre: str
    institucion: str
    comuna: str
    region: str
    latitud: float
    longitud: float
    distancia_km: float


class MedicionOut(BaseModel):
    fecha_hora: datetime
    temperatura: float | None = None
    humedad: float | None = None
    precipitacion: float | None = None
    viento: float | None = None


class ResumenClimaOut(BaseModel):
    """Últimas 24 horas."""

    temperatura_min: float | None
    temperatura_max: float | None
    precipitacion: float
    humedad_media: float | None
    viento_max: float | None


class AlertaOut(BaseModel):
    nivel: str  # alta | media | info
    titulo: str
    detalle: str


class LecturaSensorOut(BaseModel):
    fecha_hora: datetime
    humedad_suelo: float | None = None  # % de la capacidad de campo
    temperatura_suelo: float | None = None


class SensoresOut(BaseModel):
    fuente: str  # instacrops | simulado
    dispositivo: str
    actual: LecturaSensorOut | None
    reciente: bool  # False: la última lectura está atrasada y no se usa para recomendar


class ClimaOut(BaseModel):
    campo: CampoOut
    estacion: EstacionOut
    fuente: str  # agromet | simulado
    actual: MedicionOut | None
    resumen_24h: ResumenClimaOut
    serie: list[MedicionOut]
    alertas: list[AlertaOut]
    sensores: SensoresOut | None = None
    aviso_sensores: str | None = None  # por qué no hay sensores, si el proveedor falló
