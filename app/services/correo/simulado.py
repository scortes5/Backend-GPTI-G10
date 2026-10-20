import logging

from app.services.correo.servicio import Correo

logger = logging.getLogger("agrotracker.correo")


class CorreoSimulado:
    """No envía nada: registra el correo en el log. Para desarrollo y demos sin SMTP."""

    def enviar(self, correo: Correo) -> None:
        adjuntos = ", ".join(adjunto.nombre for adjunto in correo.adjuntos) or "sin adjuntos"
        logger.warning("Correo simulado a %s: %s (%s)", correo.destinatario, correo.asunto, adjuntos)
