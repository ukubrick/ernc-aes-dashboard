"""
Adquisición horaria de datos ERNC para AES Andes.
Ejecutado por GitHub Actions cada hora (minuto :10).
Fuentes: API CEN (gen-real, PCP, CMG, limitaciones, SSCC).
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Verificar variables de entorno requeridas antes de importar módulos que las usan
_required = ["CEN_USER_KEY", "CEN_OPS_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
_missing = [v for v in _required if not os.environ.get(v)]
if _missing:
    print(f"[ERROR] Variables de entorno faltantes: {', '.join(_missing)}")
    sys.exit(1)

from config import (
    NOMBRE_DISPLAY, ID_CENTRAL, CMG_NODO, CMG_NODOS_TODOS,
    DIAS_VENTANA, DIAS_VENTANA_LIM,
)
from utils.cen_api import (
    fetch_gen_real_todos,
    fetch_gen_bess,
    fetch_gen_programada,
    fetch_cmg,
    cmg_a_registros,
    fetch_cmg_online_8b,
    fetch_cmg_programado,
    fetch_limitaciones,
    fetch_sscc,
    _ventana_fechas,
)
from utils.db import (
    upsert_generacion_real,
    upsert_generacion_bess,
    upsert_generacion_programada,
    upsert_cmg,
    upsert_cmg_programado,
    upsert_limitaciones,
    upsert_sscc,
)


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def adquirir_gen_real() -> int:
    log("=== GENERACIÓN REAL ===")
    start, end = _ventana_fechas(DIAS_VENTANA)
    log(f"Ventana: {start} → {end}")
    registros = fetch_gen_real_todos(start, end)
    if not registros:
        log("Sin registros de gen. real.")
        return 0
    n = upsert_generacion_real(registros)
    log(f"Upsert gen. real: {len(registros)} registros procesados.")
    return len(registros)


def adquirir_gen_bess() -> int:
    log("=== GENERACIÓN BESS ===")
    # Ventana corta: requiere scan completo del feed (BESS sin idCentral).
    registros = fetch_gen_bess()
    if not registros:
        log("Sin registros de BESS.")
        return 0
    upsert_generacion_bess(registros)
    log(f"Upsert BESS: {len(registros)} registros procesados.")
    return len(registros)


def adquirir_gen_programada() -> int:
    log("=== GENERACIÓN PROGRAMADA PCP ===")
    start, end = _ventana_fechas(DIAS_VENTANA)
    log(f"Ventana: {start} → {end} (solo últimas {DIAS_VENTANA} horas para no tardar 12 min)")
    registros = fetch_gen_programada(start, end)
    if not registros:
        log("Sin registros PCP para nuestros parques.")
        return 0
    n = upsert_generacion_programada(registros)
    log(f"Upsert gen. programada: {len(registros)} registros procesados.")
    return len(registros)


def adquirir_cmg() -> int:
    log("=== CMG (COSTO MARGINAL) ===")
    try:
        cmg_data = fetch_cmg()
        # Nodos únicos con parques asignados
        nodos = CMG_NODOS_TODOS
        registros = cmg_a_registros(cmg_data, nodos)
        if not registros:
            log("Sin nodos CMG disponibles en el JSON S3.")
            return 0
        n = upsert_cmg(registros)
        for r in registros:
            log(f"  CMG {r['nodo']}: {r['cmg_usd_mwh']} USD/MWh @ {r['fecha_hora']}")
        return len(registros)
    except Exception as e:
        log(f"[WARN] Feed S3 falló ({e}). Probando respaldo API 8 barras...")
        try:
            registros = fetch_cmg_online_8b()
            if not registros:
                log("Respaldo 8b sin datos.")
                return 0
            upsert_cmg(registros)
            log(f"Upsert CMG (respaldo 8b): {len(registros)} registros.")
            return len(registros)
        except Exception as e2:
            log(f"[WARN] Respaldo 8b también falló: {e2}")
            return 0


def adquirir_cmg_programado() -> int:
    log("=== CMG PROGRAMADO PCP (CMG futuro) ===")
    start, end = _ventana_fechas(DIAS_VENTANA)
    log(f"Ventana: {start} → {end}")
    registros = fetch_cmg_programado(start, end)
    if not registros:
        log("Sin registros de CMG programado para los nodos del proyecto.")
        return 0
    upsert_cmg_programado(registros)
    log(f"Upsert CMG programado: {len(registros)} registros procesados.")
    return len(registros)


def adquirir_limitaciones() -> int:
    log("=== LIMITACIONES DE TRANSMISIÓN ===")
    start, end = _ventana_fechas(DIAS_VENTANA_LIM)
    log(f"Ventana: {start} → {end} ({DIAS_VENTANA_LIM} días)")
    registros = fetch_limitaciones(start, end)
    if not registros:
        log("Sin limitaciones para nuestros parques.")
        return 0
    n = upsert_limitaciones(registros)
    log(f"Upsert limitaciones: {len(registros)} registros procesados.")
    for r in registros:
        log(f"  {NOMBRE_DISPLAY.get(r['parque'], r['parque'])}: {r['instalacion_nombre']} | status={r['status']} | {r['potencia']} MW")
    return len(registros)


def adquirir_sscc() -> int:
    log("=== SSCC (SERVICIOS COMPLEMENTARIOS) ===")
    start, end = _ventana_fechas(DIAS_VENTANA)
    log(f"Ventana: {start} → {end}")
    registros = fetch_sscc(start, end)
    if not registros:
        log("Sin instrucciones SSCC para nuestros parques.")
        return 0
    n = upsert_sscc(registros)
    log(f"Upsert SSCC: {len(registros)} registros procesados.")
    for r in registros:
        log(f"  {NOMBRE_DISPLAY.get(r['parque'], r['parque'])}: {r['instruccion_sscc']} @ {r['inicio_periodo']}")
    return len(registros)


def main():
    log("=" * 60)
    log("INICIO ADQUISICIÓN ERNC AES ANDES")
    log("=" * 60)

    errores = []
    totales = {}

    try:
        totales["gen_real"] = adquirir_gen_real()
    except Exception as e:
        log(f"[ERROR] Gen. real: {e}")
        errores.append(f"gen_real: {e}")

    try:
        totales["bess"] = adquirir_gen_bess()
    except Exception as e:
        log(f"[ERROR] BESS: {e}")
        errores.append(f"bess: {e}")

    try:
        totales["gen_prog"] = adquirir_gen_programada()
    except Exception as e:
        log(f"[ERROR] Gen. programada: {e}")
        errores.append(f"gen_prog: {e}")

    try:
        totales["cmg"] = adquirir_cmg()
    except Exception as e:
        log(f"[ERROR] CMG: {e}")
        errores.append(f"cmg: {e}")

    try:
        totales["cmg_prog"] = adquirir_cmg_programado()
    except Exception as e:
        log(f"[ERROR] CMG programado: {e}")
        errores.append(f"cmg_prog: {e}")

    try:
        totales["limitaciones"] = adquirir_limitaciones()
    except Exception as e:
        log(f"[ERROR] Limitaciones: {e}")
        errores.append(f"limitaciones: {e}")

    try:
        totales["sscc"] = adquirir_sscc()
    except Exception as e:
        log(f"[ERROR] SSCC: {e}")
        errores.append(f"sscc: {e}")

    log("=" * 60)
    log("RESUMEN:")
    for fuente, n in totales.items():
        log(f"  {fuente}: {n} registros")

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
