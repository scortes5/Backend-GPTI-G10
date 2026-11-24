"""RUT validado, credenciales por correo y edición de nombre y correo (C1, C2)."""
import pytest

from app.exceptions import ServicioExternoNoDisponible
from app.main import app
from app.schemas import normalizar_rut
from app.services.correo import crear_servicio_correo

NUEVO = {"nombre": "Pedro Lienlaf", "email": "pedro@coop.cl", "rut": "12.345.678-5", "rol": "productor"}


class CorreoEspia:
    def __init__(self, falla=False):
        self.enviados, self.falla = [], falla

    def enviar(self, correo):
        if self.falla:
            raise ServicioExternoNoDisponible("SMTP caído")
        self.enviados.append(correo)


@pytest.fixture
def correo():
    espia = CorreoEspia()
    app.dependency_overrides[crear_servicio_correo] = lambda: espia
    yield espia
    app.dependency_overrides.pop(crear_servicio_correo, None)


@pytest.mark.parametrize("entrada, normalizado", [("12.345.678-5", "12345678-5"), ("123456785", "12345678-5"), ("7.654.321-6", "7654321-6"), ("10.000.013-k", "10000013-K")])
def test_rut_valido_se_normaliza(entrada, normalizado):
    assert normalizar_rut(entrada) == normalizado


@pytest.mark.parametrize("rut", ["12.345.678-9", "abc", "1-9", ""])
def test_rut_invalido(client, correo, rut):
    assert client.post("/usuarios", json={**NUEVO, "rut": rut}).status_code == 422


def test_credenciales_se_envian_por_correo(client, correo, anonimo):
    creado = client.post("/usuarios", json=NUEVO).json()

    assert creado["credenciales_enviadas"] is True and creado["rut"] == "12345678-5"
    mensaje = correo.enviados[0]
    assert mensaje.destinatario == "pedro@coop.cl"
    clave = mensaje.cuerpo.split("Contraseña inicial: ")[1].split("\n")[0]
    assert anonimo.post("/auth/login", json={"email": "pedro@coop.cl", "clave": clave}).status_code == 200


def test_si_el_correo_falla_el_usuario_igual_se_crea(client):
    app.dependency_overrides[crear_servicio_correo] = lambda: CorreoEspia(falla=True)
    try:
        respuesta = client.post("/usuarios", json=NUEVO)
    finally:
        app.dependency_overrides.pop(crear_servicio_correo, None)
    assert respuesta.status_code == 201 and respuesta.json()["credenciales_enviadas"] is False


def test_rut_repetido(client, correo):
    client.post("/usuarios", json=NUEVO)
    assert client.post("/usuarios", json={**NUEVO, "email": "otro@coop.cl"}).status_code == 409


def test_admin_edita_nombre_y_correo(client, correo, anonimo):
    usuario_id = client.post("/usuarios", json={**NUEVO, "clave": "clave-segura"}).json()["id"]

    editado = client.patch(f"/usuarios/{usuario_id}", json={"nombre": "Pedro Lienlaf Ñancul", "email": "PLienlaf@coop.cl"}).json()

    assert (editado["nombre"], editado["email"]) == ("Pedro Lienlaf Ñancul", "plienlaf@coop.cl")
    assert anonimo.post("/auth/login", json={"email": "plienlaf@coop.cl", "clave": "clave-segura"}).status_code == 200


def test_no_se_repite_el_correo_al_editar(client, correo):
    usuario_id = client.post("/usuarios", json=NUEVO).json()["id"]
    assert client.patch(f"/usuarios/{usuario_id}", json={"email": "admin@coop.cl"}).status_code == 409


def test_admin_puede_editar_su_propio_nombre(client):
    propio_id = client.get("/auth/yo").json()["id"]
    assert client.patch(f"/usuarios/{propio_id}", json={"nombre": "Directiva Newen"}).status_code == 200
