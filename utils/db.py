import os
from supabase import create_client, Client

_client: Client | None = None


def _get_credentials() -> tuple[str, str]:
    """
    Obtiene URL y key de Supabase.
    Prioridad: st.secrets (Streamlit Cloud) → variables de entorno (.env local).
    """
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY", "")
    except Exception:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL y SUPABASE_KEY no están configurados.")
    return url, key


def get_client() -> Client:
    global _client
    if _client is None:
        url, key = _get_credentials()
        _client = create_client(url, key)
    return _client


# ── Generación Real ────────────────────────────────────────────────────────────

def upsert_generacion_real(registros: list[dict]) -> int:
    if not registros:
        return 0
    sb = get_client()
    # upsert en lotes de 500
    for i in range(0, len(registros), 500):
        lote = registros[i:i + 500]
        sb.table("generacion_real_ernc").upsert(
            lote, on_conflict="parque,fecha_hora"
        ).execute()
    return len(registros)


# ── Generación Programada PCP ─────────────────────────────────────────────────

def upsert_generacion_programada(registros: list[dict]) -> int:
    if not registros:
        return 0
    # Deduplicar por clave única antes de enviar — PCP puede tener repetidos en el mismo lote
    vistos: set[tuple] = set()
    unicos = []
    for r in registros:
        clave = (r["parque"], r["fecha_hora"], r.get("fuente", "CEN_PCP"))
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(r)
    sb = get_client()
    for i in range(0, len(unicos), 500):
        lote = unicos[i:i + 500]
        sb.table("generacion_programada_ernc").upsert(
            lote, on_conflict="parque,fecha_hora,fuente"
        ).execute()
    return len(unicos)


# ── Meteorología ───────────────────────────────────────────────────────────────

def upsert_meteo(registros: list[dict]) -> int:
    if not registros:
        return 0
    sb = get_client()
    for i in range(0, len(registros), 500):
        lote = registros[i:i + 500]
        sb.table("meteo_ernc").upsert(
            lote, on_conflict="parque,fecha_hora,fuente"
        ).execute()
    return len(registros)


# ── CMG ────────────────────────────────────────────────────────────────────────

def upsert_cmg(registros: list[dict]) -> int:
    if not registros:
        return 0
    sb = get_client()
    sb.table("cmg_ernc").upsert(
        registros, on_conflict="nodo,fecha_hora"
    ).execute()
    return len(registros)


# ── Limitaciones ───────────────────────────────────────────────────────────────

def upsert_limitaciones(registros: list[dict]) -> int:
    if not registros:
        return 0
    sb = get_client()
    sb.table("limitaciones_ernc").upsert(
        registros, on_conflict="id"
    ).execute()
    return len(registros)


# ── SSCC ────────────────────────────────────────────────────────────────────────

def upsert_sscc(registros: list[dict]) -> int:
    if not registros:
        return 0
    sb = get_client()
    sb.table("sscc_ernc").upsert(
        registros, on_conflict="fecha,id_configuracion,instruccion_sscc,inicio_periodo"
    ).execute()
    return len(registros)


# ── Queries de lectura para el dashboard ──────────────────────────────────────

def _ahora_santiago():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=-3)))


def query_gen_real_ultimas_horas(horas: int = 48) -> list[dict]:
    from datetime import timedelta
    sb = get_client()
    desde = (_ahora_santiago() - timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S")
    res = (sb.table("generacion_real_ernc")
             .select("*")
             .gte("fecha_hora", desde)
             .order("fecha_hora", desc=True)
             .execute())
    return res.data or []


def query_gen_prog_ultimas_horas(horas: int = 48) -> list[dict]:
    from datetime import timedelta
    sb = get_client()
    desde = (_ahora_santiago() - timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S")
    res = (sb.table("generacion_programada_ernc")
             .select("parque,fecha_hora,gen_programada_mw,capacidad_disponible_mw,costo_generacion_usd,fuente")
             .gte("fecha_hora", desde)
             .order("fecha_hora", desc=True)
             .execute())
    return res.data or []


def query_meteo_parque(parque: str, horas: int = 48) -> list[dict]:
    from datetime import timedelta
    sb = get_client()
    desde = (_ahora_santiago() - timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S")
    res = (sb.table("meteo_ernc")
             .select("*")
             .eq("parque", parque)
             .gte("fecha_hora", desde)
             .order("fecha_hora", desc=True)
             .execute())
    return res.data or []


def query_meteo_forecast(dias: int = 7) -> list[dict]:
    from datetime import timedelta
    sb = get_client()
    ahora = _ahora_santiago().strftime("%Y-%m-%d %H:%M:%S")
    hasta = (_ahora_santiago() + timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    res = (sb.table("meteo_ernc")
             .select("*")
             .eq("es_forecast", True)
             .gte("fecha_hora", ahora)
             .lte("fecha_hora", hasta)
             .order("fecha_hora")
             .execute())
    return res.data or []


def query_limitaciones_activas() -> list[dict]:
    sb = get_client()
    res = (sb.table("limitaciones_ernc")
             .select("*")
             .is_("fecha_efectiva_retorno", "null")
             .order("fecha_perturbacion", desc=True)
             .execute())
    return res.data or []


def query_ultima_hora_gen() -> str | None:
    sb = get_client()
    res = (sb.table("generacion_real_ernc")
             .select("fecha_hora")
             .order("fecha_hora", desc=True)
             .limit(1)
             .execute())
    if res.data:
        return res.data[0]["fecha_hora"]
    return None


def query_cmg_ultimo() -> list[dict]:
    sb = get_client()
    # Trae el último registro de CMG por nodo (ordenado desc, 8 nodos máx)
    res = (sb.table("cmg_ernc")
             .select("nodo,cmg_usd_mwh,fecha_hora")
             .order("fecha_hora", desc=True)
             .limit(20)
             .execute())
    # Deduplicar por nodo — quedarse con el más reciente
    vistos: set[str] = set()
    resultado = []
    for r in (res.data or []):
        if r["nodo"] not in vistos:
            vistos.add(r["nodo"])
            resultado.append(r)
    return resultado
