"""Recomendaciones agronómicas por lote, independientes del proveedor de IA."""
from sqlalchemy.orm import Session

from app.models import Lote, Usuario
from app.services import lotes as lotes_service
from app.services.ia import ProveedorIA

INSTRUCCIONES = (
    "Eres un asesor agronómico para pequeños productores de una cooperativa chilena. "
    "Responde en español simple, en máximo 5 viñetas cortas y accionables."
)


def recomendar(db: Session, codigo_lote: str, usuario: Usuario, proveedor: ProveedorIA) -> str:
    lote = lotes_service.obtener(db, codigo_lote, usuario)
    return proveedor.generar(INSTRUCCIONES, describir_lote(lote))


def describir_lote(lote: Lote) -> str:
    return (
        f"Lote {lote.codigo} de {lote.cultivo}, productor {lote.productor}. "
        f"Cosechado el {lote.fecha_cosecha:%d-%m-%Y} con {lote.kilos:g} kg; "
        f"vendidos {lote.kilos_vendidos:g} kg, disponibles {lote.kilos_disponibles:g} kg. "
        "¿Qué recomiendas para conservar y comercializar lo disponible?"
    )


INSTRUCCIONES_CLIMA = (
    "Eres un asesor agronómico para pequeños productores de una cooperativa chilena del sur. "
    "Con el clima reciente del campo (estación de la Red Agroclimática Nacional) y lo que el productor "
    "tiene en bodega, indica qué debe tomar en consideración hoy y los próximos días: labores, riego, "
    "heladas, plagas y enfermedades, cosecha y conservación. Responde en español simple, en máximo 6 "
    "viñetas cortas y accionables, empezando por lo más urgente. No inventes datos que no se entregan."
)


def recomendar_clima(db: Session, usuario: Usuario, clima, proveedor: ProveedorIA) -> str:
    from app.services.clima.analisis import describir

    duenio = db.get(Usuario, clima.campo.usuario_id)
    lotes = [l for l in lotes_service.listar(db, duenio) if l.kilos_disponibles > 0]
    consulta = describir(clima)
    if not clima.alertas:
        consulta += " Sin alertas climáticas."
    if lotes:
        consulta += " En bodega: " + "; ".join(
            f"{l.cultivo} {l.kilos_disponibles:g} kg (cosechado el {l.fecha_cosecha:%d-%m-%Y})" for l in lotes[:10]
        ) + "."
    else:
        consulta += " No tiene cosecha en bodega."
    return proveedor.generar(INSTRUCCIONES_CLIMA, consulta + " ¿Qué debo tomar en consideración?")
