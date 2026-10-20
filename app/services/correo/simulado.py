import logging

from app.services.correo.servicio import Correo

logger = logging.getLogger("agrotracker.correo")


class CorreoSimulado:
    """No envía nada: registra el correo completo en el log. Solo para desarrollo y demos sin SMTP:
    el log incluye el cuerpo (por ejemplo, códigos de recuperación), así que nunca usarlo en producción.
    """

    def enviar(self, correo: Correo) -> None:
        adjuntos = ", ".join(adjunto.nombre for adjunto in correo.adjuntos) or "sin adjuntos"
        logger.warning(
            "Correo simulado a %s: %s (%s)\n%s", correo.destinatario, correo.asunto, adjuntos, correo.cuerpo
        )
