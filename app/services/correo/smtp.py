import smtplib
from email.message import EmailMessage

from app.exceptions import ServicioExternoNoDisponible
from app.services.correo.servicio import Correo


class SmtpAdapter:
    """Adapta smtplib (Gmail, Outlook, SendGrid SMTP, etc.) a la interfaz ServicioCorreo."""

    def __init__(self, host: str, puerto: int, usuario: str, clave: str, remitente: str):
        self._host = host
        self._puerto = puerto
        self._usuario = usuario
        self._clave = clave
        self._remitente = remitente

    def enviar(self, correo: Correo) -> None:
        try:
            with smtplib.SMTP(self._host, self._puerto, timeout=15) as servidor:
                servidor.starttls()
                if self._usuario:
                    servidor.login(self._usuario, self._clave)
                servidor.send_message(self._construir_mensaje(correo))
        except (smtplib.SMTPException, OSError) as error:
            raise ServicioExternoNoDisponible("No se pudo enviar el correo") from error

    def _construir_mensaje(self, correo: Correo) -> EmailMessage:
        mensaje = EmailMessage()
        mensaje["From"] = self._remitente
        mensaje["To"] = correo.destinatario
        mensaje["Subject"] = correo.asunto
        mensaje.set_content(correo.cuerpo)
        for adjunto in correo.adjuntos:
            tipo, subtipo = adjunto.tipo_mime.split("/", 1)
            mensaje.add_attachment(adjunto.contenido, maintype=tipo, subtype=subtipo, filename=adjunto.nombre)
        return mensaje
