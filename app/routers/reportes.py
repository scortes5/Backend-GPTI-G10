from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import usuario_actual
from app.db import get_db
from app.models import Usuario
from app.schemas import ReporteEnviadoOut, SolicitudReporte
from app.services import reportes as reportes_service
from app.services.correo import ServicioCorreo, crear_servicio_correo

router = APIRouter(prefix="/lotes/{codigo}/reporte", tags=["reportes"])


@router.post("", response_model=ReporteEnviadoOut, status_code=202)
def enviar_reporte(
    codigo: str,
    solicitud: SolicitudReporte,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
    servicio: ServicioCorreo = Depends(crear_servicio_correo),
):
    reportes_service.enviar_reporte_lote(db, codigo, solicitud.destinatario, usuario, servicio)
    return ReporteEnviadoOut(enviado_a=solicitud.destinatario)
