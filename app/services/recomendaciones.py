"""Recomendaciones agronómicas, independientes del proveedor de IA.

Cada recomendación queda en un historial con los datos que se le entregaron a la IA, para que
el usuario vea en qué se basa (RN-07, RN-08). Hay un límite diario de consultas por usuario
(IA_LIMITE_DIARIO) y un interruptor para desactivarlas (IA_HABILITADA).
"""
import json
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import DemasiadosIntentos, ServicioExternoNoDisponible
from app.models import Estado, Lote, Recomendacion, Usuario
from app.schemas import RecomendacionOut
from app.services import lotes as lotes_service
from app.services.ia import ProveedorIA, nombre_proveedor
from app.services.ia.contexto import ContextoCampo, ContextoLote, LoteEnBodega

INSTRUCCIONES = (
    "Eres un asesor agronómico para pequeños productores de una cooperativa chilena. "
    "Responde en español simple, en máximo 5 viñetas cortas y accionables."
)


def recomendar(db: Session, codigo_lote: str, usuario: Usuario, proveedor: ProveedorIA) -> RecomendacionOut:
    lote = lotes_service.obtener(db, codigo_lote, usuario)
    _verificar_disponible(db, usuario)
    dias = _dias_desde(lote.fecha_cosecha)
    contexto = ContextoLote(lote.cultivo, lote.kilos, lote.kilos_disponibles, dias)
    texto = proveedor.generar(INSTRUCCIONES, describir_lote(lote), contexto)
    datos = [
        ("Cultivo", lote.cultivo),
        ("Kilos cosechados", f"{lote.kilos:g} kg"),
        ("Kilos disponibles", f"{lote.kilos_disponibles:g} kg"),
        ("Días desde la cosecha", str(dias)),
        ("Entregas vigentes", str(len(lote.entregas_vigentes))),
    ]
    return _guardar(db, usuario, "lote", texto, datos, proveedor, lote)


def historial(db: Session, usuario: Usuario, codigo_lote: str | None = None, limite: int = 20) -> list[RecomendacionOut]:
    consulta = select(Recomendacion)
    if codigo_lote:
        consulta = consulta.where(Recomendacion.lote_id == lotes_service.obtener(db, codigo_lote, usuario).id)
    elif not usuario.es_admin:
        consulta = consulta.where(Recomendacion.usuario_id == usuario.id)
    filas = db.scalars(consulta.order_by(Recomendacion.creado.desc(), Recomendacion.id.desc()).limit(limite))
    return [a_salida(r) for r in filas]


def a_salida(r: Recomendacion, restantes: int | None = None) -> RecomendacionOut:
    return RecomendacionOut(
        id=r.id,
        tipo=r.tipo,
        lote_codigo=r.lote.codigo if r.lote else None,
        proveedor=r.proveedor,
        texto=r.texto,
        datos_usados=[{"dato": d, "valor": v} for d, v in json.loads(r.datos_usados)],
        creado=r.creado,
        consultas_restantes=restantes,
    )


def consultas_de_hoy(db: Session, usuario: Usuario) -> int:
    inicio = datetime.combine(date.today(), datetime.min.time())
    return db.scalar(
        select(func.count(Recomendacion.id)).where(
            Recomendacion.usuario_id == usuario.id,
            Recomendacion.creado >= inicio,
            Recomendacion.creado < inicio + timedelta(days=1),
        )
    )


def _verificar_disponible(db: Session, usuario: Usuario) -> None:
    if not settings.ia_habilitada:
        raise ServicioExternoNoDisponible("Las recomendaciones con IA están desactivadas por la cooperativa")
    limite = settings.ia_limite_diario
    if limite and consultas_de_hoy(db, usuario) >= limite:
        raise DemasiadosIntentos(f"Llegaste al límite de {limite} recomendaciones por día. Vuelve a intentarlo mañana.")


def _guardar(db: Session, usuario: Usuario, tipo: str, texto: str, datos: list[tuple[str, str]],
             proveedor: ProveedorIA, lote: Lote | None = None) -> RecomendacionOut:
    registro = Recomendacion(
        tipo=tipo,
        lote=lote,
        usuario_id=usuario.id,
        proveedor=nombre_proveedor(proveedor),
        texto=texto,
        datos_usados=json.dumps(datos, ensure_ascii=False),
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    limite = settings.ia_limite_diario
    return a_salida(registro, max(0, limite - consultas_de_hoy(db, usuario)) if limite else None)


def _dias_desde(fecha: date) -> int:
    return max(0, (date.today() - fecha).days)


def describir_lote(lote: Lote) -> str:
    return (
        f"Lote {lote.codigo} de {lote.cultivo}, productor {lote.productor}. "
        f"Cosechado el {lote.fecha_cosecha:%d-%m-%Y} con {lote.kilos:g} kg; "
        f"vendidos {lote.kilos_vendidos:g} kg, disponibles {lote.kilos_disponibles:g} kg. "
        "¿Qué recomiendas para conservar y comercializar lo disponible?"
    )


INSTRUCCIONES_CLIMA = (
    "Eres un asesor agronómico para pequeños productores de una cooperativa chilena del sur. "
    "Con el clima reciente del campo (estación de la Red Agroclimática Nacional), los sensores de suelo "
    "si están disponibles y lo que el productor tiene en bodega, indica qué debe tomar en consideración hoy y los próximos días: labores, riego, "
    "heladas, plagas y enfermedades, cosecha y conservación. Responde en español simple, en máximo 6 "
    "viñetas cortas y accionables, empezando por lo más urgente. No inventes datos que no se entregan."
)


def recomendar_clima(db: Session, usuario: Usuario, clima, proveedor: ProveedorIA) -> RecomendacionOut:
    from app.services.clima.analisis import describir

    _verificar_disponible(db, usuario)
    duenio = db.get(Usuario, clima.campo.usuario_id)
    lotes = [l for l in lotes_service.listar(db, duenio, estado=Estado.VIGENTE) if l.kilos_disponibles > 0]
    consulta = describir(clima)
    if not clima.alertas:
        consulta += " Sin alertas climáticas."
    if lotes:
        consulta += " En bodega: " + "; ".join(
            f"{l.cultivo} {l.kilos_disponibles:g} kg (cosechado el {l.fecha_cosecha:%d-%m-%Y})" for l in lotes[:10]
        ) + "."
    else:
        consulta += " No tiene cosecha en bodega."
    r, s = clima.resumen_24h, clima.sensores
    lectura = s.actual if s and s.reciente else None
    contexto = ContextoCampo(
        temperatura_min=r.temperatura_min,
        temperatura_max=r.temperatura_max,
        lluvia_24h=r.precipitacion,
        humedad_media=r.humedad_media,
        viento_max=r.viento_max,
        humedad_suelo=lectura.humedad_suelo if lectura else None,
        temperatura_suelo=lectura.temperatura_suelo if lectura else None,
        lotes=tuple(LoteEnBodega(l.cultivo, l.kilos_disponibles, _dias_desde(l.fecha_cosecha)) for l in lotes[:10]),
    )
    texto = proveedor.generar(INSTRUCCIONES_CLIMA, consulta + " ¿Qué debo tomar en consideración?", contexto)
    datos = [
        ("Estación", f"{clima.estacion.nombre} ({clima.estacion.distancia_km:g} km)"),
        ("Fuente del clima", clima.fuente),
        ("Temperatura 24 h", f"{_o(r.temperatura_min)} a {_o(r.temperatura_max)} °C"),
        ("Lluvia 24 h", f"{r.precipitacion:g} mm"),
        ("Humedad media", f"{_o(r.humedad_media)} %"),
        ("Viento máximo", f"{_o(r.viento_max)} km/h"),
        ("Humedad del suelo", f"{lectura.humedad_suelo:g} %" if lectura and lectura.humedad_suelo is not None else "sin sensor"),
        ("Alertas", ", ".join(a.titulo for a in clima.alertas) or "ninguna"),
        ("Lotes en bodega", str(len(lotes))),
    ]
    return _guardar(db, usuario, "clima", texto, datos, proveedor)


def _o(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:g}"
