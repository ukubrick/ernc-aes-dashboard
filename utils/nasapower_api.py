"""NASA POWER — fuente independiente de irradiancia (validación del recurso solar).

NASA POWER publica datos satelitales/reanálisis horarios de GHI, temperatura y viento,
gratis y sin API key. Tiene un rezago real de ~2-3 meses (~85 días observados, no es
forecast), por lo que se usa para VALIDAR/benchmarkear el GHI de Open-Meteo y el modelo
físico contra una segunda fuente, cruzando por fecha_hora cuando ambas series solapan.

Se guarda en la tabla meteo_ernc con fuente='nasa-power' (mismas columnas ghi_wm2/temp_2m/
wind_speed_10m), de modo que el dashboard puede cruzarlo con el Open-Meteo existente.
"""
import requests
from datetime import datetime, timedelta, timezone

from config import COORDENADAS, NOMBRE_DISPLAY, TZ_CHILE, PARQUES_SOLAR

_BASE = "https://power.larc.nasa.gov/api/temporal/hourly/point"
# GHI, GHI cielo despejado, temp 2m, viento 10m
_PARAMS = "ALLSKY_SFC_SW_DWN,CLRSKY_SFC_SW_DWN,T2M,WS10M"
_FILL = -999.0


def fetch_nasa_meteo(parque: str, dias: int = 100) -> list[dict]:
    """Descarga GHI/temp/viento horario de NASA POWER para un parque.

    Ventana: desde hace `dias` días hasta hoy. NASA recorta sola las fechas sin dato, así
    que con el rezago real (~85 días) conviene una ventana amplia (~100 d) para alcanzarlo.
    Retorna registros listos para upsert_meteo() con fuente='nasa-power'.
    """
    if parque not in COORDENADAS:
        return []
    hoy = datetime.now(TZ_CHILE).date()
    start = (hoy - timedelta(days=dias)).strftime("%Y%m%d")
    end = hoy.strftime("%Y%m%d")
    coord = COORDENADAS[parque]

    try:
        r = requests.get(_BASE, params={
            "parameters": _PARAMS, "community": "RE",
            "latitude": coord["lat"], "longitude": coord["lon"],
            "start": start, "end": end, "format": "JSON",
            "time-standard": "UTC",
        }, timeout=60)
        r.raise_for_status()
        param = r.json().get("properties", {}).get("parameter", {})
    except Exception as e:
        print(f"[NASA] ERROR {parque}: {e}")
        return []

    ghi = param.get("ALLSKY_SFC_SW_DWN", {})
    t2m = param.get("T2M", {})
    ws = param.get("WS10M", {})

    registros = []
    for k, v in ghi.items():
        # k = "YYYYMMDDHH" en UTC → convertir a hora civil de Chile (America/Santiago)
        # para alinear con Open-Meteo. Pedir en LST desfasa ~2 h (hora solar ≠ hora civil).
        if v == _FILL:
            continue
        try:
            dt = datetime.strptime(k, "%Y%m%d%H").replace(tzinfo=timezone.utc).astimezone(TZ_CHILE)
        except ValueError:
            continue
        fecha_hora = dt.strftime("%Y-%m-%d %H:%M:%S")
        def _val(d):
            x = d.get(k)
            return None if x is None or x == _FILL else float(x)
        registros.append({
            "parque":         parque,
            "fecha_hora":     fecha_hora,
            "ghi_wm2":        float(v),
            "temp_2m":        _val(t2m),
            "wind_speed_10m": _val(ws),
            "fuente":         "nasa-power",
            "es_forecast":    False,
        })
    return registros


def fetch_nasa_solar_todos(dias: int = 100) -> list[dict]:
    """NASA POWER para los parques solares (el recurso clave a validar es el FV)."""
    todos = []
    for parque in PARQUES_SOLAR:
        recs = fetch_nasa_meteo(parque, dias)
        print(f"[NASA] {NOMBRE_DISPLAY[parque]}: {len(recs)} registros")
        todos.extend(recs)
    return todos
