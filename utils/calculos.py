"""Fórmulas derivadas para parques ERNC — temperatura celda, potencias estimadas, KPIs."""
import math
from config import (
    PANEL_NOCT, PANEL_GAMMA, AIRE_R, PMAX,
    TURBINA_CP, TURBINA_V_CUTIN, TURBINA_V_RATED, TURBINA_V_CUTOUT,
    SHEAR_ALPHA_MIN, SHEAR_ALPHA_MAX,
    TRACKER_GAIN, TRACKER_AVAIL, TRACKER_STOW_WIND_MS, TRACKER_POA_MAX,
)

# PCP mínimo (MW) para que el % de desvío sea representativo. Por debajo se
# reporta solo el desvío en MW. Acota además el % a ±DESVIO_PCT_CAP.
DESVIO_BASE_MIN_MW = 1.0
DESVIO_PCT_CAP     = 200.0


# ── Solar FV ──────────────────────────────────────────────────────────────────

def calcular_temp_celda(t_amb: float, ghi: float, wind_ms: float = 1.0) -> float:
    """
    Temperatura de celda FV con modelo NOCT ajustado por viento.
    Ref: IEC 61215 — Tc = Ta + (NOCT-20)/800 * G * (1 - wind/wind_ref)
    """
    if ghi is None or ghi <= 0:
        return t_amb if t_amb is not None else 25.0
    wind = max(wind_ms or 1.0, 0.5)
    factor_viento = max(0.5, 1.0 - (wind - 1.0) / 10.0)
    tc = t_amb + (PANEL_NOCT - 20.0) / 800.0 * ghi * factor_viento
    return round(tc, 2)


def poa_tracker(gti_fijo: float, ghi: float, wind_ms: float = 0.0,
                gusts_ms: float | None = None) -> float:
    """
    Irradiancia en el plano (POA) para seguidores de 1 eje, a partir del GTI de tilt
    fijo de Open-Meteo. Modelo pragmático:
      - Stow por viento alto: si viento/ráfaga ≥ TRACKER_STOW_WIND_MS, los paneles se
        ponen horizontales por protección → POA ≈ GHI (no se aprovecha el tracking).
      - Operación normal: POA = GTI_fijo × TRACKER_GAIN, nunca menor que GHI (un tracker
        no rinde peor que horizontal) y acotado a TRACKER_POA_MAX.
    """
    if gti_fijo is None or gti_fijo <= 0:
        return 0.0
    ghi = ghi or 0.0
    viento = max(wind_ms or 0.0, gusts_ms or 0.0)
    if viento >= TRACKER_STOW_WIND_MS:
        return round(min(max(ghi, 0.0), TRACKER_POA_MAX), 2)
    poa = gti_fijo * TRACKER_GAIN
    poa = max(poa, ghi)
    return round(min(poa, TRACKER_POA_MAX), 2)


def calcular_potencia_fv_estimada(gti: float, tc: float, pmax_mw: float,
                                  availability: float = TRACKER_AVAIL) -> float:
    """
    P = Ppico × (POA/1000) × [1 + γ(Tc - 25)] × disponibilidad
    `gti` aquí ya debe ser el POA del tracker (ver poa_tracker). El factor
    `availability` (0.80) refleja la confiabilidad de los seguidores. Cap a pmax_mw.
    """
    if gti is None or gti <= 0:
        return 0.0
    eficiencia_temp = 1.0 + PANEL_GAMMA * (tc - 25.0)
    p = pmax_mw * (gti / 1000.0) * eficiencia_temp * availability
    return round(max(0.0, min(p, pmax_mw)), 4)


def calcular_eficiencia_real(gen_real_mw: float, p_estimada_mw: float) -> float | None:
    """
    Ratio real/modelo en %. None si el estimado es 0 o inválido.
    Detecta fallas y limitaciones (< 75% → sospechoso).
    """
    if not p_estimada_mw or p_estimada_mw <= 0:
        return None
    if gen_real_mw is None:
        return None
    return round(gen_real_mw / p_estimada_mw * 100.0, 1)


# ── Eólica ────────────────────────────────────────────────────────────────────

def interpolar_viento_100m(v_80m: float, v_120m: float, v_10m: float | None = None) -> tuple[float, float]:
    """
    Interpolación ley de potencia entre dos alturas → v100m y α (wind shear).
    Retorna (v100m, alpha). Unidades de entrada: m/s.

    A vientos muy bajos (<1.5 m/s) la razón entre alturas es ruido y el exponente α
    se dispara a valores no físicos; en ese caso se interpola linealmente y α=0.

    Saneamiento del nivel 80m: en algunas celdas Open-Meteo entrega un
    wind_speed_80m corrupto (cae fuera del rango [v10, v120], ej. PE Los Cururos
    donde v80<v10 el 82% de las horas) → α se satura siempre al tope. Si se pasa
    v_10m y el v80 es no físico (fuera del bracket 10m–120m), se descarta el 80m y
    el cizalle se calcula con el par fiable 10m–120m.
    """
    h_baja, v_baja, h_alta, v_alta = 80.0, v_80m, 120.0, v_120m

    # Si el 80m es no físico respecto al bracket 10m–120m, usar 10m–120m
    if v_10m and v_10m > 0 and v_120m and v_120m > 0:
        lo, hi = min(v_10m, v_120m), max(v_10m, v_120m)
        tol = 0.05 * hi  # tolerancia 5% para no descartar por ruido menor
        if (not v_80m) or v_80m <= 0 or v_80m < lo - tol or v_80m > hi + tol:
            h_baja, v_baja = 10.0, v_10m

    if not v_baja or not v_alta or v_baja <= 0 or v_alta <= 0:
        return (round(v_baja or v_80m or 0.0, 3), 0.0)
    # Con vientos despreciables, el cizalle no es informativo
    if v_baja < 1.5 or v_alta < 1.5:
        v100m = v_baja + (v_alta - v_baja) * (100.0 - h_baja) / (h_alta - h_baja)
        return (round(max(0.0, v100m), 3), 0.0)
    try:
        alpha = math.log(v_alta / v_baja) / math.log(h_alta / h_baja)
        alpha = max(SHEAR_ALPHA_MIN, min(alpha, SHEAR_ALPHA_MAX))  # acotar a rango físico
        v100m = v_baja * (100.0 / h_baja) ** alpha
        return (round(v100m, 3), round(alpha, 4))
    except (ValueError, ZeroDivisionError):
        return (round(v_baja, 3), 0.0)


def calcular_densidad_aire(temp_c: float, presion_hpa: float) -> float:
    """ρ = P / (R × T) en kg/m³. T en Kelvin, P en Pa."""
    if temp_c is None or presion_hpa is None:
        return 1.225  # densidad estándar ISA
    T = temp_c + 273.15
    P = presion_hpa * 100.0  # hPa → Pa
    return round(P / (AIRE_R * T), 4)


def calcular_potencia_eolica_estimada(
    v100m: float,
    densidad: float,
    pmax_mw: float,
    v_cutin: float = TURBINA_V_CUTIN,
    v_rated: float = TURBINA_V_RATED,
    v_cutout: float = TURBINA_V_CUTOUT,
) -> float:
    """
    Curva de potencia simplificada de turbina (v en m/s):
      v < cut-in            → 0       (no arranca)
      cut-in ≤ v < rated    → rampa cúbica P = Pmax·(v³−v_in³)/(v_rated³−v_in³)
      rated ≤ v ≤ cut-out   → Pmax    (corregido por densidad del aire)
      v > cut-out           → 0       (parada de seguridad)

    La corrección por densidad ρ/ρ_ref solo se aplica en la zona rampa/nominal,
    no extiende la potencia más allá de Pmax.
    """
    if not v100m or v100m <= 0:
        return 0.0
    v = float(v100m)
    if v < v_cutin or v > v_cutout:
        return 0.0

    rho_factor = max(0.5, min(densidad / 1.225, 1.15))  # corrección acotada
    if v >= v_rated:
        p_mw = pmax_mw * rho_factor
    else:
        frac = (v ** 3 - v_cutin ** 3) / (v_rated ** 3 - v_cutin ** 3)
        p_mw = pmax_mw * rho_factor * max(0.0, frac)
    return round(max(0.0, min(p_mw, pmax_mw)), 4)


# ── KPIs universales ──────────────────────────────────────────────────────────

def calcular_factor_planta(gen_real_mw: float, pmax_mw: float) -> float | None:
    """Factor de planta en %. None si pmax = 0."""
    if not pmax_mw or gen_real_mw is None:
        return None
    return round(gen_real_mw / pmax_mw * 100.0, 2)


def calcular_desvio(gen_real_mw: float, gen_prog_mw: float) -> dict:
    """
    Retorna dict con desvio_mw, desvio_pct, semaforo ('verde'|'amarillo'|'rojo').
    Verde: |%| ≤ 15 | Amarillo: 15 < |%| ≤ 25 | Rojo: |%| > 25.

    El % se calcula sobre el PCP. Cuando el PCP es muy bajo (p.ej. solar al
    amanecer programado ~0 MW) la división explota a cientos/miles de %, un valor
    sin sentido operacional. Por eso: (1) si el PCP es menor a DESVIO_BASE_MIN_MW
    no se reporta % (el desvío en MW sigue disponible); (2) el % se acota a
    ±DESVIO_PCT_CAP para no mostrar cifras absurdas. El semáforo no se ve afectado
    (cualquier desvío grande ya es rojo).
    """
    if gen_real_mw is None or gen_prog_mw is None or gen_prog_mw == 0:
        return {"desvio_mw": None, "desvio_pct": None, "semaforo": None}

    desvio_mw = round(gen_real_mw - gen_prog_mw, 4)

    # PCP demasiado bajo → el % no es representativo; solo se reporta MW.
    if abs(gen_prog_mw) < DESVIO_BASE_MIN_MW:
        return {"desvio_mw": desvio_mw, "desvio_pct": None, "semaforo": None}

    desvio_pct = round(desvio_mw / gen_prog_mw * 100.0, 2)
    desvio_pct = max(-DESVIO_PCT_CAP, min(DESVIO_PCT_CAP, desvio_pct))

    if abs(desvio_pct) <= 15:
        semaforo = "verde"
    elif abs(desvio_pct) <= 25:
        semaforo = "amarillo"
    else:
        semaforo = "rojo"

    return {"desvio_mw": desvio_mw, "desvio_pct": desvio_pct, "semaforo": semaforo}


def calcular_ingreso_estimado(gen_real_mwh: float, cmg_usd_mwh: float) -> float | None:
    """Ingreso horario estimado en USD = gen_real (MWh) × CMG (USD/MWh)."""
    if gen_real_mwh is None or cmg_usd_mwh is None:
        return None
    return round(gen_real_mwh * cmg_usd_mwh, 2)
