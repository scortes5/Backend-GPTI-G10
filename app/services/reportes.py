"""Reporte de trazabilidad de un lote en PDF y CSV: para descargar o enviar por correo."""
import csv
import io
from datetime import datetime

from fpdf import FPDF, FontFace
from sqlalchemy.orm import Session

from app.models import Usuario
from app.schemas import TrazabilidadOut
from app.services import historial
from app.services import lotes as lotes_service
from app.services.correo import Adjunto, Correo, ServicioCorreo

COLUMNAS_VENTAS = ["fecha", "comprador", "kilos", "precio_por_kilo", "estado"]


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
        adjuntos=[
            Adjunto(f"lote_{lote.codigo}.pdf", pdf(traza), "application/pdf"),
            Adjunto(f"ventas_{lote.codigo}.csv", _ventas_csv(traza), "text/csv"),
        ],
    )


def _cuerpo(traza: TrazabilidadOut) -> str:
    lote = traza.lote
    return (
        f"Lote: {lote.codigo}\n"
        f"Productor: {lote.productor}\n"
        f"Cultivo: {lote.cultivo}\n"
        f"Predio: {lote.predio or '—'}\n"
        f"Estado: {lote.estado.value}\n"
        f"Fecha de cosecha: {lote.fecha_cosecha:%d-%m-%Y}\n\n"
        f"Kilos cosechados: {lote.kilos:g}\n"
        f"Kilos vendidos: {traza.kilos_vendidos:g}\n"
        f"Kilos disponibles: {traza.kilos_disponibles:g}\n"
        f"Ingresos: ${traza.ingresos:,.0f}\n"
        f"Entregas registradas: {len(traza.entregas)}\n"
        f"Ventas registradas: {len(traza.ventas)} (detalle en los adjuntos PDF y CSV)\n\n"
        f"Ficha en línea: {lotes_service.url_trazabilidad(lote.codigo)}\n"
    )


def _ventas_csv(traza: TrazabilidadOut) -> bytes:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(COLUMNAS_VENTAS)
    for venta in traza.ventas:
        escritor.writerow([_valor(getattr(venta, columna)) for columna in COLUMNAS_VENTAS])
    return buffer.getvalue().encode("utf-8")


def csv_completo(traza: TrazabilidadOut) -> bytes:
    """Un CSV con el lote, sus entregas, sus ventas y el historial de cambios, una fila por registro.

    Lleva BOM para que Excel lo abra con tildes y eñes correctas.
    """
    lote = traza.lote
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(["registro", "fecha", "detalle", "kilos", "calidad", "comprador", "precio_por_kilo", "estado", "motivo", "usuario"])
    escritor.writerow(["lote", lote.fecha_cosecha, f"{lote.codigo} {lote.cultivo} · {lote.productor} · predio {lote.predio or '—'}",
                       _valor(lote.kilos), "", "", "", lote.estado.value, lote.motivo_anulacion or "", ""])
    for e in traza.entregas:
        escritor.writerow(["entrega", e.fecha, "", _valor(e.kilos), e.calidad.value, "", "", e.estado.value, e.motivo_anulacion or "", ""])
    for v in traza.ventas:
        escritor.writerow(["venta", v.fecha, "", _valor(v.kilos), "", v.comprador, _valor(v.precio_por_kilo), v.estado.value, v.motivo_anulacion or "", ""])
    for c in traza.historial:
        escritor.writerow([f"cambio {c.entidad}", f"{c.fecha:%Y-%m-%d %H:%M}", f"{historial.titulo(c.entidad, c.accion)}: {c.detalle}", "", "", "", "", "", c.motivo or "", c.usuario_nombre])
    return ("﻿" + buffer.getvalue()).encode("utf-8")


def _valor(valor):
    return getattr(valor, "value", valor)


# ---------- PDF ----------

VERDE = (47, 93, 58)
GRIS = (110, 110, 110)


class _Documento(FPDF):
    def __init__(self, codigo: str):
        super().__init__(format="A4")
        self.codigo = codigo
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(True, margin=18)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*GRIS)
        self.cell(0, 5, f"AgroTracker · Cooperativa Newen al Sur · Lote {self.codigo} · página {self.page_no()}", align="C")


def pdf(traza: TrazabilidadOut) -> bytes:
    lote = traza.lote
    doc = _Documento(lote.codigo)
    doc.add_page()

    doc.set_font("Helvetica", "B", 18)
    doc.set_text_color(*VERDE)
    doc.cell(0, 9, "Reporte de trazabilidad", new_x="LMARGIN", new_y="NEXT")
    doc.set_font("Helvetica", size=9)
    doc.set_text_color(*GRIS)
    doc.cell(0, 5, f"Generado el {datetime.now():%d-%m-%Y %H:%M} · {lotes_service.url_trazabilidad(lote.codigo)}",
             new_x="LMARGIN", new_y="NEXT")
    doc.ln(4)

    if lote.estado.value == "anulado":
        doc.set_fill_color(253, 236, 234)
        doc.set_text_color(160, 40, 30)
        doc.set_font("Helvetica", "B", 10)
        doc.multi_cell(0, 7, _latin(f"LOTE ANULADO. Motivo: {lote.motivo_anulacion or '-'}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        doc.ln(2)

    _pares(doc, [
        ("Código", lote.codigo), ("Cultivo", lote.cultivo), ("Productor", lote.productor),
        ("Predio", lote.predio or "—"), ("Superficie", f"{_n(lote.superficie_ha)} ha" if lote.superficie_ha else "—"),
        ("Primera cosecha", f"{lote.fecha_cosecha:%d-%m-%Y}"), ("Kilos cosechados", f"{_n(lote.kilos)} kg"),
        ("Kilos vendidos", f"{_n(traza.kilos_vendidos)} kg"), ("Kilos disponibles", f"{_n(traza.kilos_disponibles)} kg"),
        ("Ingresos", _clp(traza.ingresos)),
    ])

    _titulo(doc, "Entregas de cosecha")
    _tabla(doc, ["Fecha", "Kilos", "Calidad", "Estado"], [38, 38, 44, 54], [
        [f"{e.fecha:%d-%m-%Y}", f"{_n(e.kilos)} kg", e.calidad.value.capitalize(), _estado(e.estado.value, e.motivo_anulacion)]
        for e in traza.entregas
    ])

    _titulo(doc, "Ventas")
    _tabla(doc, ["Fecha", "Comprador", "Kilos", "Precio/kg", "Total", "Estado"], [24, 44, 24, 24, 28, 30], [
        [f"{v.fecha:%d-%m-%Y}", v.comprador, f"{_n(v.kilos)} kg", _clp(v.precio_por_kilo), _clp(v.kilos * v.precio_por_kilo),
         _estado(v.estado.value, v.motivo_anulacion)]
        for v in traza.ventas
    ], vacio="El lote no tiene ventas.")

    _titulo(doc, "Historial de cambios")
    _tabla(doc, ["Fecha", "Usuario", "Registro", "Detalle y motivo"], [28, 34, 26, 86], [
        [f"{c.fecha:%d-%m-%Y %H:%M}", c.usuario_nombre, historial.titulo(c.entidad, c.accion),
         c.detalle + (f" · Motivo: {c.motivo}" if c.motivo else "")]
        for c in traza.historial
    ], vacio="Sin cambios registrados.")
    return bytes(doc.output())


def _titulo(doc: FPDF, texto: str) -> None:
    doc.ln(5)
    doc.set_font("Helvetica", "B", 12)
    doc.set_text_color(*VERDE)
    doc.cell(0, 7, texto, new_x="LMARGIN", new_y="NEXT")


def _pares(doc: FPDF, pares: list[tuple[str, str]]) -> None:
    for etiqueta, valor in pares:
        doc.set_font("Helvetica", size=9)
        doc.set_text_color(*GRIS)
        doc.cell(45, 6, etiqueta)
        doc.set_font("Helvetica", "B", 10)
        doc.set_text_color(30, 30, 30)
        doc.cell(0, 6, _latin(valor), new_x="LMARGIN", new_y="NEXT")


def _tabla(doc: FPDF, columnas: list[str], anchos: list[int], filas: list[list[str]], vacio: str = "Sin registros.") -> None:
    if not filas:
        doc.set_font("Helvetica", "I", 9)
        doc.set_text_color(*GRIS)
        doc.cell(0, 6, vacio, new_x="LMARGIN", new_y="NEXT")
        return
    doc.set_font("Helvetica", size=9)
    doc.set_text_color(30, 30, 30)
    with doc.table(col_widths=anchos, text_align="LEFT", line_height=5.5,
                   headings_style=FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=VERDE)) as tabla:
        encabezado = tabla.row()
        for c in columnas:
            encabezado.cell(c)
        for fila in filas:
            linea = tabla.row()
            for valor in fila:
                linea.cell(_latin(valor))


def _estado(estado: str, motivo: str | None) -> str:
    return f"Anulada: {motivo}" if estado == "anulado" else "Vigente"


def _n(valor: float | None) -> str:
    return f"{valor or 0:,.1f}".rstrip("0").rstrip(".").replace(",", "_").replace(".", ",").replace("_", ".")


def _clp(valor: float) -> str:
    return "$" + f"{valor:,.0f}".replace(",", ".")


def _latin(texto: str) -> str:
    """Las fuentes base del PDF usan Latin-1: tildes y eñes sí, emojis u otros símbolos no."""
    return str(texto).replace("→", "->").replace("—", "-").replace("·", "-").encode("latin-1", "replace").decode("latin-1")
