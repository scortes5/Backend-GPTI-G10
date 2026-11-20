"""Dashboard con filtros y la métrica de la cola sin conexión (C6, solicitud de cambio N°2)."""
import time

from app.models import Rol

LOTE = {"productor": "Juan", "cultivo": "Arándano", "kilos": 100, "fecha_cosecha": "2026-10-01"}
VENTA = {"comprador": "Exportadora Sur", "kilos": 40, "precio_por_kilo": 2500, "fecha": "2026-10-05"}


def test_filtra_por_periodo_cultivo_y_socio(client, crear_cliente):
    socio = crear_cliente(Rol.PRODUCTOR, "Ana", "ana@coop.cl")
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    client.post(f"/lotes/{codigo}/ventas", json=VENTA)
    socio.post("/lotes", json={**LOTE, "cultivo": "Papa", "fecha_cosecha": "2026-11-01"})
    ana_id = socio.get("/auth/yo").json()["id"]

    octubre = client.get("/dashboard/resumen", params={"desde": "2026-10-01", "hasta": "2026-10-31"}).json()
    papa = client.get("/dashboard/resumen", params={"cultivo": "papa"}).json()
    de_ana = client.get("/dashboard/resumen", params={"usuario_id": ana_id}).json()

    assert (octubre["kilos_cosechados"], octubre["total_ventas"], octubre["ingresos"]) == (100, 1, 100_000)
    assert papa["kilos_por_cultivo"] == {"Papa": 100}
    assert (de_ana["total_lotes"], de_ana["total_ventas"]) == (1, 0)


def test_productor_no_puede_ver_otro_socio(client, productor):
    client.post("/lotes", json=LOTE)
    assert productor.get("/dashboard/resumen", params={"usuario_id": 1}).json()["total_lotes"] == 0


def test_resumen_cuenta_recomendaciones(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    client.get(f"/lotes/{codigo}/recomendacion")

    resumen = client.get("/dashboard/resumen").json()["recomendaciones"]

    assert resumen["total"] == 1 and resumen["ultima"]["lote_codigo"] == codigo


def _cabeceras(evento_id, hace_segundos, en_cola=True):
    creado = int((time.time() - hace_segundos) * 1000)
    return {"X-Evento-Id": evento_id, "X-Evento-Creado": str(creado), "X-Cola": "1" if en_cola else "0"}


def test_reintento_de_la_cola_no_duplica_el_lote(client):
    cabeceras = _cabeceras("evento-1", 120)

    primero = client.post("/lotes", json=LOTE, headers=cabeceras)
    segundo = client.post("/lotes", json=LOTE, headers=cabeceras)

    assert primero.json()["codigo"] == segundo.json()["codigo"]
    assert len(client.get("/lotes").json()) == 1


def test_reintento_de_la_cola_no_descuenta_dos_veces_la_venta(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    cabeceras = _cabeceras("venta-1", 30)

    client.post(f"/lotes/{codigo}/ventas", json=VENTA, headers=cabeceras)
    client.post(f"/lotes/{codigo}/ventas", json=VENTA, headers=cabeceras)

    assert client.get(f"/lotes/{codigo}/trazabilidad").json()["kilos_vendidos"] == 40


def test_dashboard_muestra_el_tiempo_promedio_de_llegada(client):
    client.post("/lotes", json=LOTE, headers=_cabeceras("a", 600))
    client.post("/lotes", json=LOTE, headers=_cabeceras("b", 1200))
    client.post("/lotes", json=LOTE, headers=_cabeceras("c", 0, en_cola=False))

    cola = client.get("/dashboard/resumen").json()["cola"]

    assert (cola["eventos"], cola["en_cola"]) == (3, 2)
    assert 895 <= cola["promedio_cola_segundos"] <= 910
    assert 1195 <= cola["maximo_segundos"] <= 1210


def test_fecha_de_creacion_absurda_no_distorsiona_la_metrica(client):
    client.post("/lotes", json=LOTE, headers={"X-Evento-Id": "x", "X-Evento-Creado": "1000", "X-Cola": "1"})
    assert client.get("/dashboard/resumen").json()["cola"]["maximo_segundos"] < 5
