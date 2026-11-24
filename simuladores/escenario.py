"""Cambia el escenario de las APIs simuladas: python -m simuladores.escenario helada"""
import json
import os
import sys
import urllib.error
import urllib.request

from simuladores.datos import ESCENARIOS

URL = os.getenv("SIMULADORES_URL", "http://127.0.0.1:9000")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ESCENARIOS:
        print(f"Uso: python -m simuladores.escenario [{' | '.join(ESCENARIOS)}]")
        return 2
    pedido = urllib.request.Request(f"{URL}/escenario/{sys.argv[1]}", method="PUT")
    try:
        with urllib.request.urlopen(pedido, timeout=5) as respuesta:
            print("Escenario activo:", json.load(respuesta)["escenario"])
    except urllib.error.URLError as e:
        print(f"No se pudo contactar a los simuladores en {URL}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
