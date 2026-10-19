from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Productor = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Cultivo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


def validar_fecha_no_futura(fecha: date) -> date:
    if fecha > date.today():
        raise ValueError("La fecha de cosecha no puede ser futura")
    return fecha


class LoteCreate(BaseModel):
    productor: Productor
    cultivo: Cultivo
    kilos: float = Field(gt=0)
    fecha_cosecha: date

    _fecha_no_futura = field_validator("fecha_cosecha")(validar_fecha_no_futura)


class LoteOut(LoteCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    creado: datetime
