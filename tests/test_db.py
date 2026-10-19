from app.db import normalizar_url


def test_normaliza_urls_de_postgres():
    assert normalizar_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalizar_url("postgresql://u:p@host/db") == "postgresql+psycopg://u:p@host/db"


def test_mantiene_sqlite():
    assert normalizar_url("sqlite:///./agrotracker.db") == "sqlite:///./agrotracker.db"
