import re


class ProveedorSimulado:
    """Proveedor sin costo ni red para desarrollo local y demos sin API key.

    No usa un modelo: arma una respuesta fija a partir de las alertas que vienen en la consulta.
    """

    def generar(self, instrucciones: str, consulta: str) -> str:
        if "Alertas:" in consulta or "Sin alertas climáticas" in consulta:
            tramo = consulta.split("Alertas:", 1)[1] if "Alertas:" in consulta else ""
            tramo = re.split(r" En bodega:| No tiene cosecha", tramo)[0]
            titulos = re.findall(r"(?:^ |; )([^(;]+?) \(", tramo)
            vinetas = [f"- **{t.strip()}:** revisa el detalle de la alerta y prioriza esa tarea hoy." for t in titulos]
            vinetas = vinetas or ["- **Clima estable:** buen momento para cosechar, aplicar productos y ordenar la bodega."]
            return "\n".join([
                "Recomendación de ejemplo (IA simulada) según el clima de tu campo:",
                *vinetas,
                "- **Lotes en bodega:** mantén ventilación y revisa humedad y temperatura de almacenamiento.",
            ])
        return (
            "Recomendación de ejemplo (IA simulada): revise humedad y temperatura "
            "de almacenamiento y priorice la venta de los kilos disponibles."
        )
