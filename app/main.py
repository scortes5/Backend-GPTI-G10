from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import Base, engine
from app.exceptions import RecursoNoEncontrado, ReglaDeNegocioInvalida, ServicioExternoNoDisponible
from app.routers import dashboard, instacrops, lotes, recomendaciones, reportes, ventas


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="AgroTracker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RecursoNoEncontrado)
def recurso_no_encontrado(_: Request, exc: RecursoNoEncontrado):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ReglaDeNegocioInvalida)
def regla_de_negocio_invalida(_: Request, exc: ReglaDeNegocioInvalida):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ServicioExternoNoDisponible)
def servicio_externo_no_disponible(_: Request, exc: ServicioExternoNoDisponible):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


app.include_router(lotes.router)
app.include_router(ventas.router)
app.include_router(recomendaciones.router)
app.include_router(reportes.router)
app.include_router(dashboard.router)
app.include_router(instacrops.router)


@app.get("/health")
def health():
    return {"status": "ok"}
