"""Reportes de trazabilidad enviados por correo, independientes del proveedor de correo."""
import csv
import io

from sqlalchemy.orm import Session

from app.models import Usuario
from app.schemas import TrazabilidadOut
from app.services import lotes as lotes_service
from app.services.correo import Adjunto, Correo, ServicioCorreo

COLUMNAS_VENTAS = ["fecha", "comprador", "kilos", "precio_por_kilo"]


def enviar_reporte_lote(
    db: Session, codigo: str, destinatario: str, usuario: Usuario, servicio: ServicioCorreo
) -> None:
    traza = lotes_service.trazabilidad(db, codigo, usuario)
    servicio.enviar(armar_reporte(traza, destinatario))


def armar_reporte(traza: TrazabilidadOut, destinatario: str) -> Correo:
    lote = traza.lote
    return Correo(
        destinatario=destinatario,
        asunto=f"Reporte de trazabilidad · Lote {lote.codigo} ({lote.cultivo})",
        cuerpo=_cuerpo(traza),
        adjuntos=[Adjunto(f"ventas_{lote.codigo}.csv", _ventas_csv(traza), "text/csv")],
    )


def _cuerpo(traza: TrazabilidadOut) -> str:
    lote = traza.lote
    return (
        f"Lote: {lote.codigo}\n"
        f"Productor: {lote.productor}\n"
        f"Cultivo: {lote.cultivo}\n"
        f"Fecha de cosecha: {lote.fecha_cosecha:%d-%m-%Y}\n\n"
        f"Kilos cosechados: {lote.kilos:g}\n"
        f"Kilos vendidos: {traza.kilos_vendidos:g}\n"
        f"Kilos disponibles: {traza.kilos_disponibles:g}\n"
        f"Ingresos: ${traza.ingresos:,.0f}\n"
        f"Ventas registradas: {len(traza.ventas)} (detalle en el CSV adjunto)\n\n"
        f"Ficha en línea: {lotes_service.url_trazabilidad(lote.codigo)}\n"
    )


def _ventas_csv(traza: TrazabilidadOut) -> bytes:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(COLUMNAS_VENTAS)
    for venta in traza.ventas:
        escritor.writerow([getattr(venta, columna) for columna in COLUMNAS_VENTAS])
    return buffer.getvalue().encode("utf-8")
