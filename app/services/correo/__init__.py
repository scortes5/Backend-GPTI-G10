from app.config import settings
from app.services.correo.servicio import Adjunto, Correo, ServicioCorreo

__all__ = ["Adjunto", "Correo", "ServicioCorreo", "crear_servicio_correo"]


def crear_servicio_correo() -> ServicioCorreo:
    """Elige el adapter según CORREO_PROVEEDOR en el .env."""
    if settings.correo_proveedor == "smtp":
        from app.services.correo.smtp import SmtpAdapter

        return SmtpAdapter(
            host=settings.smtp_host,
            puerto=settings.smtp_puerto,
            usuario=settings.smtp_usuario,
            clave=settings.smtp_clave,
            remitente=settings.correo_remitente,
        )

    from app.services.correo.simulado import CorreoSimulado

    return CorreoSimulado()
