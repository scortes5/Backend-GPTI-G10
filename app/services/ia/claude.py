import anthropic

from app.exceptions import ServicioExternoNoDisponible


class ClaudeAdapter:
    """Adapta el SDK de Anthropic a la interfaz ProveedorIA."""

    def __init__(self, api_key: str, modelo: str):
        self._cliente = anthropic.Anthropic(api_key=api_key)
        self._modelo = modelo

    def generar(self, instrucciones: str, consulta: str) -> str:
        try:
            respuesta = self._cliente.beta.messages.create(
                model=self._modelo,
                max_tokens=16000,
                system=instrucciones,
                messages=[{"role": "user", "content": consulta}],
                output_config={"effort": "medium"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except (anthropic.APIConnectionError, anthropic.APIStatusError) as error:
            raise ServicioExternoNoDisponible("El servicio de IA no está disponible") from error

        if respuesta.stop_reason == "refusal":
            raise ServicioExternoNoDisponible("La IA no pudo generar una recomendación")
        return "".join(bloque.text for bloque in respuesta.content if bloque.type == "text")
