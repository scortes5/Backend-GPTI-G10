from typing import Protocol

from app.services.ia.contexto import Contexto


class ProveedorIA(Protocol):
    """Puerto (target del patrón Adapter): lo único que el dominio sabe de la IA.

    Cada proveedor concreto (Gemini, Claude o uno simulado) se adapta a esta
    interfaz, así cambiar de proveedor no toca los casos de uso.
    """

    def generar(self, instrucciones: str, consulta: str, contexto: Contexto | None = None) -> str:
        """`consulta` es el texto para un modelo; `contexto`, los mismos datos estructurados."""
        ...
