from fastapi import APIRouter, HTTPException

from app.services import instacrops

router = APIRouter(prefix="/instacrops", tags=["instacrops"])


@router.get("/{path:path}")
def proxy(path: str):
    """Reenvía un GET a Instacrops. Reemplazar por endpoints concretos cuando exista la spec."""
    import httpx

    try:
        return instacrops.get(f"/{path}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, e.response.text)
    except httpx.RequestError as e:
        raise HTTPException(502, f"Instacrops no disponible: {e}")
