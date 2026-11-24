"""Los adapters reales contra las APIs simuladas, y las reglas de la IA simulada."""
from datetime import datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.exceptions import ServicioExternoNoDisponible
from app.main import app
from app.models import Rol
from app.services.clima import crear_proveedor_clima
from app.services.clima.agromet import AgrometAdapter
from app.services.clima.analisis import resumir
from app.services.ia.contexto import ContextoCampo, ContextoLote, LoteEnBodega
from app.services.ia.simulado import ProveedorSimulado
from app.services.sensores import crear_proveedor_sensores
from app.services.sensores.instacrops import InstacropsAdapter, interpretar
from simuladores import main as simuladores

BASE = "http://simuladores"
TEMUCO = {"nombre": "Parcela Los Robles", "latitud": -38.74, "longitud": -72.60}
IA = ProveedorSimulado()


@pytest.fixture
def apis(monkeypatch):
    """Dirige los httpx.get de los adapters a las APIs simuladas y a sus proveedores en la app."""
    cliente = TestClient(simuladores.app)
    monkeypatch.setattr(httpx, "get", lambda url, params=None, headers=None, timeout=None: cliente.get(url, params=params, headers=headers))
    simuladores.estado["escenario"] = "normal"
    clima = AgrometAdapter(f"{BASE}/agromet/getGraphData.php", 0, nombre="simulado")
    sensores = InstacropsAdapter(f"{BASE}/instacrops", "demo", 0, nombre="simulado")
    app.dependency_overrides[crear_proveedor_clima] = lambda: clima
    app.dependency_overrides[crear_proveedor_sensores] = lambda: sensores
    yield cliente
    app.dependency_overrides.pop(crear_proveedor_clima, None)
    app.dependency_overrides.pop(crear_proveedor_sensores, None)
    simuladores.estado["escenario"] = "normal"


def _con_escenario(apis, nombre):
    assert apis.put(f"/escenario/{nombre}").status_code == 200


def _titulos(datos):
    return [a["titulo"] for a in datos["alertas"]]


def test_agromet_simulado_se_lee_con_el_adapter_real(apis):
    hasta = datetime(2026, 11, 18, 12)
    adapter = AgrometAdapter(f"{BASE}/agromet/getGraphData.php", 0)
    a = adapter.mediciones(644, hasta - timedelta(hours=23), hasta)
    assert len(a) == 24 and a == adapter.mediciones(644, hasta - timedelta(hours=23), hasta)
    assert all(m.temperatura is not None and m.viento is not None for m in a)
    _con_escenario(apis, "helada")
    assert resumir(adapter.mediciones(644, hasta - timedelta(hours=23), hasta)).temperatura_min <= 0


def test_instacrops_simulado_exige_token(apis):
    assert apis.get("/instacrops/v1/lecturas", params={"latitud": -38, "longitud": -72}).status_code == 401
    with pytest.raises(ServicioExternoNoDisponible, match="credencial"):
        InstacropsAdapter(f"{BASE}/instacrops", "mala", 0).lecturas(-38, -72)


def test_escenario_desconocido(apis):
    assert apis.put("/escenario/terremoto").status_code == 404


@pytest.mark.parametrize("datos", [{}, {"dispositivo": "x", "lecturas": [{"fecha_hora": "ayer"}]}, {"dispositivo": "x", "lecturas": 3}])
def test_respuesta_rara_de_instacrops(datos):
    with pytest.raises(ServicioExternoNoDisponible):
        interpretar(datos)


@pytest.mark.parametrize("escenario, alerta, texto", [
    ("helada", "Helada", "**Helada"),
    ("lluvia", "Suelo saturado", "no riegues"),
    ("sequia", "Suelo seco", "prioriza el riego"),
])
def test_escenarios_cambian_alertas_y_recomendacion(apis, client, escenario, alerta, texto):
    client.put("/campo", json=TEMUCO)
    _con_escenario(apis, escenario)
    datos = client.get("/clima").json()
    assert datos["fuente"] == "simulado" and datos["sensores"]["fuente"] == "simulado"
    assert alerta in _titulos(datos)
    recomendacion = client.get("/clima/recomendacion").json()["texto"]
    assert "IA simulada" in recomendacion and texto in recomendacion


def test_sin_instacrops_el_clima_sigue_funcionando(apis, client):
    client.put("/campo", json=TEMUCO)
    _con_escenario(apis, "sin_instacrops")
    datos = client.get("/clima").json()
    assert datos["sensores"] is None and "Instacrops" in datos["aviso_sensores"]
    assert client.get("/clima/recomendacion").status_code == 200


def test_sin_agromet_responde_503(apis, client):
    client.put("/campo", json=TEMUCO)
    _con_escenario(apis, "sin_agromet")
    assert client.get("/clima").status_code == 503


def test_lectura_antigua_no_se_usa_para_recomendar(apis, crear_cliente, monkeypatch):
    from app.services.sensores import DatosSensores, LecturaSensor

    vieja = DatosSensores("IC-1", [LecturaSensor(datetime.now() - timedelta(hours=8), 10, 12)])
    sensores = type("Sensores", (), {"nombre": "prueba", "lecturas": lambda self, *a, **k: vieja})()
    app.dependency_overrides[crear_proveedor_sensores] = lambda: sensores
    productor = crear_cliente(Rol.PRODUCTOR, "María", "maria@coop.cl")
    productor.put("/campo", json=TEMUCO)
    datos = productor.get("/clima").json()
    assert datos["sensores"]["reciente"] is False
    assert "Sensores sin datos recientes" in _titulos(datos) and "Suelo seco" not in _titulos(datos)
    assert "Suelo seco" not in productor.get("/clima/recomendacion").json()["texto"]


def test_ia_simulada_cruza_clima_suelo_y_bodega():
    contexto = ContextoCampo(
        temperatura_min=-2, temperatura_max=8, lluvia_24h=30, humedad_media=90, humedad_suelo=95,
        lotes=(LoteEnBodega("Papa", 300, 10), LoteEnBodega("Arándano", 40, 9)),
    )
    texto = IA.generar("", "", contexto)
    assert texto == IA.generar("", "", contexto)
    lineas = texto.splitlines()
    assert "IA simulada" in lineas[0] and len(lineas) <= 7
    assert "Helada (-2 °C)" in lineas[1] and "Suelo saturado tras 30 mm" in lineas[2]
    assert texto.index("Arándano") < texto.index("Papa")  # primero lo que está más cerca de perderse
    assert "ya pasó su tiempo habitual" in texto and "Protege la cosecha del frío" in texto


def test_ia_simulada_agrupa_lotes_del_mismo_cultivo():
    lotes = (LoteEnBodega("Papa nativa", 300, 3), LoteEnBodega("papa nativa", 80, 12))
    texto = IA.generar("", "", ContextoCampo(lotes=lotes))
    assert texto.count("en bodega") == 1 and "380 kg, hasta 12 días" in texto


def test_ia_simulada_sin_sensor_no_inventa_suelo():
    texto = IA.generar("", "", ContextoCampo(temperatura_min=10, temperatura_max=27, humedad_media=50))
    assert "no hay lectura del sensor" in texto and "Suelo seco" not in texto


@pytest.mark.parametrize("contexto, esperado", [
    (ContextoLote("Frutilla", 100, 60, 8), "Venta prioritaria"),
    (ContextoLote("Papa", 100, 100, 5), "dentro de lo habitual"),
    (ContextoLote("Papa", 100, 0, 5), "vendido por completo"),
])
def test_ia_simulada_por_lote(contexto, esperado):
    assert esperado in IA.generar("", "", contexto)
