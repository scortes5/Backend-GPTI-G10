"""Ajustes a bases creadas con versiones anteriores.

`create_all` crea las tablas nuevas pero no agrega columnas a las que ya existen. Aquí se agregan
las columnas que faltan y se completan los datos para que los lotes antiguos sigan funcionando.
Es idempotente: se ejecuta en cada inicio y no hace nada si la base ya está al día.
"""
import logging
from datetime import date

from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Entrega, Lote

logger = logging.getLogger("agrotracker.migraciones")

# tabla -> columnas agregadas después de la primera versión (definidas en models.py)
COLUMNAS_NUEVAS = {
    "usuarios": ["rut"],
    "lotes": ["predio", "superficie_ha", "estado", "motivo_anulacion"],
    "ventas": ["estado", "motivo_anulacion"],
}
VALORES_INICIALES = {"estado": "'VIGENTE'"}  # SQLAlchemy guarda el nombre del enum


def migrar(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    _agregar_columnas(engine)
    with Session(engine) as db:
        _entregas_de_lotes_antiguos(db)


def _agregar_columnas(engine: Engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as conexion:
        for tabla, columnas in COLUMNAS_NUEVAS.items():
            existentes = {c["name"] for c in inspector.get_columns(tabla)}
            for nombre in columnas:
                if nombre in existentes:
                    continue
                columna = Base.metadata.tables[tabla].columns[nombre]
                tipo = columna.type.compile(engine.dialect)
                conexion.execute(text(f'ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}'))
                if nombre in VALORES_INICIALES:
                    conexion.execute(text(f"UPDATE {tabla} SET {nombre} = {VALORES_INICIALES[nombre]}"))
                logger.warning("Columna agregada: %s.%s", tabla, nombre)


def _entregas_de_lotes_antiguos(db: Session) -> None:
    """Antes cada lote guardaba sus kilos directamente: se convierten en su primera entrega."""
    sin_entregas = db.scalars(select(Lote).where(~Lote.entregas.any(), Lote.kilos > 0)).all()
    for lote in sin_entregas:
        db.add(Entrega(lote=lote, fecha=lote.fecha_cosecha or date.today(), kilos=lote.kilos))
    if sin_entregas:
        db.commit()
        logger.warning("Entregas creadas para %d lote(s) anteriores", len(sin_entregas))
