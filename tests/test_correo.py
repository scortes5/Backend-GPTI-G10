import smtplib

import pytest

from app.exceptions import ServicioExternoNoDisponible
from app.services.correo import Adjunto, Correo, crear_servicio_correo
from app.services.correo.simulado import CorreoSimulado
from app.services.correo.smtp import SmtpAdapter

CORREO = Correo(
    destinatario="auditor@ejemplo.cl",
    asunto="Reporte",
    cuerpo="Hola",
    adjuntos=[Adjunto("ventas.csv", b"a,b\n1,2\n", "text/csv")],
)


def adapter() -> SmtpAdapter:
    return SmtpAdapter("smtp.ejemplo.cl", 587, "usuario", "clave", "AgroTracker <no-reply@ejemplo.cl>")


def test_por_defecto_se_usa_el_correo_simulado():
    assert isinstance(crear_servicio_correo(), CorreoSimulado)


def test_smtp_arma_el_mensaje_con_adjuntos():
    mensaje = adapter()._construir_mensaje(CORREO)

    assert mensaje["To"] == "auditor@ejemplo.cl"
    assert mensaje["Subject"] == "Reporte"
    assert [parte.get_filename() for parte in mensaje.iter_attachments()] == ["ventas.csv"]


def test_smtp_caido_se_traduce_a_error_de_dominio(monkeypatch):
    def smtp_que_falla(*args, **kwargs):
        raise smtplib.SMTPConnectError(421, "no disponible")

    monkeypatch.setattr(smtplib, "SMTP", smtp_que_falla)

    with pytest.raises(ServicioExternoNoDisponible):
        adapter().enviar(CORREO)
