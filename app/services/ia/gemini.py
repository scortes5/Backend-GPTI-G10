import httpx

from app.exceptions import ServicioExternoNoDisponible
from app.services.ia.contexto import Contexto

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"


class GeminiAdapter:
    """Adapta la API REST de Google Gemini a la interfaz ProveedorIA (sin SDK: solo httpx)."""

    def __init__(self, api_key: str, modelo: str, cliente: httpx.Client | None = None):
        self._api_key = api_key
        self._modelo = modelo
        self._cliente = cliente or httpx.Client(timeout=30)

    def generar(self, instrucciones: str, consulta: str, contexto: Contexto | None = None) -> str:
        cuerpo = {
            "systemInstruction": {"parts": [{"text": instrucciones}]},
            "contents": [{"role": "user", "parts": [{"text": consulta}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
        }
        try:
            respuesta = self._cliente.post(
                URL.format(modelo=self._modelo), json=cuerpo, headers={"x-goog-api-key": self._api_key}
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ServicioExternoNoDisponible("El servicio de IA no está disponible") from error

        candidatos = datos.get("candidates") or []
        partes = (candidatos[0].get("content") or {}).get("parts", []) if candidatos else []
        texto = "".join(p.get("text", "") for p in partes).strip()
        if not texto:
            raise ServicioExternoNoDisponible("La IA no pudo generar una recomendación")
        return texto
