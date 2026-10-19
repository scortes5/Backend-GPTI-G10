"""Recomendaciones agronómicas por lote, independientes del proveedor de IA."""
from sqlalchemy.orm import Session

from app.models import Lote
from app.services import lotes as lotes_service
from app.services.ia import ProveedorIA

INSTRUCCIONES = (
    "Eres un asesor agronómico para pequeños productores de una cooperativa chilena. "
    "Responde en español simple, en máximo 5 viñetas cortas y accionables."
)


def recomendar(db: Session, codigo_lote: str, proveedor: ProveedorIA) -> str:
    lote = lotes_service.obtener(db, codigo_lote)
    return proveedor.generar(INSTRUCCIONES, describir_lote(lote))


def describir_lote(lote: Lote) -> str:
    return (
        f"Lote {lote.codigo} de {lote.cultivo}, productor {lote.productor}. "
        f"Cosechado el {lote.fecha_cosecha:%d-%m-%Y} con {lote.kilos:g} kg; "
        f"vendidos {lote.kilos_vendidos:g} kg, disponibles {lote.kilos_disponibles:g} kg. "
        "¿Qué recomiendas para conservar y comercializar lo disponible?"
    )
