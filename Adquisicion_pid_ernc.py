"""
Adquisición de PROGRAMACIÓN PID — generación programada PID + demanda PID por zona.

El PID (Programa Intra-Día) es el reprograma que ajusta el PCP dentro del día con la
operación real. Ambos endpoints paginan TODO el sistema, así que esta adquisición vive
en un workflow propio (no satura la corrida horaria de Adquisicion_ernc.py).

Reutiliza las funciones de Adquisicion_ernc.py para no duplicar lógica.
Solo requiere CEN_USER_KEY (plan SIP) — NO usa CEN_OPS_KEY.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

_required = ["CEN_USER_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
_missing = [v for v in _required if not os.environ.get(v)]
if _missing:
    print(f"[ERROR] Variables de entorno faltantes: {', '.join(_missing)}")
    sys.exit(1)

from datetime import datetime, timezone

from Adquisicion_ernc import (
    log, adquirir_gen_programada_pid, adquirir_demanda_pid,
    adquirir_demanda_pronostico, adquirir_instrucciones, adquirir_sscc_programado,
)


def main():
    log("=== ADQUISICIÓN PROGRAMACIÓN PID (gen PID + demanda PID + instrucciones) ===")
    errores = []
    total = 0
    try:
        total += adquirir_gen_programada_pid()
    except Exception as e:
        log(f"[ERROR] gen PID: {e}")
        errores.append(f"gen_pid: {e}")
    try:
        total += adquirir_demanda_pid()
    except Exception as e:
        log(f"[ERROR] demanda PID: {e}")
        errores.append(f"demanda_pid: {e}")
    try:
        total += adquirir_instrucciones()
    except Exception as e:
        log(f"[ERROR] instrucciones: {e}")
        errores.append(f"instrucciones: {e}")
    try:
        total += adquirir_demanda_pronostico()
    except Exception as e:
        log(f"[ERROR] demanda pronóstico 7d: {e}")
        errores.append(f"demanda_7d: {e}")
    # SSCC programados: MUY voluminoso (~77 páginas/día) → solo 1 vez al día (13 UTC)
    if datetime.now(timezone.utc).hour == 13:
        try:
            total += adquirir_sscc_programado()
        except Exception as e:
            log(f"[ERROR] SSCC programados: {e}")
            errores.append(f"sscc_prog: {e}")

    log(f"RESUMEN PID: {total} registros procesados.")
    if errores:
        for e in errores:
            log(f"  - {e}")
        log("FIN CON ERRORES")
        sys.exit(1)
    log("FIN OK")


if __name__ == "__main__":
    main()
