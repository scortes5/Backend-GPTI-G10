import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Rol
from app.services import tokens
from app.services import usuarios as usuarios_service


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestSession() as db:
        yield db
    app.dependency_overrides.clear()


@pytest.fixture
def crear_cliente(db_session):
    """Crea un usuario con el rol indicado y un TestClient con su sesión iniciada."""

    def _crear(rol: Rol = Rol.ADMIN, nombre: str = "Directiva", email: str = "admin@coop.cl") -> TestClient:
        usuario = usuarios_service.crear(db_session, nombre, email, "clave-segura", rol)
        return TestClient(app, headers={"Authorization": f"Bearer {tokens.emitir(usuario.id)}"})

    return _crear


@pytest.fixture
def client(crear_cliente):
    """Cliente con sesión de administrador."""
    return crear_cliente()


@pytest.fixture
def productor(crear_cliente):
    return crear_cliente(Rol.PRODUCTOR, "Ana Huenchul", "ana@coop.cl")


@pytest.fixture
def anonimo(db_session):
    return TestClient(app)
