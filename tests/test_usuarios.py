import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.exceptions import CredencialesInvalidas, ReglaDeNegocioInvalida
from app.models import Rol
from app.services import claves
from app.services import usuarios as usuarios_service


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion


def test_la_clave_se_guarda_hasheada():
    clave_hash = claves.hashear("secreta123")

    assert "secreta123" not in clave_hash
    assert claves.verificar("secreta123", clave_hash)
    assert not claves.verificar("otra", clave_hash)


def test_autenticar_con_credenciales_validas(db):
    usuarios_service.crear(db, "Ana", "Ana@Coop.cl", "secreta123", Rol.PRODUCTOR)
    assert usuarios_service.autenticar(db, "ana@coop.cl", "secreta123").nombre == "Ana"


def test_autenticar_con_clave_incorrecta(db):
    usuarios_service.crear(db, "Ana", "ana@coop.cl", "secreta123", Rol.PRODUCTOR)
    with pytest.raises(CredencialesInvalidas):
        usuarios_service.autenticar(db, "ana@coop.cl", "mala")


def test_usuario_inactivo_no_puede_entrar(db):
    usuario = usuarios_service.crear(db, "Ana", "ana@coop.cl", "secreta123", Rol.PRODUCTOR)
    usuario.activo = False
    db.commit()
    with pytest.raises(CredencialesInvalidas):
        usuarios_service.autenticar(db, "ana@coop.cl", "secreta123")


def test_correo_duplicado(db):
    usuarios_service.crear(db, "Ana", "ana@coop.cl", "secreta123", Rol.PRODUCTOR)
    with pytest.raises(ReglaDeNegocioInvalida):
        usuarios_service.crear(db, "Otra", "ANA@coop.cl", "secreta123", Rol.PRODUCTOR)


def test_crea_admin_inicial_solo_si_no_hay_usuarios(db, monkeypatch):
    monkeypatch.setattr(usuarios_service.settings, "admin_email", "admin@coop.cl")
    monkeypatch.setattr(usuarios_service.settings, "admin_clave", "admin12345")

    usuarios_service.asegurar_admin_inicial(db)
    usuarios_service.asegurar_admin_inicial(db)

    admin = usuarios_service.obtener_por_email(db, "admin@coop.cl")
    assert admin.es_admin
