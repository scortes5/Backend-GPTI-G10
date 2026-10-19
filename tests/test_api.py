LOTE = {"productor": "Juan Pérez", "cultivo": "Arándano", "kilos": 120.5, "fecha_cosecha": "2026-10-01"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_crear_y_obtener_lote(client):
    creado = client.post("/lotes", json=LOTE)
    assert creado.status_code == 201
    codigo = creado.json()["codigo"]

    assert client.get(f"/lotes/{codigo}").json()["productor"] == "Juan Pérez"
    assert len(client.get("/lotes").json()) == 1


def test_qr_lote(client):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]
    response = client.get(f"/lotes/{codigo}/qr")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_lote_inexistente(client):
    assert client.get("/lotes/noexiste").status_code == 404


def test_kilos_invalidos(client):
    assert client.post("/lotes", json={**LOTE, "kilos": 0}).status_code == 422


def test_productor_vacio(client):
    assert client.post("/lotes", json={**LOTE, "productor": "   "}).status_code == 422


def test_fecha_cosecha_futura(client):
    assert client.post("/lotes", json={**LOTE, "fecha_cosecha": "2999-01-01"}).status_code == 422
