"""Lotes con predio, superficie, calidad y varias entregas; historial y anulación (C3, C4, C5)."""
LOTE = {
    "productor": "Juan Pérez", "cultivo": "Arándano", "predio": "El Roble", "superficie_ha": 1.5,
    "kilos": 100, "fecha_cosecha": "2026-10-01", "calidad": "extra",
}


def test_lote_guarda_predio_superficie_y_primera_entrega(client):
    lote = client.post("/lotes", json=LOTE).json()

    traza = client.get(f"/lotes/{lote['codigo']}/trazabilidad").json()

    assert lote["predio"] == "El Roble" and lote["superficie_ha"] == 1.5
    assert [(e["kilos"], e["calidad"]) for e in traza["entregas"]] == [(100, "extra")]


def test_varias_entregas_suman_al_lote(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]

    client.post(f"/lotes/{codigo}/entregas", json={"fecha": "2026-10-03", "kilos": 50, "calidad": "segunda"})

    assert client.get(f"/lotes/{codigo}").json()["kilos"] == 150


def test_entrega_rechaza_kilos_y_fecha_invalidos(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    assert client.post(f"/lotes/{codigo}/entregas", json={"fecha": "2026-10-03", "kilos": 0}).status_code == 422
    assert client.post(f"/lotes/{codigo}/entregas", json={"fecha": "2999-01-01", "kilos": 5}).status_code == 422
    assert client.post(f"/lotes/{codigo}/entregas", json={"fecha": "2026-10-03", "kilos": 5, "calidad": "mala"}).status_code == 422


def test_anular_entrega_la_descuenta_y_queda_en_el_historial(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    entrega = client.post(f"/lotes/{codigo}/entregas", json={"fecha": "2026-10-03", "kilos": 50}).json()

    client.post(f"/lotes/{codigo}/entregas/{entrega['id']}/anular", json={"motivo": "Kilos mal anotados"})

    traza = client.get(f"/lotes/{codigo}/trazabilidad").json()
    assert traza["lote"]["kilos"] == 100
    assert len(traza["entregas"]) == 2
    anulacion = traza["historial"][-1]
    assert (anulacion["entidad"], anulacion["accion"], anulacion["motivo"]) == ("entrega", "anulado", "Kilos mal anotados")
    assert anulacion["usuario_nombre"] == "Directiva"


def test_no_se_anula_la_unica_entrega(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    entrega_id = client.get(f"/lotes/{codigo}/trazabilidad").json()["entregas"][0]["id"]
    assert client.post(f"/lotes/{codigo}/entregas/{entrega_id}/anular", json={"motivo": "Error"}).status_code == 409


def test_edicion_queda_registrada_con_usuario_fecha_y_motivo(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]

    client.patch(f"/lotes/{codigo}", json={"cultivo": "Frutilla", "motivo": "Se anotó mal el cultivo"})

    cambio = client.get(f"/lotes/{codigo}/trazabilidad").json()["historial"][-1]
    assert cambio["accion"] == "editado"
    assert cambio["detalle"] == "cultivo: Arándano → Frutilla"
    assert cambio["motivo"] == "Se anotó mal el cultivo"
    assert cambio["fecha"]


def test_lote_anulado_no_se_borra_ni_admite_cambios(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]

    anulado = client.post(f"/lotes/{codigo}/anular", json={"motivo": "Lote duplicado"}).json()

    assert anulado["estado"] == "anulado" and anulado["motivo_anulacion"] == "Lote duplicado"
    assert client.patch(f"/lotes/{codigo}", json={"cultivo": "Ajo", "motivo": "x" * 5}).status_code == 409
    assert client.post(f"/lotes/{codigo}/ventas", json={"comprador": "A", "kilos": 1, "precio_por_kilo": 1, "fecha": "2026-10-05"}).status_code == 409
    assert client.get("/dashboard/resumen").json()["kilos_cosechados"] == 0


def test_anular_exige_motivo(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    assert client.post(f"/lotes/{codigo}/anular", json={"motivo": ""}).status_code == 422


def test_filtros_por_fecha_estado_y_cultivo(client):
    client.post("/lotes", json=LOTE)
    viejo = client.post("/lotes", json={**LOTE, "cultivo": "Papa", "fecha_cosecha": "2026-03-01"}).json()["codigo"]
    client.post(f"/lotes/{viejo}/anular", json={"motivo": "Prueba"})

    assert len(client.get("/lotes", params={"desde": "2026-09-01"}).json()) == 1
    assert [l["codigo"] for l in client.get("/lotes", params={"estado": "anulado"}).json()] == [viejo]
    assert len(client.get("/lotes", params={"cultivo": "arándano"}).json()) == 1


def test_ficha_publica_muestra_entregas_y_estado_sin_precios(client, anonimo):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    client.post(f"/lotes/{codigo}/ventas", json={"comprador": "Exportadora", "kilos": 10, "precio_por_kilo": 3000, "fecha": "2026-10-05"})

    ficha = anonimo.get(f"/publico/lotes/{codigo}").json()

    assert ficha["estado"] == "vigente"
    assert ficha["entregas"] == [{"fecha": "2026-10-01", "kilos": 100, "calidad": "extra"}]
    assert "ventas" not in ficha and "Exportadora" not in str(ficha) and "3000" not in str(ficha)


def test_descarga_reporte_pdf_y_csv(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    client.patch(f"/lotes/{codigo}", json={"predio": "Los Notros", "motivo": "Cambio de predio"})

    pdf = client.get(f"/lotes/{codigo}/reporte.pdf")
    csv = client.get(f"/lotes/{codigo}/reporte.csv")

    assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
    texto = csv.content.decode("utf-8-sig")
    assert "entrega;2026-10-01" in texto
    assert "Cambio de predio" in texto


def test_productor_no_descarga_reporte_ajeno(client, productor):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    assert productor.get(f"/lotes/{codigo}/reporte.pdf").status_code == 403
