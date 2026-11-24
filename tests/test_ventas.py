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


def test_no_se_anula_una_entrega_si_quedan_menos_kilos_que_lo_vendido(client):
    codigo = crear_lote(client)
    entrega = client.post(f"/lotes/{codigo}/entregas", json={"fecha": "2026-10-02", "kilos": 20}).json()
    client.post(f"/lotes/{codigo}/ventas", json={**VENTA, "kilos": 110})

    respuesta = client.post(f"/lotes/{codigo}/entregas/{entrega['id']}/anular", json={"motivo": "Mal pesada"})

    assert respuesta.status_code == 409
    assert client.get(f"/lotes/{codigo}").json()["kilos"] == 120


def test_anular_venta_devuelve_los_kilos(client):
    codigo = crear_lote(client)
    venta = client.post(f"/lotes/{codigo}/ventas", json=VENTA).json()

    anulada = client.post(f"/lotes/{codigo}/ventas/{venta['id']}/anular", json={"motivo": "Comprador desistió"})

    assert anulada.json()["estado"] == "anulado"
    traza = client.get(f"/lotes/{codigo}/trazabilidad").json()
    assert traza["kilos_disponibles"] == 100
    assert traza["ingresos"] == 0
    assert len(traza["ventas"]) == 1  # sigue en el historial


def test_lote_con_ventas_vigentes_no_se_anula(client):
    codigo = crear_lote(client)
    client.post(f"/lotes/{codigo}/ventas", json=VENTA)

    assert client.post(f"/lotes/{codigo}/anular", json={"motivo": "Error"}).status_code == 409


def test_trazabilidad_resume_ventas_del_lote(client):
    codigo = crear_lote(client)
    client.post(f"/lotes/{codigo}/ventas", json=VENTA)

    traza = client.get(f"/lotes/{codigo}/trazabilidad").json()

    assert traza["lote"]["codigo"] == codigo
    assert traza["kilos_vendidos"] == 40
    assert traza["kilos_disponibles"] == 60
    assert traza["ingresos"] == 40 * 2500
    assert len(traza["ventas"]) == 1
