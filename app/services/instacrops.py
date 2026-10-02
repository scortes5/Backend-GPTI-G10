"""Cliente mínimo para la API privada de Instacrops (Fase 2)."""
from app.config import settings


def get(path: str, params: dict | None = None) -> dict:
    import httpx

    with httpx.Client(
        base_url=settings.instacrops_api_url,
        headers={"Authorization": f"Bearer {settings.instacrops_api_key}"},
        timeout=15,
    ) as client:
        response = client.get(path, params=params)
        response.raise_for_status()
        return response.json()
