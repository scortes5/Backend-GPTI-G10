"""IA simulada: reglas fijas sobre los datos de la consulta, sin red, costo ni API key.

No es un modelo ni reemplaza a un agrónomo. La misma entrada siempre da la misma respuesta, y esta
siempre se presenta como simulada.
"""
import unicodedata
from dataclasses import dataclass

from app.services.ia.contexto import Contexto, ContextoCampo, ContextoLote, LoteEnBodega

MAX_VINETAS = 6


@dataclass(frozen=True)
class GuiaCultivo:
    palabras: tuple[str, ...]
    dias_referencia: int
    conservacion: str


GUIAS = (
    GuiaCultivo(("arandano", "frutilla", "frambuesa", "mora", "cereza"), 7,
                "mantén la cosecha refrigerada y sin golpes, porque se deteriora rápido"),
    GuiaCultivo(("lechuga", "acelga", "espinaca", "cilantro", "perejil"), 5,
                "mantén la cosecha fresca y a la sombra, y véndela primero"),
    GuiaCultivo(("tomate", "pepino", "pimiento", "zapallo italiano"), 10,
                "guarda la cosecha en un lugar fresco, ventilado y sin apilar demasiado"),
    GuiaCultivo(("papa",), 90, "guarda la cosecha a oscuras y ventilada, porque la luz la enverdece"),
    GuiaCultivo(("cebolla", "ajo", "zapallo"), 90, "guarda la cosecha seca y bien ventilada"),
    GuiaCultivo(("trigo", "avena", "cebada", "quinoa", "maiz", "poroto", "lenteja", "arveja seca"), 180,
                "guarda la cosecha seca, sobre tarimas y protegida de roedores"),
    GuiaCultivo(("manzana", "pera", "kiwi"), 45, "guarda la cosecha en frío y separada de productos sensibles a olores"),
)
GUIA_GENERAL = GuiaCultivo((), 30, "guarda la cosecha limpia, fresca y ventilada")


def _sin_tildes(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def _guia(cultivo: str) -> GuiaCultivo:
    nombre = _sin_tildes(cultivo)
    return next((g for g in GUIAS if any(p in nombre for p in g.palabras)), GUIA_GENERAL)


def _n(valor: float) -> str:
    return f"{valor:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def _agrupar_por_cultivo(lotes: tuple[LoteEnBodega, ...]) -> list[LoteEnBodega]:
    """Una viñeta por cultivo: suma los kilos y considera el lote más antiguo."""
    grupos: dict[str, LoteEnBodega] = {}
    for l in lotes:
        clave = _sin_tildes(l.cultivo).strip()
        g = grupos.get(clave)
        grupos[clave] = LoteEnBodega(g.cultivo, g.kilos + l.kilos, max(g.dias, l.dias)) if g else l
    return list(grupos.values())


def _vineta_bodega(lote: LoteEnBodega, heladas: bool, humedo: bool) -> str:
    guia = _guia(lote.cultivo)
    texto = f"- **{lote.cultivo} en bodega ({_n(lote.kilos)} kg, hasta {lote.dias} días):** {guia.conservacion}."
    if lote.dias >= guia.dias_referencia:
        texto += " Lo más antiguo ya pasó su tiempo habitual de guarda: revísalo hoy y prioriza su venta."
    if heladas:
        texto += " Protege la cosecha del frío esta noche."
    elif humedo:
        texto += " Ventila y revisa que no haya condensación."
    return texto


def _recomendar_campo(c: ContextoCampo) -> str:
    vinetas: list[tuple[int, str]] = []  # (prioridad, texto): primero lo más urgente
    tmin, tmax, suelo = c.temperatura_min, c.temperatura_max, c.humedad_suelo
    saturado = suelo is not None and suelo >= 90
    seco = suelo is not None and suelo <= 30
    heladas = tmin is not None and tmin <= 3
    humedo = c.humedad_media is not None and c.humedad_media >= 85

    if tmin is not None and tmin <= 0:
        vinetas.append((0, f"- **Helada ({_n(tmin)} °C):** revisa brotes y flores, y prepara cubiertas o riego antiheladas para la próxima noche."))
    elif heladas:
        vinetas.append((1, f"- **Riesgo de helada ({_n(tmin)} °C):** si la noche viene despejada, ten listas las cubiertas."))

    if c.lluvia_24h >= 20 and saturado:
        vinetas.append((0, f"- **Suelo saturado tras {_n(c.lluvia_24h)} mm de lluvia ({_n(suelo)} %):** no riegues, no entres con maquinaria y despeja los drenajes."))
    elif c.lluvia_24h >= 20:
        vinetas.append((1, f"- **Lluvia intensa ({_n(c.lluvia_24h)} mm):** revisa drenajes y evita entrar con maquinaria hasta que el suelo drene."))
    elif saturado:
        vinetas.append((1, f"- **Suelo saturado ({_n(suelo)} %) sin lluvia fuerte:** suspende el riego y revisa fugas o drenajes."))
    elif seco and c.lluvia_24h < 5:
        momento = "temprano o al atardecer" if tmax is not None and tmax >= 28 else "hoy"
        vinetas.append((0, f"- **Suelo seco ({_n(suelo)} %):** prioriza el riego {momento}, partiendo por los cultivos más sensibles."))
    elif seco:
        vinetas.append((1, f"- **La lluvia no alcanzó ({_n(suelo)} % de humedad en el suelo):** revisa si necesitas un riego complementario."))
    elif c.lluvia_24h >= 5:
        vinetas.append((3, f"- **Lluvia ({_n(c.lluvia_24h)} mm):** ajusta o suspende el próximo riego."))
    elif suelo is None and tmax is not None and tmax >= 25:
        vinetas.append((3, "- **Riego:** no hay lectura del sensor de suelo; compruébalo a mano antes de regar."))

    if tmax is not None and tmax >= 32:
        vinetas.append((1, f"- **Calor intenso ({_n(tmax)} °C):** evita cosechar al mediodía y deja lo cosechado a la sombra."))
    if c.viento_max is not None and c.viento_max >= 40:
        vinetas.append((1, f"- **Viento fuerte ({_n(c.viento_max)} km/h):** no apliques productos y revisa amarras y mallas."))
    temperaturas = [t for t in (tmin, tmax) if t is not None]
    if humedo and temperaturas and 10 <= sum(temperaturas) / len(temperaturas) <= 25:
        vinetas.append((2, f"- **Riesgo de hongos (humedad {_n(c.humedad_media)} %):** vigila botritis y oídio, y mejora la ventilación."))

    if not vinetas:
        detalle = f" La humedad del suelo está en {_n(suelo)} %." if suelo is not None else ""
        vinetas.append((3, f"- **Condiciones estables:** buen momento para labores de campo y aplicaciones planificadas.{detalle}"))

    ordenadas = sorted(_agrupar_por_cultivo(c.lotes), key=lambda l: l.dias / _guia(l.cultivo).dias_referencia, reverse=True)
    vinetas.extend((4, _vineta_bodega(l, heladas, humedo)) for l in ordenadas)
    if not c.lotes:
        vinetas.append((5, "- **Bodega:** no registras cosecha disponible."))

    seleccion = [texto for _, texto in sorted(vinetas, key=lambda v: v[0])[:MAX_VINETAS]]
    return "\n".join(["Recomendación de ejemplo (IA simulada) según los datos de tu campo:", *seleccion])


def _recomendar_lote(c: ContextoLote) -> str:
    guia = _guia(c.cultivo)
    if c.kilos_disponibles <= 0:
        return "\n".join([
            "Recomendación de ejemplo (IA simulada) para este lote:",
            "- **Lote vendido por completo:** no requiere conservación. Revisa sus ventas para planificar la próxima temporada.",
        ])
    vinetas = [f"- **Conservación:** {guia.conservacion}."]
    if c.dias >= guia.dias_referencia:
        vinetas.insert(0, f"- **Venta prioritaria:** lleva {c.dias} días desde la cosecha y ya pasó su tiempo habitual de guarda. Revísalo hoy.")
    elif c.dias >= guia.dias_referencia * 0.7:
        vinetas.append(f"- **Planifica la venta:** lleva {c.dias} días y se acerca a su tiempo habitual de guarda.")
    else:
        vinetas.append(f"- **Tiempo de guarda:** lleva {c.dias} días; aún está dentro de lo habitual, pero revísalo periódicamente.")
    vendido = 100 * (c.kilos - c.kilos_disponibles) / c.kilos if c.kilos else 0
    vinetas.append(f"- **Comercialización:** quedan {_n(c.kilos_disponibles)} kg y llevas vendido el {vendido:.0f} % del lote.")
    return "\n".join(["Recomendación de ejemplo (IA simulada) para este lote:", *vinetas])


class ProveedorSimulado:
    def generar(self, instrucciones: str, consulta: str, contexto: Contexto | None = None) -> str:
        if isinstance(contexto, ContextoCampo):
            return _recomendar_campo(contexto)
        if isinstance(contexto, ContextoLote):
            return _recomendar_lote(contexto)
        return "Recomendación de ejemplo (IA simulada): revisa las condiciones de almacenamiento y prioriza lo más antiguo."
