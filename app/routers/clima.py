from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import solo_admin, usuario_actual
from app.db import get_db
from app.models import Usuario
from app.schemas import CampoIn, CampoOut, ClimaOut, RecomendacionOut
from app.services import campos as campos_service
from app.services import recomendaciones as recomendaciones_service
from app.services.clima import ProveedorClima, crear_proveedor_clima
from app.services.clima.analisis import clima_del_campo
from app.services.ia import ProveedorIA, crear_proveedor

router = APIRouter(tags=["clima"])


@router.get("/campo", response_model=CampoOut)
def mi_campo(usuario_id: int | None = None, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return campos_service.a_salida(campos_service.obtener(db, usuario, usuario_id))


@router.put("/campo", response_model=CampoOut)
def guardar_campo(datos: CampoIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return campos_service.a_salida(campos_service.guardar(db, usuario, datos))


@router.get("/campos", response_model=list[CampoOut])
def listar_campos(db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    return [campos_service.a_salida(c) for c in campos_service.listar(db)]


@router.get("/clima", response_model=ClimaOut)
def clima(
    usuario_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
    proveedor: ProveedorClima = Depends(crear_proveedor_clima),
):
    """Clima del campo propio (o de otro usuario, solo administrador) según la estación Agromet más cercana."""
    return clima_del_campo(db, usuario, proveedor, usuario_id)


@router.get("/clima/recomendacion", response_model=RecomendacionOut)
def recomendacion_clima(
    usuario_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
    proveedor_clima: ProveedorClima = Depends(crear_proveedor_clima),
    proveedor_ia: ProveedorIA = Depends(crear_proveedor),
):
    datos = clima_del_campo(db, usuario, proveedor_clima, usuario_id)
    return RecomendacionOut(texto=recomendaciones_service.recomendar_clima(db, usuario, datos, proveedor_ia))
