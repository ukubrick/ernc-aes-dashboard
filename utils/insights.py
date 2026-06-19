"""
Motor de alertas e insights automáticos para el portfolio ERNC.
Evalúa condiciones meteorológicas, operacionales y de mercado.
Retorna lista de insights ordenados por severidad.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from config import (
    NOMBRE_DISPLAY, TECNOLOGIA, PMAX,
    PARQUES_SOLAR, PARQUES_EOLICA, CMG_NODO,
)
from utils.calculos import calcular_factor_planta, calcular_desvio

Severidad = Literal["critico", "alerta", "info", "positivo"]

_ICONS = {
    "critico":  "🔴",
    "alerta":   "🟡",
    "info":     "🔵",
    "positivo": "🟢",
}

_ORDEN = {"critico": 0, "alerta": 1, "info": 2, "positivo": 3}


@dataclass
class Insight:
    severidad: Severidad
    parque: str | None          # None = portfolio global
    titulo: str
    detalle: str
    valor: float | None = None
    unidad: str = ""
    categoria: str = "general"  # general | meteo | operacional | mercado

    @property
    def icono(self) -> str:
        return _ICONS[self.severidad]

    @property
    def nombre_parque(self) -> str:
        if self.parque:
            return NOMBRE_DISPLAY.get(self.parque, self.parque)
        return "Portfolio"


def _get_meteo_actual(parque: str) -> dict | None:
    """Último registro meteo histórico (es_forecast=False) del parque."""
    try:
        from utils.db import get_client
        sb = get_client()
        desde = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
        res = (
            sb.table("meteo_ernc")
            .select("*")
            .eq("parque", parque)
            .eq("es_forecast", False)
            .gte("fecha_hora", desde)
            .order("fecha_hora", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception:
        return None


# ── Reglas de insight ─────────────────────────────────────────────────────────

def _check_desvio(
    parque: str,
    gen_por_parque: dict,
    prog_por_parque: dict,
    insights: list[Insight],
) -> None:
    gen  = gen_por_parque.get(parque)
    prog = prog_por_parque.get(parque)
    if gen is None or prog is None or prog == 0:
        return
    dev = calcular_desvio(gen, prog)
    pct = dev["desvio_pct"]
    if pct is None:
        return

    if abs(pct) > 25:
        insights.append(Insight(
            severidad="critico",
            parque=parque,
            titulo="Desvío crítico vs PCP",
            detalle=f"Generación real {gen:.1f} MW vs programada {prog:.1f} MW ({pct:+.1f}%)",
            valor=pct,
            unidad="%",
            categoria="operacional",
        ))
    elif abs(pct) > 15:
        insights.append(Insight(
            severidad="alerta",
            parque=parque,
            titulo="Desvío elevado vs PCP",
            detalle=f"Generación real {gen:.1f} MW vs programada {prog:.1f} MW ({pct:+.1f}%)",
            valor=pct,
            unidad="%",
            categoria="operacional",
        ))


def _check_eficiencia_solar(parque: str, gen_por_parque: dict, insights: list[Insight]) -> None:
    meteo = _get_meteo_actual(parque)
    if not meteo:
        return
    ghi = meteo.get("ghi_wm2") or 0
    p_est = meteo.get("p_fv_estimada_mw") or 0
    gen = gen_por_parque.get(parque)
    is_day = meteo.get("is_day")

    if not is_day or ghi < 400 or p_est <= 0 or gen is None:
        return

    ratio = gen / p_est * 100
    if ratio < 75:
        insights.append(Insight(
            severidad="alerta",
            parque=parque,
            titulo="Eficiencia FV baja sin causa meteo",
            detalle=(
                f"GHI={ghi:.0f} W/m² (recurso bueno), modelo estima {p_est:.1f} MW, "
                f"real {gen:.1f} MW → ratio {ratio:.0f}%. Posible falla o limitación."
            ),
            valor=ratio,
            unidad="%",
            categoria="operacional",
        ))
    elif ratio > 95:
        insights.append(Insight(
            severidad="positivo",
            parque=parque,
            titulo="Excelente rendimiento FV",
            detalle=f"Eficiencia {ratio:.0f}% respecto al modelo (GHI={ghi:.0f} W/m²)",
            valor=ratio,
            unidad="%",
            categoria="operacional",
        ))


def _check_camanchaca(parque: str, insights: list[Insight]) -> None:
    meteo = _get_meteo_actual(parque)
    if not meteo:
        return
    cloud_low = meteo.get("cloudcover_low_pct") or 0
    cloud_total = meteo.get("cloud_cover_pct") or 0
    # Camanchaca: nubosidad baja alta pero cielo total despejado
    if cloud_low > 60 and cloud_total < 35:
        insights.append(Insight(
            severidad="alerta",
            parque=parque,
            titulo="Posible camanchaca detectada",
            detalle=f"Nubosidad baja {cloud_low:.0f}% con cielo general {cloud_total:.0f}%. Puede reducir GHI.",
            valor=cloud_low,
            unidad="%",
            categoria="meteo",
        ))


def _check_viento_cut_out(parque: str, insights: list[Insight]) -> None:
    meteo = _get_meteo_actual(parque)
    if not meteo:
        return
    gusts = meteo.get("wind_gusts_10m") or 0
    v100 = meteo.get("wind_speed_100m") or 0

    if gusts > 20:
        insights.append(Insight(
            severidad="critico",
            parque=parque,
            titulo="Viento sobre cut-out",
            detalle=f"Ráfagas {gusts:.1f} m/s (umbral cut-out ~20 m/s). Posible parada de turbinas.",
            valor=gusts,
            unidad="m/s",
            categoria="meteo",
        ))
    elif gusts > 16:
        insights.append(Insight(
            severidad="alerta",
            parque=parque,
            titulo="Viento alto — acercándose al cut-out",
            detalle=f"Ráfagas {gusts:.1f} m/s, viento hub {v100:.1f} m/s.",
            valor=gusts,
            unidad="m/s",
            categoria="meteo",
        ))


def _check_wind_shear(parque: str, insights: list[Insight]) -> None:
    meteo = _get_meteo_actual(parque)
    if not meteo:
        return
    alpha = meteo.get("wind_shear_alpha") or 0
    if alpha > 0.30:
        insights.append(Insight(
            severidad="alerta",
            parque=parque,
            titulo="Wind shear elevado",
            detalle=(
                f"α={alpha:.3f} (>0.30 indica atmósfera estable). "
                "Las turbinas traseras pueden generar menos por estelas más persistentes."
            ),
            valor=alpha,
            unidad="",
            categoria="meteo",
        ))


def _check_factor_planta_alto(parque: str, gen_por_parque: dict, insights: list[Insight]) -> None:
    gen = gen_por_parque.get(parque)
    fp = calcular_factor_planta(gen, PMAX[parque])
    if fp and fp > 90:
        insights.append(Insight(
            severidad="positivo",
            parque=parque,
            titulo="Factor de planta excepcional",
            detalle=f"Factor de planta {fp:.1f}% — recurso excelente.",
            valor=fp,
            unidad="%",
            categoria="operacional",
        ))


def _check_cmg_bajo(cmg_crucero: float | None, insights: list[Insight]) -> None:
    if cmg_crucero is None:
        return
    if cmg_crucero < 5:
        insights.append(Insight(
            severidad="alerta",
            parque=None,
            titulo="CMG muy bajo — ingreso mínimo",
            detalle=f"CMG CRUCERO {cmg_crucero:.1f} USD/MWh. Ingreso horario del portfolio norte mínimo.",
            valor=cmg_crucero,
            unidad="USD/MWh",
            categoria="mercado",
        ))
    elif cmg_crucero > 200:
        insights.append(Insight(
            severidad="positivo",
            parque=None,
            titulo="CMG alto — ingreso elevado",
            detalle=f"CMG CRUCERO {cmg_crucero:.1f} USD/MWh. Ingreso horario favorable.",
            valor=cmg_crucero,
            unidad="USD/MWh",
            categoria="mercado",
        ))


def _check_limitaciones(lim_rows: list[dict], insights: list[Insight]) -> None:
    for lim in lim_rows:
        parque = lim.get("parque")
        potencia = lim.get("potencia")
        instalacion = lim.get("instalacion_nombre", "")
        insights.append(Insight(
            severidad="critico",
            parque=parque,
            titulo="Limitación de transmisión activa",
            detalle=f"{instalacion} — {potencia} {lim.get('unidad_medida_potencia', 'MW')} restringidos.",
            valor=potencia,
            unidad=lim.get("unidad_medida_potencia", "MW"),
            categoria="operacional",
        ))


# ── Función principal ─────────────────────────────────────────────────────────

def evaluar_insights(
    gen_por_parque: dict[str, float | None],
    prog_por_parque: dict[str, float | None],
    cmg_crucero: float | None,
    lim_rows: list[dict],
) -> list[Insight]:
    """
    Evalúa todas las reglas y retorna lista de Insights ordenados por severidad.
    Llama a Supabase para obtener datos meteo actuales.
    """
    insights: list[Insight] = []

    # Reglas globales
    _check_cmg_bajo(cmg_crucero, insights)
    _check_limitaciones(lim_rows, insights)

    # Reglas por parque solar
    for p in PARQUES_SOLAR:
        _check_desvio(p, gen_por_parque, prog_por_parque, insights)
        _check_eficiencia_solar(p, gen_por_parque, insights)
        _check_camanchaca(p, insights)
        _check_factor_planta_alto(p, gen_por_parque, insights)

    # Reglas por parque eólico
    for p in PARQUES_EOLICA:
        _check_desvio(p, gen_por_parque, prog_por_parque, insights)
        _check_viento_cut_out(p, insights)
        _check_wind_shear(p, insights)
        _check_factor_planta_alto(p, gen_por_parque, insights)

    # Ordenar: crítico → alerta → info → positivo
    insights.sort(key=lambda x: _ORDEN[x.severidad])
    return insights
