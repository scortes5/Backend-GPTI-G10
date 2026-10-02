from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class LoteCreate(BaseModel):
    productor: str
    cultivo: str
    kilos: float = Field(gt=0)
    fecha_cosecha: date


class LoteOut(LoteCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    creado: datetime
