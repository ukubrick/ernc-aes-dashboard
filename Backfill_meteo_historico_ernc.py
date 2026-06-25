"""
Backfill histórico de meteo (Open-Meteo reanálisis) para entrenar los modelos ML.

El backfill de la Sesión 24 solo pobló radiación SOLAR; la meteo histórica eólica
(viento) solo existía desde la ventana móvil (~8 días), insuficiente para el forecast
probabilístico. Este script usa el endpoint de reanálisis (historical-forecast-api),
que sirve historia con las MISMAS variables y cálculos (v100m, densidad, cizalle) que
la adquisición normal, y la escribe en meteo_ernc con fuente='open-meteo', es_forecast=False.

    python Backfill_meteo_historico_ernc.py [YYYY-MM-DD inicio]   # default 2026-03-01

Por defecto backfillea los parques EÓLICOS (los solares ya tienen historia). Idempotente.
"""
import sys
from datetime import datetime, date

from dotenv import load_dotenv
load_dotenv()

from config import COORDENADAS, TECNOLOGIA, PARQUES_EOLICA, OPENMETEO_VARS_SOLAR, OPENMETEO_VARS_EOLICA
from utils.openmeteo_api import (
    _client, _params_solar, _params_eolica, _response_to_registros,
    OPENMETEO_HISTORICAL_URL,
)
from utils.db import upsert_meteo

INICIO_DEFECTO = "2026-03-01"


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def _dedup(registros: list[dict]) -> list[dict]:
    # (parque, fecha_hora, fuente) — Open-Meteo trae duplicados por DST; el upsert
    # falla con ON CONFLICT si vienen repetidos en el mismo lote.
    visto, out = set(), []
    for r in registros:
        k = (r["parque"], r["fecha_hora"], r["fuente"])
        if k not in visto:
            visto.add(k)
            out.append(r)
    return out


def backfill_parque(parque: str, inicio: str, fin: str) -> int:
    coord = COORDENADAS[parque]
    if TECNOLOGIA[parque] == "Solar":
        params = _params_solar(coord["lat"], coord["lon"], inicio, fin)
        variables = OPENMETEO_VARS_SOLAR
    else:
        params = _params_eolica(coord["lat"], coord["lon"], inicio, fin)
        variables = OPENMETEO_VARS_EOLICA
    try:
        responses = _client.weather_api(OPENMETEO_HISTORICAL_URL, params=params)
        registros = _dedup(_response_to_registros(responses[0], parque, variables))
        if registros:
            upsert_meteo(registros)
        log(f"  {parque}: {len(registros)} registros")
        return len(registros)
    except Exception as e:
        log(f"  {parque} ERROR: {e}")
        return 0


def main() -> None:
    inicio = sys.argv[1] if len(sys.argv) > 1 else INICIO_DEFECTO
    fin = date.today().isoformat()
    parques = sys.argv[2:] if len(sys.argv) > 2 else PARQUES_EOLICA
    log(f"Backfill meteo {inicio} → {fin} | parques: {parques}")
    total = 0
    for p in parques:
        total += backfill_parque(p, inicio, fin)
    log(f"=== LISTO. {total} registros meteo ===")


if __name__ == "__main__":
    main()
