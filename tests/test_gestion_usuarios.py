NUEVO = {"nombre": "Pedro Lienlaf", "email": "pedro@coop.cl", "clave": "clave-segura", "rol": "productor"}


def test_admin_crea_productor_que_puede_iniciar_sesion(client, anonimo):
    assert client.post("/usuarios", json=NUEVO).status_code == 201

    login = anonimo.post("/auth/login", json={"email": "pedro@coop.cl", "clave": "clave-segura"})

    assert login.status_code == 200
    assert [u["email"] for u in client.get("/usuarios").json()] == ["admin@coop.cl", "pedro@coop.cl"]


def test_clave_corta_se_rechaza(client):
    assert client.post("/usuarios", json={**NUEVO, "clave": "corta"}).status_code == 422


def test_admin_desactiva_usuario_y_pierde_acceso(client, anonimo):
    usuario_id = client.post("/usuarios", json=NUEVO).json()["id"]

    assert client.patch(f"/usuarios/{usuario_id}", json={"activo": False}).json()["activo"] is False
    login = anonimo.post("/auth/login", json={"email": "pedro@coop.cl", "clave": "clave-segura"})
    assert login.status_code == 401


def test_admin_no_puede_desactivarse_a_si_mismo(client):
    propio_id = client.get("/auth/yo").json()["id"]
    assert client.patch(f"/usuarios/{propio_id}", json={"activo": False}).status_code == 409


def test_productor_no_gestiona_usuarios(productor):
    assert productor.get("/usuarios").status_code == 403
    assert productor.post("/usuarios", json=NUEVO).status_code == 403
