LOTE = {"productor": "Juan Pérez", "cultivo": "Arándano", "kilos": 100, "fecha_cosecha": "2026-10-01"}
VENTA = {"comprador": "Exportadora Sur", "kilos": 40, "precio_por_kilo": 2500, "fecha": "2026-10-05"}


def crear_lote(client) -> str:
    return client.post("/lotes", json=LOTE).json()["codigo"]


def test_registrar_y_listar_ventas(client):
    codigo = crear_lote(client)

    assert client.post(f"/lotes/{codigo}/ventas", json=VENTA).status_code == 201
    ventas = client.get(f"/lotes/{codigo}/ventas").json()

    assert [v["comprador"] for v in ventas] == ["Exportadora Sur"]


def test_no_se_puede_vender_mas_de_lo_disponible(client):
    codigo = crear_lote(client)
    client.post(f"/lotes/{codigo}/ventas", json=VENTA)

    respuesta = client.post(f"/lotes/{codigo}/ventas", json={**VENTA, "kilos": 61})

    assert respuesta.status_code == 409


def test_venta_anterior_a_la_cosecha(client):
    codigo = crear_lote(client)
    respuesta = client.post(f"/lotes/{codigo}/ventas", json={**VENTA, "fecha": "2026-09-30"})
    assert respuesta.status_code == 409


def test_venta_en_lote_inexistente(client):
    assert client.post("/lotes/noexiste/ventas", json=VENTA).status_code == 404


def test_no_se_puede_reducir_lote_bajo_lo_vendido(client):
    codigo = crear_lote(client)
    client.post(f"/lotes/{codigo}/ventas", json=VENTA)

    assert client.patch(f"/lotes/{codigo}", json={"kilos": 30}).status_code == 409
    assert client.get(f"/lotes/{codigo}").json()["kilos"] == 100


def test_eliminar_lote_elimina_sus_ventas(client):
    codigo = crear_lote(client)
    client.post(f"/lotes/{codigo}/ventas", json=VENTA)

    assert client.delete(f"/lotes/{codigo}").status_code == 204


def test_trazabilidad_resume_ventas_del_lote(client):
    codigo = crear_lote(client)
    client.post(f"/lotes/{codigo}/ventas", json=VENTA)

    traza = client.get(f"/lotes/{codigo}/trazabilidad").json()

    assert traza["lote"]["codigo"] == codigo
    assert traza["kilos_vendidos"] == 40
    assert traza["kilos_disponibles"] == 60
    assert traza["ingresos"] == 40 * 2500
    assert len(traza["ventas"]) == 1
