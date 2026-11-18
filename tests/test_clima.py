from datetime import datetime, timedelta

import pytest

from app.exceptions import ServicioExternoNoDisponible
from app.main import app
from app.models import Rol
from app.schemas import ResumenClimaOut
from app.services.clima import crear_proveedor_clima, estaciones
from app.services.clima.agromet import AgrometAdapter, interpretar
from app.services.clima.analisis import alertas
from app.services.clima.proveedor import Medicion
from app.services.clima.simulado import ProveedorClimaSimulado
from app.services.ia import crear_proveedor

TEMUCO = {"nombre": "Parcela Los Robles", "latitud": -38.74, "longitud": -72.60}

XML_AGROMET = """<?xml version="1.0"?>
<datos>
  <eje>1|°C|1</eje>
  <gra>1|Temperatura del Aire Mínima (°C)|1</gra>
  <gra>2|Temperatura del Aire Promedio (°C)|2</gra>
  <gra>3|Temperatura del Aire Máxima (°C)|3</gra>
  <gra>4|Humedad Relativa Promedio (%)|4</gra>
  <gra>5|Precipitación Horaria (mm)|5</gra>
  <gra>6|Dirección del Viento (°)|6</gra>
  <gra>7|Velocidad de Viento Máxima (km/h)|7</gra>
  <dato>0|2026-11-15 06:00:00|1|-1.2|2|0.4|3|1.5|4|92|5|0|6|180|7|8.5</dato>
  <dato>0|2026-11-15 05:00:00|1|-0.5|2|1.0|3|2.0|4|90|5|0.4|6|170|7|6</dato>
</datos>"""


class ProveedorFijo:
    """Clima conocido para probar las reglas sin depender del simulado."""

    nombre = "prueba"

    def __init__(self, temperatura=12.0, humedad=60.0, lluvia=0.0, viento=10.0):
        self.valores = dict(temperatura=temperatura, humedad=humedad, precipitacion=lluvia, viento=viento)

    def mediciones(self, estacion_id, desde, hasta):
        hora, salida = desde, []
        while hora <= hasta:
            salida.append(Medicion(fecha_hora=hora, **self.valores))
            hora += timedelta(hours=1)
        return salida


class ProveedorCaido:
    nombre = "agromet"

    def mediciones(self, *args):
        raise ServicioExternoNoDisponible("Agromet rechazó la consulta")


class IAEspia:
    def __init__(self):
        self.consultas = []

    def generar(self, instrucciones, consulta):
        self.consultas.append(consulta)
        return "- Cubrir los almácigos"


@pytest.fixture
def usar_clima():
    def _usar(proveedor):
        app.dependency_overrides[crear_proveedor_clima] = lambda: proveedor

    yield _usar
    app.dependency_overrides.pop(crear_proveedor_clima, None)


def test_estacion_mas_cercana():
    estacion, distancia = estaciones.mas_cercana(TEMUCO["latitud"], TEMUCO["longitud"])
    assert estacion.region == "Araucanía"
    assert distancia < 30
    assert len(estaciones.todas()) > 400


def test_sin_campo_responde_404(client):
    assert client.get("/campo").status_code == 404
    assert client.get("/clima").status_code == 404


def test_guardar_y_actualizar_campo(client):
    respuesta = client.put("/campo", json=TEMUCO)
    assert respuesta.status_code == 200
    assert respuesta.json()["productor"] == "Directiva"
    client.put("/campo", json={**TEMUCO, "nombre": "Otro nombre"})
    assert client.get("/campo").json()["nombre"] == "Otro nombre"


def test_campo_fuera_de_chile_se_rechaza(client):
    assert client.put("/campo", json={**TEMUCO, "latitud": 40.4, "longitud": -3.7}).status_code == 422


def test_clima_del_campo(client, usar_clima):
    usar_clima(ProveedorFijo(temperatura=-1.0, humedad=95, lluvia=1.0))
    client.put("/campo", json=TEMUCO)
    datos = client.get("/clima").json()
    assert datos["estacion"]["region"] == "Araucanía"
    assert datos["fuente"] == "prueba"
    assert len(datos["serie"]) == 48
    assert datos["resumen_24h"]["temperatura_min"] == -1.0
    assert datos["resumen_24h"]["precipitacion"] == 24.0
    titulos = [a["titulo"] for a in datos["alertas"]]
    assert "Helada" in titulos and "Lluvia intensa" in titulos


def test_proveedor_caido_responde_503(client, usar_clima):
    usar_clima(ProveedorCaido())
    client.put("/campo", json=TEMUCO)
    respuesta = client.get("/clima")
    assert respuesta.status_code == 503
    assert "Agromet" in respuesta.json()["detail"]


def test_productor_no_ve_campo_ajeno_pero_admin_si(client, crear_cliente, usar_clima):
    usar_clima(ProveedorFijo())
    productor = crear_cliente(Rol.PRODUCTOR, "María", "maria@coop.cl")
    productor.put("/campo", json=TEMUCO)
    id_maria = productor.get("/campo").json()["usuario_id"]
    otro = crear_cliente(Rol.PRODUCTOR, "Pedro", "pedro@coop.cl")
    assert otro.get(f"/clima?usuario_id={id_maria}").status_code == 403
    assert otro.get("/campos").status_code == 403
    assert client.get(f"/clima?usuario_id={id_maria}").json()["campo"]["productor"] == "María"
    assert [c["productor"] for c in client.get("/campos").json()] == ["María"]


def test_recomendacion_clima_incluye_alertas_y_bodega(crear_cliente, usar_clima):
    usar_clima(ProveedorFijo(temperatura=1.5))
    espia = IAEspia()
    app.dependency_overrides[crear_proveedor] = lambda: espia
    try:
        productor = crear_cliente(Rol.PRODUCTOR, "María", "maria@coop.cl")
        productor.put("/campo", json=TEMUCO)
        productor.post("/lotes", json={"productor": "x", "cultivo": "Papa", "kilos": 300, "fecha_cosecha": "2026-11-01"})
        respuesta = productor.get("/clima/recomendacion")
    finally:
        app.dependency_overrides.pop(crear_proveedor, None)
    assert respuesta.json()["texto"] == "- Cubrir los almácigos"
    consulta = espia.consultas[0]
    assert "Riesgo de helada" in consulta and "Papa 300 kg" in consulta and "Parcela Los Robles" in consulta


def test_alertas_por_reglas():
    ahora = datetime(2026, 11, 15, 12)
    actual = Medicion(fecha_hora=ahora, temperatura=20)
    resumen = ResumenClimaOut(temperatura_min=14, temperatura_max=34, precipitacion=0, humedad_media=50, viento_max=55)
    titulos = [a.titulo for a in alertas(resumen, actual, 5, ahora)]
    assert titulos == ["Calor intenso", "Viento fuerte"]
    titulos = [a.titulo for a in alertas(resumen, Medicion(fecha_hora=ahora - timedelta(hours=6)), 45, ahora)]
    assert "Sin datos recientes" in titulos and "Estación lejana" in titulos


def test_interpretar_respuesta_de_agromet():
    mediciones = interpretar(XML_AGROMET)
    assert [m.fecha_hora.hour for m in mediciones] == [5, 6]  # ordenadas
    ultima = mediciones[-1]
    assert (ultima.temperatura_min, ultima.temperatura, ultima.temperatura_max) == (-1.2, 0.4, 1.5)
    assert (ultima.humedad, ultima.precipitacion, ultima.viento) == (92, 0, 8.5)


def test_agromet_html_del_firewall_es_servicio_no_disponible():
    with pytest.raises(ServicioExternoNoDisponible):
        interpretar("<!DOCTYPE html><html><body>Web Application Firewall</body></html>")


def test_agromet_usa_cache(monkeypatch):
    adapter = AgrometAdapter("https://agromet.invalid/datos")
    llamadas = []
    monkeypatch.setattr(adapter, "_descargar", lambda *a: llamadas.append(a) or XML_AGROMET)
    desde, hasta = datetime(2026, 11, 14, 7, 10), datetime(2026, 11, 15, 6, 10)
    adapter.mediciones(108, desde, hasta)
    adapter.mediciones(108, desde, hasta)
    assert len(llamadas) == 1


def test_simulado_es_estable_y_plausible():
    desde, hasta = datetime(2026, 11, 14, 7), datetime(2026, 11, 15, 6)
    a = ProveedorClimaSimulado().mediciones(644, desde, hasta)
    b = ProveedorClimaSimulado().mediciones(644, desde, hasta)
    assert a == b and len(a) == 24
    assert all(-10 < m.temperatura < 40 and 0 <= m.humedad <= 100 for m in a)
