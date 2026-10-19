class ProveedorSimulado:
    """Proveedor sin costo ni red para desarrollo local y demos sin API key."""

    def generar(self, instrucciones: str, consulta: str) -> str:
        return (
            "Recomendación de ejemplo (IA simulada): revise humedad y temperatura "
            "de almacenamiento y priorice la venta de los kilos disponibles."
        )
