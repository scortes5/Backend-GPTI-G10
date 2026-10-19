import pytest

from app.exceptions import ServicioExternoNoDisponible
from app.main import app
from app.services.ia import crear_proveedor
from app.services.ia.simulado import ProveedorSimulado

LOTE = {"productor": "Juan Pérez", "cultivo": "Arándano", "kilos": 100, "fecha_cosecha": "2026-10-01"}


class ProveedorEspia:
    def __init__(self):
        self.consultas: list[str] = []

    def generar(self, instrucciones: str, consulta: str) -> str:
        self.consultas.append(consulta)
        return "Vender pronto"


class ProveedorCaido:
    def generar(self, instrucciones: str, consulta: str) -> str:
        raise ServicioExternoNoDisponible("El servicio de IA no está disponible")


@pytest.fixture
def usar_proveedor():
    def _usar(proveedor):
        app.dependency_overrides[crear_proveedor] = lambda: proveedor

    yield _usar
    app.dependency_overrides.pop(crear_proveedor, None)


def test_recomendacion_usa_el_proveedor_inyectado(client, usar_proveedor):
    espia = ProveedorEspia()
    usar_proveedor(espia)
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]

    respuesta = client.get(f"/lotes/{codigo}/recomendacion")

    assert respuesta.json() == {"texto": "Vender pronto"}
    assert "Arándano" in espia.consultas[0]
    assert "disponibles 100 kg" in espia.consultas[0]


def test_recomendacion_con_proveedor_caido(client, usar_proveedor):
    usar_proveedor(ProveedorCaido())
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]

    assert client.get(f"/lotes/{codigo}/recomendacion").status_code == 503


def test_recomendacion_lote_inexistente(client, usar_proveedor):
    usar_proveedor(ProveedorEspia())
    assert client.get("/lotes/noexiste/recomendacion").status_code == 404


def test_proveedor_por_defecto_es_simulado():
    assert isinstance(crear_proveedor(), ProveedorSimulado)
