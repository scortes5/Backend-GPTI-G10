import io

import qrcode


def generar_png(contenido: str) -> io.BytesIO:
    buffer = io.BytesIO()
    qrcode.make(contenido).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
