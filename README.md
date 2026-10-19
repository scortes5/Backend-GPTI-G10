# Backend AgroTracker · GPTI G10

API (FastAPI) del sistema de trazabilidad y gestión de cosecha para la Cooperativa Newen al Sur.

- **Fase 1:** registro de lotes/cosechas, código QR por lote, historial.
- **Fase 2:** integración Instacrops, alertas climáticas, recomendaciones IA.

## Estructura

```
app/
  main.py            # app FastAPI, CORS, routers
  config.py          # variables de entorno (.env)
  db.py              # SQLAlchemy (SQLite local / Postgres en AWS)
  models.py          # tablas
  schemas.py         # modelos de entrada/salida (Pydantic)
  exceptions.py      # errores de dominio (se mapean a HTTP en main.py)
  routers/           # endpoints por módulo (solo HTTP)
  services/          # casos de uso y clientes externos
    ia/              # patrón Adapter: puerto ProveedorIA + adapters Claude/simulado
tests/
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/lotes` | Listar / registrar lotes |
| GET/PATCH/DELETE | `/lotes/{codigo}` | Ver, editar o eliminar un lote |
| GET | `/lotes/{codigo}/qr` | Código QR del lote |
| GET/POST | `/lotes/{codigo}/ventas` | Ventas del lote |
| GET | `/lotes/{codigo}/trazabilidad` | Lote + ventas + kilos e ingresos |
| GET | `/lotes/{codigo}/recomendacion` | Recomendación agronómica con IA |
| GET | `/dashboard/resumen` | Indicadores generales |

Las reglas de negocio que no se cumplen responden **409** (p. ej. vender más kilos de los disponibles).

## IA

`IA_PROVEEDOR=simulado` (por defecto) no usa red ni API key. Con `IA_PROVEEDOR=claude` y
`ANTHROPIC_API_KEY` se usa Claude. Para agregar otro proveedor basta un nuevo adapter con el
método `generar(instrucciones, consulta)` y registrarlo en `services/ia/__init__.py`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

## Correr

```bash
uvicorn app.main:app --reload
```

Docs interactivas en http://localhost:8000/docs

## Tests

```bash
pytest
```
