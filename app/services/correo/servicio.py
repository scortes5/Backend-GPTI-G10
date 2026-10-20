from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Adjunto:
    nombre: str
    contenido: bytes
    tipo_mime: str = "application/octet-stream"


@dataclass(frozen=True)
class Correo:
    destinatario: str
    asunto: str
    cuerpo: str
    adjuntos: list[Adjunto] = field(default_factory=list)


class ServicioCorreo(Protocol):
    """Puerto (target del patrón Adapter) para enviar correos.

    Los casos de uso arman un Correo y no saben si sale por SMTP, por otro
    proveedor o si solo se registra en consola.
    """

    def enviar(self, correo: Correo) -> None: ...
