"""KPIs generales del portfolio ERNC — tema claro, paleta AES, cards con explicacion inline."""
import streamlit as st

from config import (
    PMAX_FP_TOTAL, PMAX_FP_TOTAL_SOLAR, PMAX_FP_TOTAL_EOLICA,
    PARQUES_SOLAR, PARQUES_EOLICA, CMG_NODOS_TODOS, BESS,
)
from utils.calculos import calcular_factor_planta, calcular_desvio

# Paleta AES
AES_AZUL    = "#3B4CE8"
AES_CYAN    = "#4DC8DC"
AES_VIOLETA = "#9B6FD4"
AES_VERDE   = "#5AB848"
AES_ROJO    = "#EF4444"
AES_AMBAR   = "#F59E0B"
AES_MUTED   = "#6B7280"
AES_TEXTO   = "#1A1F36"

_SEM_COLOR = {"verde": AES_VERDE, "amarillo": AES_AMBAR, "rojo": AES_ROJO}

# Nodo de otro sistema eléctrico (SIC sur extremo) — se excluye del promedio CMG.
_CMG_NODO_EXCLUIDO = "P.MONTT_______220"

_GRID_CSS = """
<style>
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:4px 0 2px 0}
@media(max-width:1500px){.kpi-grid{grid-template-columns:repeat(3,1fr)}}
@media(max-width:1100px){.kpi-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:620px){.kpi-grid{grid-template-columns:repeat(1,1fr)}}
.kpi-card{background:#FFFFFF;border:1px solid #E5E7EB;border-radius:12px;
  padding:14px 16px;box-shadow:0 2px 12px rgba(59,76,232,0.07);
  display:flex;flex-direction:column;gap:3px;
  transition:transform .2s ease,box-shadow .2s ease;animation:fadeInUp .4s ease both}
.kpi-card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(59,76,232,0.14)}
.kpi-label{font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.8px;color:#6B7280}
.kpi-value{font-size:23px;font-weight:800;color:#1A1F36;line-height:1.15}
.kpi-delta{font-size:12px;font-weight:600;min-height:16px}
.kpi-note{font-size:10px;color:#9aa1ad;line-height:1.35;margin-top:3px;
  border-top:1px solid #F1F2F4;padding-top:5px}
</style>
"""


def _card(color: str, label: str, value: str, delta: str | None,
          delta_color: str, note: str) -> str:
    delta_html = (
        f"<div class='kpi-delta' style='color:{delta_color}'>{delta}</div>"
        if delta else "<div class='kpi-delta'></div>"
    )
    return (
        f"<div class='kpi-card' style='border-top:4px solid {color}'>"
        f"<div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value'>{value}</div>"
        f"{delta_html}"
        f"<div class='kpi-note'>{note}</div>"
        f"</div>"
    )


def render_kpis(
    gen_por_parque: dict,
    prog_por_parque: dict,
    cmg_crucero: float | None,
    n_limitaciones_activas: int,
    ultima_hora: str | None,
    cmg_rows: list | None = None,
    bess_rows: list | None = None,
) -> None:
    gen_total  = sum(v for v in gen_por_parque.values() if v is not None)
    gen_solar  = sum(gen_por_parque.get(p) or 0 for p in PARQUES_SOLAR)
    gen_eolica = sum(gen_por_parque.get(p) or 0 for p in PARQUES_EOLICA)
    prog_total = sum(v for v in prog_por_parque.values() if v is not None)

    fp_total   = calcular_factor_planta(gen_total,  PMAX_FP_TOTAL)
    fp_solar   = calcular_factor_planta(gen_solar,  PMAX_FP_TOTAL_SOLAR)
    fp_eolica  = calcular_factor_planta(gen_eolica, PMAX_FP_TOTAL_EOLICA)
    desvio     = calcular_desvio(gen_total, prog_total)
    semaforo   = desvio["semaforo"]
    desvio_pct = desvio["desvio_pct"]

    # CMG promedio del SEN — excluye P.MONTT (pertenece a otro sistema).
    nodos_validos = [n for n in CMG_NODOS_TODOS if n != _CMG_NODO_EXCLUIDO]
    cmg_idx  = {r["nodo"]: r.get("cmg_usd_mwh") for r in (cmg_rows or [])}
    cmg_hora_idx = {r["nodo"]: r.get("fecha_hora") for r in (cmg_rows or [])}
    cmg_vals = [cmg_idx[n] for n in nodos_validos if cmg_idx.get(n) is not None]
    cmg_prom = round(sum(cmg_vals) / len(cmg_vals), 1) if cmg_vals else None
    cmg_horas = [cmg_hora_idx[n] for n in nodos_validos if cmg_hora_idx.get(n)]
    cmg_hora = max(cmg_horas)[11:16] if cmg_horas else "—"
    ingreso_total = round(gen_total * (cmg_prom or 0) / 1000, 1) if cmg_prom else None

    hora_gen = ultima_hora[11:16] if ultima_hora else "—"

    # ── Construcción de las 6 cards ──────────────────────────────────────────
    cards = []

    cards.append(_card(
        AES_AZUL, "Generacion Total", f"{gen_total:,.1f} MW",
        f"↑ FP {fp_total:.1f}%" if fp_total else None, AES_VERDE,
        f"Suma 11 parques · Pmax neta {PMAX_FP_TOTAL:,.0f} MW · CEN gen-real · {hora_gen} hrs",
    ))

    cards.append(_card(
        AES_AZUL, "Solar FV", f"{gen_solar:,.1f} MW",
        f"↑ FP {fp_solar:.1f}%" if fp_solar else None, AES_VERDE,
        f"6 parques FV norte · Pmax neta {PMAX_FP_TOTAL_SOLAR:,.0f} MW · FP=gen/Pmax neta · {hora_gen} hrs",
    ))

    cards.append(_card(
        AES_CYAN, "Eolica", f"{gen_eolica:,.1f} MW",
        f"↑ FP {fp_eolica:.1f}%" if fp_eolica else None, AES_VERDE,
        f"5 parques sur · Pmax neta {PMAX_FP_TOTAL_EOLICA:,.0f} MW · FP=gen/Pmax neta · {hora_gen} hrs",
    ))

    dev_val   = f"{desvio_pct:+.1f}%" if desvio_pct is not None else "—"
    dev_mw    = f"{desvio['desvio_mw']:+.1f} MW" if desvio["desvio_mw"] is not None else None
    dev_color = _SEM_COLOR.get(semaforo, AES_MUTED)
    cards.append(_card(
        dev_color, "Desvio vs PCP", dev_val, dev_mw, dev_color,
        f"(real−PCP)/PCP · verde ≤15% ámbar ≤25% rojo &gt;25% · CEN PCP · {hora_gen} hrs",
    ))

    cards.append(_card(
        AES_VIOLETA, "CMG Promedio",
        f"{cmg_prom:.1f} USD/MWh" if cmg_prom else "—",
        f"~{ingreso_total:.0f} kUSD/h" if ingreso_total else None, AES_VIOLETA,
        f"Prom. {len(cmg_vals)} nodos SEN (excl. P.Montt) · ingreso=gen×CMG · CEN S3 · {cmg_hora} hrs",
    ))

    # ── BESS: estado agregado del almacenamiento ────────────────────────────
    bess_neta, bess_util, bess_estado, bess_hora, bess_col = _agregado_bess(bess_rows)
    cards.append(_card(
        AES_CYAN, "BESS — Almacenamiento",
        f"{bess_neta:+.0f} MW" if bess_neta is not None else "—",
        f"{bess_estado}" if bess_estado else None, bess_col,
        (f"6 BESS AES · uso {bess_util:.0f}% de Pmax descarga · "
         f"neta=inyección−retiro (>0 descarga) · {bess_hora} hrs")
        if bess_neta is not None else
        "6 BESS AES · sin telemetría reciente · neta=inyección−retiro",
    ))

    lim_color = AES_ROJO if n_limitaciones_activas > 0 else AES_VERDE
    lim_delta = "↑ activas" if n_limitaciones_activas > 0 else "sin restricciones"
    cards.append(_card(
        lim_color, "Limitaciones", str(n_limitaciones_activas),
        lim_delta, lim_color,
        "Restricciones de transmisión activas · CEN limitaciones-transmision/v4",
    ))

    st.markdown(_GRID_CSS + "<div class='kpi-grid'>" + "".join(cards) + "</div>",
                unsafe_allow_html=True)


def _agregado_bess(bess_rows: list | None):
    """Estado agregado del parque de BESS: potencia neta total, % de uso sobre la
    Pmax de descarga, estado (cargando/descargando/reposo), hora y color."""
    if not bess_rows:
        return None, None, None, "—", AES_MUTED
    import pandas as pd
    df = pd.DataFrame(bess_rows)
    if df.empty or "bess" not in df.columns:
        return None, None, None, "—", AES_MUTED
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    ult = df.sort_values("fecha_hora").drop_duplicates("bess", keep="last")
    neta = float(ult["potencia_neta_mw"].sum())
    pmax_total = sum(b["pmax_mw"] for b in BESS.values()) or 1.0
    util = abs(neta) / pmax_total * 100.0
    hora = ult["fecha_hora"].max().strftime("%H:%M")
    if neta > 1:
        return neta, util, "Descargando", hora, AES_VERDE
    if neta < -1:
        return neta, util, "Cargando", hora, AES_AZUL
    return neta, util, "En reposo", hora, AES_MUTED
