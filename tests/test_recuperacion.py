import re
import time

import pytest

from app.main import app
from app.services.correo import Correo, crear_servicio_correo


class CorreoEspia:
    def __init__(self):
        self.enviados: list[Correo] = []

    def enviar(self, correo: Correo) -> None:
        self.enviados.append(correo)

    def ultimo_codigo(self) -> str:
        return re.search(r"\b(\d{6})\b", self.enviados[-1].cuerpo).group(1)


@pytest.fixture
def correo():
    espia = CorreoEspia()
    app.dependency_overrides[crear_servicio_correo] = lambda: espia
    yield espia
    app.dependency_overrides.pop(crear_servicio_correo, None)


def pedir_codigo(anonimo, email="ana@coop.cl"):
    return anonimo.post("/auth/recuperar", json={"email": email})


def restablecer(anonimo, codigo, clave="nueva-clave-segura", email="ana@coop.cl"):
    return anonimo.post("/auth/restablecer", json={"email": email, "codigo": codigo, "clave_nueva": clave})


def login(anonimo, clave):
    return anonimo.post("/auth/login", json={"email": "ana@coop.cl", "clave": clave})


def test_recuperar_con_codigo_cambia_la_clave(anonimo, productor, correo):
    assert pedir_codigo(anonimo).status_code == 202
    assert correo.enviados[0].destinatario == "ana@coop.cl"

    assert restablecer(anonimo, correo.ultimo_codigo()).status_code == 204

    assert login(anonimo, "nueva-clave-segura").status_code == 200
    assert login(anonimo, "clave-segura").status_code == 401


def test_correo_no_registrado_responde_igual_y_no_envia(anonimo, correo):
    respuesta = pedir_codigo(anonimo, "nadie@coop.cl")

    assert respuesta.status_code == 202
    assert correo.enviados == []


def test_el_codigo_sirve_una_sola_vez(anonimo, productor, correo):
    pedir_codigo(anonimo)
    codigo = correo.ultimo_codigo()

    restablecer(anonimo, codigo)

    assert restablecer(anonimo, codigo, "otra-clave-segura").status_code == 400


def test_codigo_incorrecto(anonimo, productor, correo):
    pedir_codigo(anonimo)
    incorrecto = "000000" if correo.ultimo_codigo() != "000000" else "111111"
    assert restablecer(anonimo, incorrecto).status_code == 400


def test_codigo_se_anula_tras_cinco_intentos(anonimo, productor, correo):
    pedir_codigo(anonimo)
    correcto = correo.ultimo_codigo()
    incorrecto = "000000" if correcto != "000000" else "111111"
    for _ in range(5):
        restablecer(anonimo, incorrecto)

    assert restablecer(anonimo, correcto).status_code == 400


def test_pedir_un_codigo_nuevo_anula_el_anterior(anonimo, productor, correo):
    pedir_codigo(anonimo)
    anterior = correo.ultimo_codigo()
    pedir_codigo(anonimo)

    if anterior != correo.ultimo_codigo():
        assert restablecer(anonimo, anterior).status_code == 400
    assert restablecer(anonimo, correo.ultimo_codigo()).status_code == 204


def test_codigo_vencido(anonimo, productor, correo, monkeypatch):
    from datetime import timedelta

    from app.services import recuperacion

    pedir_codigo(anonimo)
    ahora_real = recuperacion._ahora_utc
    monkeypatch.setattr(recuperacion, "_ahora_utc", lambda: ahora_real() + timedelta(minutes=16))

    assert restablecer(anonimo, correo.ultimo_codigo()).status_code == 400


def test_limita_solicitudes_por_correo(anonimo, productor, correo):
    for _ in range(5):
        pedir_codigo(anonimo)
    assert len(correo.enviados) == 3


def test_restablecer_desbloquea_el_login(anonimo, productor, correo):
    for _ in range(5):
        login(anonimo, "incorrecta")
    pedir_codigo(anonimo)
    restablecer(anonimo, correo.ultimo_codigo())

    assert login(anonimo, "nueva-clave-segura").status_code == 200


def test_formato_de_codigo_y_clave(anonimo):
    assert restablecer(anonimo, "12ab56").status_code == 422
    assert restablecer(anonimo, "123456", clave="corta").status_code == 422


def test_restablecer_cierra_las_sesiones_abiertas(anonimo, productor, correo):
    assert productor.get("/auth/yo").status_code == 200
    time.sleep(1.1)  # iat tiene resolución de segundos: evita que ambos momentos coincidan
    pedir_codigo(anonimo)
    restablecer(anonimo, correo.ultimo_codigo())

    assert productor.get("/auth/yo").status_code == 401
    nueva = login(anonimo, "nueva-clave-segura").json()["access_token"]
    assert anonimo.get("/auth/yo", headers={"Authorization": f"Bearer {nueva}"}).status_code == 200
