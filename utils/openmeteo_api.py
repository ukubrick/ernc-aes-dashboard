"""Wrapper Open-Meteo para parques ERNC — Sesión 3."""
import time
import logging
from datetime import datetime, timedelta

import openmeteo_requests
import requests_cache
from retry_requests import retry

from config import (
    TZ_CHILE,
    COORDENADAS,
    TECNOLOGIA,
    OPENMETEO_VARS_SOLAR,
    OPENMETEO_VARS_EOLICA,
    PANEL_TILT_DEG,
    PANEL_AZIMUTH,
    DIAS_VENTANA,
)

logger = logging.getLogger(__name__)

# ── Cliente Open-Meteo con caché y retry ──────────────────────────────────────
_cache_session = requests_cache.CachedSession(".cache_openmeteo", expire_after=1800)
_retry_session = retry(_cache_session, retries=3, backoff_factor=0.3)
_client = openmeteo_requests.Client(session=_retry_session)

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_HISTORICAL_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"


def _params_solar(lat: float, lon: float, start: str, end: str) -> dict:
    return {
        "latitude": lat,
        "longitude": lon,
        "hourly": OPENMETEO_VARS_SOLAR,
        "start_date": start,
        "end_date": end,
        "timezone": "America/Santiago",
        "tilt": PANEL_TILT_DEG,
        "azimuth": PANEL_AZIMUTH,
        "wind_speed_unit": "ms",   # CRÍTICO: por defecto Open-Meteo entrega km/h
    }


def _params_eolica(lat: float, lon: float, start: str, end: str) -> dict:
    return {
        "latitude": lat,
        "longitude": lon,
        "hourly": OPENMETEO_VARS_EOLICA,
        "start_date": start,
        "end_date": end,
        "timezone": "America/Santiago",
        "wind_speed_unit": "ms",   # CRÍTICO: por defecto Open-Meteo entrega km/h → modelo sobreestimaba
    }


# Mapa nombre Open-Meteo → columna en meteo_ernc
_CAMPO_MAP = {
    "shortwave_radiation":      "ghi_wm2",
    "direct_normal_irradiance": "dni_wm2",
    "diffuse_radiation":        "dhi_wm2",
    "global_tilted_irradiance": "gti_wm2",
    "temperature_2m":           "temp_2m",
    "windspeed_10m":            "wind_speed_10m",
    "windspeed_80m":            "wind_speed_80m",
    "windspeed_120m":           "wind_speed_120m",
    "winddirection_10m":        None,        # no se guarda directamente
    "winddirection_80m":        "wind_dir_80m",
    "windgusts_10m":            "wind_gusts_10m",
    "cloudcover":               "cloud_cover_pct",
    "cloudcover_low":           "cloudcover_low_pct",
    "is_day":                   "is_day",
    "surface_pressure":         "surface_pressure",
    "relativehumidity_2m":      "humidity_2m",
    "boundary_layer_height":    "boundary_layer_height",
    "precipitation":            "precipitation_mm",
}


def _aq_por_hora(lat: float, lon: float, start: str, end: str) -> dict[str, dict]:
    """Polvo/PM10 horario desde la Air Quality API (CAMS) para soiling predictivo.

    Devuelve {fecha_hora: {"dust_ugm3": x, "pm10_ugm3": y}}; {} si la API falla
    (la adquisición meteo no debe caerse por esta fuente secundaria).
    """
    from config import OPENMETEO_AQ_URL, OPENMETEO_VARS_AQ
    import pandas as pd
    try:
        responses = _client.weather_api(OPENMETEO_AQ_URL, params={
            "latitude": lat, "longitude": lon,
            "hourly": OPENMETEO_VARS_AQ,
            "start_date": start, "end_date": end,
            "timezone": "America/Santiago",
        })
        datos = responses[0].Hourly()
        fechas = pd.date_range(
            start=pd.Timestamp(datos.Time(), unit="s", tz="UTC"),
            end=pd.Timestamp(datos.TimeEnd(), unit="s", tz="UTC"),
            freq=pd.Timedelta(seconds=datos.Interval()),
            inclusive="left",
        ).tz_convert("America/Santiago")
        dust = datos.Variables(0).ValuesAsNumpy().tolist()
        pm10 = datos.Variables(1).ValuesAsNumpy().tolist()
        out = {}
        for j, ts in enumerate(fechas):
            d, p = dust[j], pm10[j]
            out[ts.strftime("%Y-%m-%d %H:%M:%S")] = {
                "dust_ugm3": None if d != d else round(float(d), 2),
                "pm10_ugm3": None if p != p else round(float(p), 2),
            }
        return out
    except Exception as exc:
        logger.warning(f"Air Quality API no disponible: {exc}")
        return {}


def _response_to_registros(response, parque: str, variables: list[str]) -> list[dict]:
    """Convierte una respuesta Open-Meteo a lista de dicts mapeados al schema de meteo_ernc."""
    import pandas as pd
    from datetime import datetime
    from utils.calculos import (
        calcular_temp_celda,
        calcular_potencia_fv_estimada,
        poa_tracker,
        interpolar_viento_100m,
        calcular_densidad_aire,
        calcular_potencia_eolica_estimada,
    )
    from config import TURBINA_V_CUTIN, TURBINA_V_RATED, TURBINA_V_CUTOUT
    from config import TECNOLOGIA, PMAX, PMAX_FP, TURBINA_PARQUE, stow_umbral

    tecnologia = TECNOLOGIA[parque]
    pmax = PMAX[parque]                       # capacidad bruta — modelo FV
    pmax_eo = PMAX_FP.get(parque, pmax)       # Pmax neta CEN — modelo eólico
    turbina = TURBINA_PARQUE.get(parque, {})
    ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    datos = response.Hourly()
    fechas = pd.date_range(
        start=pd.Timestamp(datos.Time(), unit="s", tz="UTC"),
        end=pd.Timestamp(datos.TimeEnd(), unit="s", tz="UTC"),
        freq=pd.Timedelta(seconds=datos.Interval()),
        inclusive="left",
    ).tz_convert("America/Santiago")

    vals: dict[str, list] = {}
    for i, var in enumerate(variables):
        arr = datos.Variables(i).ValuesAsNumpy().tolist()
        vals[var] = [None if (v != v) else float(v) for v in arr]

    registros = []
    for j, ts in enumerate(fechas):
        es_forecast = ts.strftime("%Y-%m-%d %H:%M:%S") >= ahora_str
        row: dict = {
            "parque": parque,
            "fecha_hora": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "fuente": "open-meteo",
            "es_forecast": es_forecast,
        }

        # Mapear variables API → columnas DB
        for var in variables:
            col = _CAMPO_MAP.get(var)
            if col is not None:
                v = vals[var][j]
                if col == "is_day":
                    row[col] = bool(v) if v is not None else None
                else:
                    row[col] = v

        # Calcular derivados según tecnología
        if tecnologia == "Solar":
            ghi   = row.get("ghi_wm2")
            gti   = row.get("gti_wm2")
            wind  = row.get("wind_speed_10m")
            gusts = row.get("wind_gusts_10m")
            temp  = row.get("temp_2m")
            tc = calcular_temp_celda(temp or 25.0, ghi or 0.0, wind or 1.0)
            row["temp_celda_c"] = tc
            # POA con seguidores de 1 eje (stow horizontal si viento alto) + derate disponibilidad
            poa = poa_tracker(gti or 0.0, ghi or 0.0, wind or 0.0, gusts,
                              stow_ms=stow_umbral(parque))
            row["p_fv_estimada_mw"] = calcular_potencia_fv_estimada(poa, tc, pmax)
        else:
            v80  = row.get("wind_speed_80m")
            v120 = vals["windspeed_120m"][j] if "windspeed_120m" in vals else None
            v10  = row.get("wind_speed_10m")
            temp = row.get("temp_2m")
            pres = row.get("surface_pressure")
            v100m, alpha = interpolar_viento_100m(v80 or 0.0, v120 or 0.0, v10)
            rho = calcular_densidad_aire(temp or 15.0, pres or 1013.25)
            row["wind_speed_100m"] = v100m
            row["wind_shear_alpha"] = alpha
            row["densidad_aire"] = rho
            row["p_eolica_estimada_mw"] = calcular_potencia_eolica_estimada(
                v100m, rho, pmax_eo,
                v_cutin=turbina.get("v_cutin", TURBINA_V_CUTIN),
                v_rated=turbina.get("v_rated", TURBINA_V_RATED),
                v_cutout=turbina.get("v_cutout", TURBINA_V_CUTOUT),
            )

        registros.append(row)

    return registros


def obtener_meteo_parque(
    parque: str,
    dias_historico: int = DIAS_VENTANA,
    dias_forecast: int = 7,
    pausa_seg: float = 1.0,
) -> list[dict]:
    """
    Consulta Open-Meteo para un parque: histórico + forecast.
    Devuelve lista de dicts lista para upsert en meteo_ernc.
    """
    coord = COORDENADAS[parque]
    tecnologia = TECNOLOGIA[parque]

    ahora = datetime.now(TZ_CHILE)
    start = (ahora - timedelta(days=dias_historico)).strftime("%Y-%m-%d")
    end   = (ahora + timedelta(days=dias_forecast)).strftime("%Y-%m-%d")

    if tecnologia == "Solar":
        params = _params_solar(coord["lat"], coord["lon"], start, end)
        variables = OPENMETEO_VARS_SOLAR
    else:
        params = _params_eolica(coord["lat"], coord["lon"], start, end)
        variables = OPENMETEO_VARS_EOLICA

    logger.info(f"[{parque}] Open-Meteo {start} → {end} ({tecnologia})")
    try:
        responses = _client.weather_api(OPENMETEO_URL, params=params)
        registros = _response_to_registros(responses[0], parque, variables)
        # Polvo/PM10 (soiling) solo en solares — grilla CAMS, endpoint aparte
        if tecnologia == "Solar":
            aq = _aq_por_hora(coord["lat"], coord["lon"], start, end)
            for row in registros:
                row.update(aq.get(row["fecha_hora"], {}))
        logger.info(f"[{parque}] {len(registros)} registros meteorológicos")
        time.sleep(pausa_seg)
        return registros
    except Exception as exc:
        logger.error(f"[{parque}] Error Open-Meteo: {exc}")
        return []


def obtener_meteo_todos(pausa_seg: float = 1.5) -> dict[str, list[dict]]:
    """Consulta Open-Meteo para los 11 parques. Devuelve dict parque→registros."""
    from config import PARQUES_TODOS
    resultado = {}
    for parque in PARQUES_TODOS:
        resultado[parque] = obtener_meteo_parque(parque, pausa_seg=pausa_seg)
    return resultado
