"""Fórmulas derivadas para parques ERNC — temperatura celda, potencias estimadas, KPIs."""
import math
from config import (
    PANEL_NOCT, PANEL_GAMMA, AIRE_R, PMAX,
    TURBINA_CP, TURBINA_V_CUTIN, TURBINA_V_RATED, TURBINA_V_CUTOUT,
    SHEAR_ALPHA_MIN, SHEAR_ALPHA_MAX,
)


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


def calcular_potencia_fv_estimada(gti: float, tc: float, pmax_mw: float) -> float:
    """
    P = Ppico × (GTI/1000) × [1 + γ(Tc - 25)]
    Retorna MW estimados. Cap a pmax_mw.
    """
    if gti is None or gti <= 0:
        return 0.0
    eficiencia_temp = 1.0 + PANEL_GAMMA * (tc - 25.0)
    p = pmax_mw * (gti / 1000.0) * eficiencia_temp
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

def interpolar_viento_100m(v_80m: float, v_120m: float) -> tuple[float, float]:
    """
    Interpolación ley de potencia entre 80m y 120m → v100m y α (wind shear).
    Retorna (v100m, alpha). Unidades de entrada: m/s.

    A vientos muy bajos (<1.5 m/s) la razón v120/v80 es ruido y el exponente α se
    dispara a valores no físicos; en ese caso se interpola linealmente y α=0.
    """
    if not v_80m or not v_120m or v_80m <= 0 or v_120m <= 0:
        return (round(v_80m or 0.0, 3), 0.0)
    # Con vientos despreciables, el cizalle no es informativo
    if v_80m < 1.5 or v_120m < 1.5:
        v100m = v_80m + (v_120m - v_80m) * (100.0 - 80.0) / (120.0 - 80.0)
        return (round(max(0.0, v100m), 3), 0.0)
    try:
        alpha = math.log(v_120m / v_80m) / math.log(120.0 / 80.0)
        alpha = max(SHEAR_ALPHA_MIN, min(alpha, SHEAR_ALPHA_MAX))  # acotar a rango físico
        v100m = v_80m * (100.0 / 80.0) ** alpha
        return (round(v100m, 3), round(alpha, 4))
    except (ValueError, ZeroDivisionError):
        return (round(v_80m, 3), 0.0)


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
    """
    if gen_real_mw is None or gen_prog_mw is None or gen_prog_mw == 0:
        return {"desvio_mw": None, "desvio_pct": None, "semaforo": None}

    desvio_mw  = round(gen_real_mw - gen_prog_mw, 4)
    desvio_pct = round(desvio_mw / gen_prog_mw * 100.0, 2)

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
