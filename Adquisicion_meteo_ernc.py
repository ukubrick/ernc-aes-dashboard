"""
Adquisición meteorológica ERNC para AES Andes — Open-Meteo.
Ejecutado por GitHub Actions cada hora (minuto :20, después de Adquisicion_ernc.py).
Descarga histórico (2 días) + forecast (7 días) para los 11 parques.
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

_required = ["SUPABASE_URL", "SUPABASE_KEY"]
_missing = [v for v in _required if not os.environ.get(v)]
if _missing:
    print(f"[ERROR] Variables de entorno faltantes: {', '.join(_missing)}")
    sys.exit(1)

from config import NOMBRE_DISPLAY, PARQUES_TODOS, TECNOLOGIA
from utils.openmeteo_api import obtener_meteo_parque
from utils.db import upsert_meteo


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main():
    log("=" * 60)
    log("INICIO ADQUISICIÓN METEOROLÓGICA ERNC AES ANDES")
    log("=" * 60)

    totales: dict[str, int] = {}
    errores: list[str] = []

    for parque in PARQUES_TODOS:
        nombre = NOMBRE_DISPLAY[parque]
        tecnologia = TECNOLOGIA[parque]
        log(f"--- [{parque}] {nombre} ({tecnologia}) ---")

        try:
            registros = obtener_meteo_parque(parque, dias_historico=2, dias_forecast=7, pausa_seg=1.5)
            if not registros:
                log(f"  Sin datos para {parque}.")
                totales[parque] = 0
                continue

            n = upsert_meteo(registros)
            log(f"  Upsert: {len(registros)} registros meteo guardados.")
            totales[parque] = len(registros)

        except Exception as e:
            log(f"  [ERROR] {parque}: {e}")
            errores.append(f"{parque}: {e}")
            totales[parque] = 0

    log("=" * 60)
    log("RESUMEN:")
    total_global = 0
    for parque, n in totales.items():
        nombre = NOMBRE_DISPLAY[parque]
        log(f"  {nombre}: {n} registros")
        total_global += n
    log(f"  TOTAL: {total_global} registros meteorológicos")

    if errores:
        log(f"ERRORES ({len(errores)}):")
        for e in errores:
            log(f"  - {e}")
        log("FIN CON ERRORES")
        sys.exit(1)
    else:
        log("FIN OK")


if __name__ == "__main__":
    main()
