"""Adquisición NASA POWER — GHI/temp/viento satelital para validar el recurso solar.

NASA POWER publica con un rezago real de ~2-3 meses (~85 días observados) y se actualiza
a diario, así que NO necesita correr cada hora. Basta una corrida diaria con una ventana
amplia (~100 días) que alcance el frente de datos disponible: NASA recorta sola las
fechas sin dato y el upsert se auto-corrige. Se guarda en meteo_ernc con
fuente='nasa-power' para cruzarlo con el GHI de Open-Meteo en el dashboard/ML.
"""
import sys
from datetime import datetime

from utils.nasapower_api import fetch_nasa_solar_todos
from utils.db import upsert_meteo

# Ventana amplia para alcanzar el frente de datos NASA (rezago real ~85 días).
DIAS = 100


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main():
    log("=== ADQUISICIÓN NASA POWER (validación solar) ===")
    try:
        registros = fetch_nasa_solar_todos(DIAS)
    except Exception as e:
        log(f"[ERROR] NASA POWER: {e}")
        sys.exit(1)

    if not registros:
        log("Sin registros NASA POWER (rezago o sin datos en la ventana). FIN OK.")
        return

    upsert_meteo(registros)
    log(f"Upsert NASA POWER: {len(registros)} registros (fuente='nasa-power').")
    log("FIN OK")


if __name__ == "__main__":
    main()
