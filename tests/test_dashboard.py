LOTE = {"productor": "Juan Pérez", "cultivo": "Arándano", "kilos": 100, "fecha_cosecha": "2026-10-01"}
VENTA = {"comprador": "Exportadora Sur", "kilos": 40, "precio_por_kilo": 2500, "fecha": "2026-10-05"}


def test_resumen_sin_datos(client):
    resumen = client.get("/dashboard/resumen").json()

    assert resumen["total_lotes"] == 0
    assert resumen["ingresos"] == 0
    assert resumen["kilos_por_cultivo"] == {}


def test_resumen_con_lotes_y_ventas(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    client.post("/lotes", json={**LOTE, "cultivo": "Cereza", "kilos": 50})
    client.post(f"/lotes/{codigo}/ventas", json=VENTA)

    resumen = client.get("/dashboard/resumen").json()

    assert resumen["total_lotes"] == 2
    assert resumen["kilos_cosechados"] == 150
    assert resumen["kilos_vendidos"] == 40
    assert resumen["kilos_disponibles"] == 110
    assert resumen["ingresos"] == 100_000
    assert resumen["kilos_por_cultivo"] == {"Arándano": 100, "Cereza": 50}
