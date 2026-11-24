from app.config import settings
from app.services.clima.proveedor import Medicion, ProveedorClima

_agromet = None


def crear_proveedor_clima() -> ProveedorClima:
    """Elige el adapter según CLIMA_PROVEEDOR en el .env."""
    global _agromet
    if settings.clima_proveedor == "agromet":
        from app.services.clima.agromet import AgrometAdapter

        if _agromet is None:  # una sola instancia: conserva la caché entre consultas
            _agromet = AgrometAdapter(
                settings.agromet_url,
                settings.agromet_cache_minutos,
                nombre="simulado" if settings.apis_simuladas else "agromet",
            )
        return _agromet

    from app.services.clima.simulado import ProveedorClimaSimulado

    return ProveedorClimaSimulado()


__all__ = ["Medicion", "ProveedorClima", "crear_proveedor_clima"]
