from app.config import settings
from app.services.sensores.proveedor import DatosSensores, LecturaSensor, ProveedorSensores

_instacrops = None


def crear_proveedor_sensores() -> ProveedorSensores | None:
    """Elige el adapter según SENSORES_PROVEEDOR en el .env (ninguno | instacrops)."""
    global _instacrops
    if settings.sensores_proveedor != "instacrops":
        return None
    if _instacrops is None:  # una sola instancia: conserva la caché entre consultas
        from app.services.sensores.instacrops import InstacropsAdapter

        _instacrops = InstacropsAdapter(
            settings.instacrops_api_url,
            settings.instacrops_api_key,
            settings.instacrops_cache_minutos,
            nombre="simulado" if settings.apis_simuladas else "instacrops",
        )
    return _instacrops


__all__ = ["DatosSensores", "LecturaSensor", "ProveedorSensores", "crear_proveedor_sensores"]
