from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.exceptions import (
    AccesoDenegado,
    CredencialesInvalidas,
    RecursoNoEncontrado,
    ReglaDeNegocioInvalida,
    ServicioExternoNoDisponible,
)
from app.routers import auth, dashboard, instacrops, lotes, publico, recomendaciones, reportes, usuarios, ventas
from app.services import usuarios as usuarios_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        usuarios_service.asegurar_admin_inicial(db)
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


@app.exception_handler(CredencialesInvalidas)
def credenciales_invalidas(_: Request, exc: CredencialesInvalidas):
    return JSONResponse(status_code=401, content={"detail": str(exc)}, headers={"WWW-Authenticate": "Bearer"})


@app.exception_handler(AccesoDenegado)
def acceso_denegado(_: Request, exc: AccesoDenegado):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


app.include_router(auth.router)
app.include_router(lotes.router)
app.include_router(ventas.router)
app.include_router(recomendaciones.router)
app.include_router(reportes.router)
app.include_router(dashboard.router)
app.include_router(instacrops.router)
app.include_router(publico.router)
app.include_router(usuarios.router)


@app.get("/health")
def health():
    return {"status": "ok"}
