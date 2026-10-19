from app.config import settings
from app.services.ia.proveedor import ProveedorIA


def crear_proveedor() -> ProveedorIA:
    """Elige el adapter según IA_PROVEEDOR en el .env."""
    if settings.ia_proveedor == "claude":
        from app.services.ia.claude import ClaudeAdapter

        return ClaudeAdapter(api_key=settings.anthropic_api_key, modelo=settings.ia_modelo)

    from app.services.ia.simulado import ProveedorSimulado

    return ProveedorSimulado()
