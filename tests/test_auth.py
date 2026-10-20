LOTE = {"productor": "X", "cultivo": "Arándano", "kilos": 100, "fecha_cosecha": "2026-10-01"}


def test_login_entrega_token_y_usuario(anonimo, productor):
    respuesta = anonimo.post("/auth/login", json={"email": "ana@coop.cl", "clave": "clave-segura"})

    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"]["rol"] == "productor"
    token = respuesta.json()["access_token"]
    assert anonimo.get("/auth/yo", headers={"Authorization": f"Bearer {token}"}).json()["nombre"] == "Ana Huenchul"


def test_login_con_clave_incorrecta(anonimo, productor):
    respuesta = anonimo.post("/auth/login", json={"email": "ana@coop.cl", "clave": "mala"})
    assert respuesta.status_code == 401


def test_yo_sin_token(anonimo):
    assert anonimo.get("/auth/yo").status_code == 401


def test_yo_con_token_adulterado(anonimo):
    assert anonimo.get("/auth/yo", headers={"Authorization": "Bearer no-es-un-token"}).status_code == 401


def test_endpoints_privados_exigen_sesion(anonimo):
    assert anonimo.get("/lotes").status_code == 401
    assert anonimo.get("/dashboard/resumen").status_code == 401


def test_productor_crea_lotes_a_su_nombre(productor):
    lote = productor.post("/lotes", json=LOTE).json()
    assert lote["productor"] == "Ana Huenchul"


def test_productor_solo_ve_sus_lotes(client, productor):
    codigo_ajeno = client.post("/lotes", json=LOTE).json()["codigo"]
    productor.post("/lotes", json=LOTE)

    assert len(productor.get("/lotes").json()) == 1
    assert len(client.get("/lotes").json()) == 2
    assert productor.get(f"/lotes/{codigo_ajeno}/trazabilidad").status_code == 403
    assert productor.get("/dashboard/resumen").json()["total_lotes"] == 1


def test_solo_admin_elimina_lotes(productor):
    codigo = productor.post("/lotes", json=LOTE).json()["codigo"]
    assert productor.delete(f"/lotes/{codigo}").status_code == 403


def test_ficha_publica_sin_sesion_no_expone_ventas(client, anonimo):
    codigo = client.post("/lotes", json=LOTE).json()["codigo"]

    ficha = anonimo.get(f"/publico/lotes/{codigo}")

    assert ficha.status_code == 200
    assert ficha.json()["cultivo"] == "Arándano"
    assert "ventas" not in ficha.json()
    assert anonimo.get(f"/lotes/{codigo}/qr").status_code == 200


def test_login_tarda_lo_mismo_exista_o_no_el_correo(anonimo, productor):
    import time

    def medir(email: str) -> float:
        inicio = time.perf_counter()
        anonimo.post("/auth/login", json={"email": email, "clave": "incorrecta"})
        return time.perf_counter() - inicio

    existe, no_existe = medir("ana@coop.cl"), medir("nadie@coop.cl")
    assert no_existe > existe / 3


def test_token_sin_expiracion_se_rechaza(anonimo):
    import jwt

    from app.services import tokens

    sin_exp = jwt.encode({"sub": "1"}, tokens._CLAVE, algorithm="HS256")
    assert anonimo.get("/auth/yo", headers={"Authorization": f"Bearer {sin_exp}"}).status_code == 401


def test_token_con_algoritmo_none_se_rechaza(anonimo):
    import jwt

    sin_firma = jwt.encode({"sub": "1", "exp": 9999999999}, None, algorithm="none")
    assert anonimo.get("/auth/yo", headers={"Authorization": f"Bearer {sin_firma}"}).status_code == 401
