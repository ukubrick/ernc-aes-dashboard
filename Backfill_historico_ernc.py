"""
Backfill histórico de generación real + BESS desde la API CEN.

Uso puntual (NO va al cron): rellena la DB con historia previa a la ventana móvil
de adquisición para tener suficientes pares meteo→gen al entrenar los modelos ML.
La generación real solo llegaba a ~9 días; la meteo open-meteo cubre desde
2026-03-01, así que se backfillea gen-real + BESS hasta esa fecha para alinear.

Recorre la historia en tramos (chunks) para acotar el tamaño de cada scan del feed.
Idempotente: usa los mismos upserts que el cron (on_conflict), se puede re-correr.

    python Backfill_historico_ernc.py [YYYY-MM-DD inicio] [YYYY-MM-DD fin]

Por defecto: inicio=2026-03-01, fin=hoy.
"""
import sys
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
load_dotenv()

from utils.cen_api import fetch_gen_real_todos, fetch_gen_bess
from utils.db import upsert_generacion_real, upsert_generacion_bess

CHUNK_DIAS = 7
INICIO_DEFECTO = "2026-03-01"


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def _chunks(inicio: date, fin: date, paso: int):
    cur = inicio
    while cur <= fin:
        hasta = min(cur + timedelta(days=paso - 1), fin)
        # endDate +1 para capturar el último día completo (igual que _ventana_fechas)
        yield cur.isoformat(), (hasta + timedelta(days=1)).isoformat()
        cur = hasta + timedelta(days=1)


def main() -> None:
    inicio = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.fromisoformat(INICIO_DEFECTO)
    fin = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()
    log(f"Backfill {inicio} → {fin} (tramos de {CHUNK_DIAS} días)")

    total_gen = total_bess = 0
    for start, end in _chunks(inicio, fin, CHUNK_DIAS):
        log(f"--- Tramo {start} → {end} ---")
        try:
            regs = fetch_gen_real_todos(start, end)
            if regs:
                upsert_generacion_real(regs)
                total_gen += len(regs)
                log(f"  gen-real: {len(regs)} registros")
            else:
                log("  gen-real: vacío")
        except Exception as e:
            log(f"  gen-real ERROR: {e}")

        try:
            regs_b = fetch_gen_bess(start, end)
            if regs_b:
                upsert_generacion_bess(regs_b)
                total_bess += len(regs_b)
                log(f"  BESS: {len(regs_b)} registros")
            else:
                log("  BESS: vacío")
        except Exception as e:
            log(f"  BESS ERROR: {e}")

    log(f"=== LISTO. gen-real={total_gen}  BESS={total_bess} ===")


if __name__ == "__main__":
    main()
