import pytest

from app.main import app
from app.services.correo import Correo, crear_servicio_correo

LOTE = {"productor": "Juan Pérez", "cultivo": "Arándano", "kilos": 100, "fecha_cosecha": "2026-10-01"}
VENTA = {"comprador": "Exportadora Sur", "kilos": 40, "precio_por_kilo": 2500, "fecha": "2026-10-05"}


class CorreoEspia:
    def __init__(self):
        self.enviados: list[Correo] = []

    def enviar(self, correo: Correo) -> None:
        self.enviados.append(correo)


@pytest.fixture
def espia():
    correo = CorreoEspia()
    app.dependency_overrides[crear_servicio_correo] = lambda: correo
    yield correo
    app.dependency_overrides.pop(crear_servicio_correo, None)


def test_envia_reporte_del_lote_con_csv_de_ventas(client, espia):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    client.post(f"/lotes/{codigo}/ventas", json=VENTA)

    respuesta = client.post(f"/lotes/{codigo}/reporte", json={"destinatario": "auditor@ejemplo.cl"})

    assert respuesta.status_code == 202
    correo = espia.enviados[0]
    assert correo.destinatario == "auditor@ejemplo.cl"
    assert codigo in correo.asunto
    assert "Kilos disponibles: 60" in correo.cuerpo
    csv = correo.adjuntos[0].contenido.decode()
    assert csv.splitlines() == ["fecha,comprador,kilos,precio_por_kilo", "2026-10-05,Exportadora Sur,40.0,2500.0"]


def test_rechaza_correo_invalido(client, espia):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    respuesta = client.post(f"/lotes/{codigo}/reporte", json={"destinatario": "no-es-correo"})
    assert respuesta.status_code == 422
    assert espia.enviados == []


def test_reporte_de_lote_inexistente(client, espia):
    respuesta = client.post("/lotes/noexiste/reporte", json={"destinatario": "auditor@ejemplo.cl"})
    assert respuesta.status_code == 404
