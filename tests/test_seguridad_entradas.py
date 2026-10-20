"""Entradas maliciosas: SQL injection y caracteres de control.

Todas las consultas usan el ORM de SQLAlchemy con parámetros enlazados (nunca SQL armado con
strings), así que estos textos se guardan o buscan literalmente y no se ejecutan.
"""
import pytest

LOTE = {"productor": "Juan", "cultivo": "Arándano", "kilos": 100, "fecha_cosecha": "2026-10-01"}
INYECCIONES = ["' OR '1'='1", "x'; DROP TABLE lotes; --", "1 UNION SELECT clave_hash FROM usuarios --"]


@pytest.mark.parametrize("codigo", INYECCIONES)
def test_codigo_con_sql_no_expone_lotes(client, codigo):
    client.post("/lotes", json=LOTE)

    assert client.get(f"/lotes/{codigo}").status_code == 404
    assert client.get(f"/publico/lotes/{codigo}").status_code == 404
    assert len(client.get("/lotes").json()) == 1


@pytest.mark.parametrize("texto", INYECCIONES)
def test_texto_con_sql_se_guarda_literal(client, texto):
    lote = client.post("/lotes", json={**LOTE, "cultivo": texto}).json()

    assert client.get(f"/lotes/{lote['codigo']}").json()["cultivo"] == texto
    assert len(client.get("/lotes").json()) == 1


@pytest.mark.parametrize("email", ["admin@coop.cl' OR '1'='1", "' OR 1=1 --@coop.cl"])
def test_login_con_sql_no_entra(anonimo, client, email):
    respuesta = anonimo.post("/auth/login", json={"email": email, "clave": "' OR '1'='1"})
    assert respuesta.status_code in (401, 422)


def test_productor_con_sql_no_ve_lotes_ajenos(client, productor):
    client.post("/lotes", json=LOTE)
    assert productor.get("/lotes", params={"usuario_id": "1 OR 1=1"}).json() == []


@pytest.mark.parametrize("campo", ["productor", "cultivo"])
def test_rechaza_saltos_de_linea_en_textos(client, campo):
    respuesta = client.post("/lotes", json={**LOTE, campo: "Arándano\r\nBcc: spam@ejemplo.cl"})
    assert respuesta.status_code == 422
