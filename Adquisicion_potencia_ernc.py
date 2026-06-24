"""
Adquisición rápida de POTENCIA REAL — solo generación real de parques + BESS.
Ejecutado por GitHub Actions cada 30 min para tener la generación lo antes posible,
sin esperar a la corrida horaria completa (PCP/CMG/limitaciones/meteo son más lentos).

Reutiliza las funciones de Adquisicion_ernc.py para no duplicar lógica.
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

from Adquisicion_ernc import log, adquirir_gen_real, adquirir_gen_bess


def main():
    log("=== ADQUISICIÓN POTENCIA REAL (gen-real + BESS, cada 30 min) ===")
    total = 0
    try:
        total += adquirir_gen_real()
    except Exception as e:
        log(f"[ERROR] gen-real: {e}")
    try:
        total += adquirir_gen_bess()
    except Exception as e:
        log(f"[ERROR] BESS: {e}")
    log(f"FIN OK — {total} registros de potencia procesados.")


if __name__ == "__main__":
    main()
