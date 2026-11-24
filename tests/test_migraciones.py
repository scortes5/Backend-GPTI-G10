"""Una base creada con la primera versión se actualiza sola al iniciar."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.migraciones import migrar
from app.models import Lote


def test_lote_antiguo_queda_con_su_entrega_y_vigente(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'vieja.db'}")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nombre VARCHAR(120), email VARCHAR(254), "
                       "clave_hash VARCHAR(255), rol VARCHAR(20), activo BOOLEAN, creado DATETIME, sesiones_desde DATETIME)"))
        c.execute(text("CREATE TABLE lotes (id INTEGER PRIMARY KEY, codigo VARCHAR(12), productor VARCHAR(120), cultivo VARCHAR(80), "
                       "kilos FLOAT, fecha_cosecha DATE, creado DATETIME, usuario_id INTEGER)"))
        c.execute(text("CREATE TABLE ventas (id INTEGER PRIMARY KEY, lote_id INTEGER, comprador VARCHAR(120), kilos FLOAT, "
                       "precio_por_kilo FLOAT, fecha DATE, creado DATETIME)"))
        c.execute(text("INSERT INTO lotes VALUES (1, 'abc', 'Juan', 'Papa', 80, '2026-09-01', '2026-09-01', NULL)"))
        c.execute(text("INSERT INTO ventas VALUES (1, 1, 'Feria', 30, 900, '2026-09-05', '2026-09-05')"))

    migrar(engine)
    migrar(engine)  # idempotente

    with Session(engine) as db:
        lote = db.get(Lote, 1)
        assert lote.estado.value == "vigente"
        assert [e.kilos for e in lote.entregas] == [80]
        assert lote.kilos_disponibles == 50
