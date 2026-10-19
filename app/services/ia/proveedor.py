from typing import Protocol


class ProveedorIA(Protocol):
    """Puerto (target del patrón Adapter): lo único que el dominio sabe de la IA.

    Cada proveedor concreto (Claude, uno simulado, otro a futuro) se adapta a esta
    interfaz, así cambiar de proveedor no toca los casos de uso.
    """

    def generar(self, instrucciones: str, consulta: str) -> str: ...
