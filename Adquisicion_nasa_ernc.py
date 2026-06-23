"""Adquisición NASA POWER — GHI/temp/viento satelital para validar el recurso solar.

NASA POWER publica con rezago (~3-7 días) y se actualiza a diario, así que NO necesita
correr cada hora. Basta una corrida diaria que rellene los últimos ~10 días (la ventana
cubre el rezago y se auto-corrige con el upsert). Se guarda en meteo_ernc con
fuente='nasa-power' para cruzarlo con el GHI de Open-Meteo en el dashboard/ML.
"""
import sys
from datetime import datetime

from utils.nasapower_api import fetch_nasa_solar_todos
from utils.db import upsert_meteo

DIAS = 10


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
