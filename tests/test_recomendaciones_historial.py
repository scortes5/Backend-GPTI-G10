"""Historial de recomendaciones, datos usados, límite diario e interruptor (C7, LA-G10-05)."""
import httpx
import pytest

from app.config import settings
from app.exceptions import ServicioExternoNoDisponible
from app.services.ia.gemini import GeminiAdapter

LOTE = {"productor": "Juan", "cultivo": "Arándano", "kilos": 100, "fecha_cosecha": "2026-10-01"}


@pytest.fixture
def limite(monkeypatch):
    def _poner(valor):
        monkeypatch.setattr(settings, "ia_limite_diario", valor)
    return _poner


def test_recomendacion_muestra_los_datos_usados_y_se_guarda(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]

    recomendacion = client.get(f"/lotes/{codigo}/recomendacion").json()
    historial = client.get(f"/lotes/{codigo}/recomendaciones").json()

    datos = {d["dato"]: d["valor"] for d in recomendacion["datos_usados"]}
    assert datos["Cultivo"] == "Arándano" and datos["Kilos disponibles"] == "100 kg"
    assert recomendacion["proveedor"] == "simulado"
    assert [r["id"] for r in historial] == [recomendacion["id"]]


def test_limite_diario_configurable(client, limite):
    limite(2)
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]

    respuestas = [client.get(f"/lotes/{codigo}/recomendacion") for _ in range(3)]

    assert [r.status_code for r in respuestas] == [200, 200, 429]
    assert respuestas[1].json()["consultas_restantes"] == 0


def test_interruptor_desactiva_la_ia(client, monkeypatch):
    monkeypatch.setattr(settings, "ia_habilitada", False)
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    assert client.get(f"/lotes/{codigo}/recomendacion").status_code == 503


def test_productor_solo_ve_su_historial(client, productor):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    client.get(f"/lotes/{codigo}/recomendacion")

    assert productor.get("/recomendaciones").json() == []
    assert len(client.get("/recomendaciones").json()) == 1


def _gemini(respuesta: httpx.Response) -> GeminiAdapter:
    return GeminiAdapter("clave", "gemini-2.5-flash", httpx.Client(transport=httpx.MockTransport(lambda _: respuesta)))


def test_gemini_devuelve_el_texto():
    cuerpo = {"candidates": [{"content": {"parts": [{"text": "- Vender esta semana"}]}}]}
    assert _gemini(httpx.Response(200, json=cuerpo)).generar("inst", "consulta") == "- Vender esta semana"


@pytest.mark.parametrize("respuesta", [httpx.Response(429, json={}), httpx.Response(200, json={"candidates": []})])
def test_gemini_sin_respuesta_util(respuesta):
    with pytest.raises(ServicioExternoNoDisponible):
        _gemini(respuesta).generar("inst", "consulta")
