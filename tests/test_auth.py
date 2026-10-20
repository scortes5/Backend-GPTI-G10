import pytest

from app.db import get_db
from app.main import app
from app.models import Rol
from app.services import usuarios as usuarios_service


@pytest.fixture
def ana(client):
    db = next(app.dependency_overrides[get_db]())
    usuarios_service.crear(db, "Ana", "ana@coop.cl", "secreta123", Rol.PRODUCTOR)


def test_login_entrega_token_y_usuario(client, ana):
    respuesta = client.post("/auth/login", json={"email": "ana@coop.cl", "clave": "secreta123"})

    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"]["rol"] == "productor"
    token = respuesta.json()["access_token"]
    assert client.get("/auth/yo", headers={"Authorization": f"Bearer {token}"}).json()["nombre"] == "Ana"


def test_login_con_clave_incorrecta(client, ana):
    respuesta = client.post("/auth/login", json={"email": "ana@coop.cl", "clave": "mala"})
    assert respuesta.status_code == 401


def test_yo_sin_token(client):
    assert client.get("/auth/yo").status_code == 401


def test_yo_con_token_adulterado(client):
    assert client.get("/auth/yo", headers={"Authorization": "Bearer no-es-un-token"}).status_code == 401
