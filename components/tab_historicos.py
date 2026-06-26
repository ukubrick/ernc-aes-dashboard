"""
Sección Históricos — visualización de cualquier evento del pasado dentro de todo el
rango disponible en la base (~desde 2026-03-01, backfill de gen real/BESS/meteo).

A diferencia de los tabs operativos (ventana móvil de 168 h), esta vista consulta la
DB por rango de fechas explícito y paginado (.range()), por lo que puede llegar a
meses atrás sin truncarse. Temas: Generación (real vs PCP/PID), Meteo, CMG, BESS.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta

from config import (
    NOMBRE_DISPLAY, TECNOLOGIA, PARQUES_SOLAR, PARQUES_EOLICA, PARQUES_TODOS,
    CMG_NODOS_TODOS, BESS,
)
from utils.db import (
    query_gen_real_rango, query_gen_prog_rango, query_bess_rango,
    query_cmg_rango, query_meteo_rango, query_fecha_min_gen_real,
)

AES_AZUL    = "#3B4CE8"
AES_CYAN    = "#4DC8DC"
AES_VIOLETA = "#9B6FD4"
AES_VERDE   = "#5AB848"
AES_ROJO    = "#EF4444"
AES_AMBAR   = "#F59E0B"
AES_GRIS    = "#F5F7FA"
AES_BORDE   = "#E5E7EB"
AES_BLANCO  = "#FFFFFF"
AES_TEXTO   = "#1A1F36"
AES_MUTED   = "#6B7280"

_FMT = "%Y-%m-%d %H:%M:%S"


@st.cache_data(ttl=300)
def _fecha_min() -> date:
    fm = query_fecha_min_gen_real()
    if fm:
        try:
            return pd.to_datetime(fm).date()
        except Exception:
            pass
    return date(2026, 3, 1)


def _layout(fig, height=380, ytitle="MW"):
    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
        height=height, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None, yaxis_title=ytitle,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)


# ── Temas ──────────────────────────────────────────────────────────────────────

def _hist_generacion(desde: str, hasta: str):
    modo = st.radio("Alcance", ["Por parque", "Portfolio (apilado)"],
                    horizontal=True, key="hist_gen_modo", label_visibility="collapsed")
    gen = pd.DataFrame(query_gen_real_rango(desde, hasta))
    prog = pd.DataFrame(query_gen_prog_rango(desde, hasta))
    if gen.empty:
        st.info("Sin generación real en el rango elegido.")
        return
    gen["fecha_hora"] = pd.to_datetime(gen["fecha_hora"])
    gen = gen[gen["gen_real_mw"] >= 0]
    if not prog.empty:
        prog["fecha_hora"] = pd.to_datetime(prog["fecha_hora"])
        if "fuente" not in prog.columns:
            prog["fuente"] = "CEN_PCP"

    if modo == "Por parque":
        p = st.selectbox("Parque", PARQUES_TODOS, format_func=lambda x: NOMBRE_DISPLAY[x],
                         key="hist_gen_parque")
        g = gen[gen["parque"] == p].sort_values("fecha_hora")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=g["fecha_hora"], y=g["gen_real_mw"], name="Generación real",
            line=dict(color=AES_AZUL, width=2), fill="tozeroy",
            fillcolor="rgba(59,76,232,0.06)",
            hovertemplate="%{y:.1f} MW<extra>Gen. real</extra>"))
        if not prog.empty:
            pp = prog[prog["parque"] == p]
            pcp = pp[pp["fuente"] == "CEN_PCP"].sort_values("fecha_hora")
            pid = pp[pp["fuente"] == "CEN_PID"].sort_values("fecha_hora")
            if not pcp.empty:
                fig.add_trace(go.Scatter(
                    x=pcp["fecha_hora"], y=pcp["gen_programada_mw"], name="PCP programada",
                    line=dict(color=AES_AMBAR, width=1.8, dash="dash"),
                    hovertemplate="%{y:.1f} MW<extra>PCP</extra>"))
            if not pid.empty:
                fig.add_trace(go.Scatter(
                    x=pid["fecha_hora"], y=pid["gen_programada_mw"], name="PID intra-día",
                    line=dict(color=AES_VERDE, width=1.6, dash="dot"),
                    hovertemplate="%{y:.1f} MW<extra>PID</extra>"))
        _layout(fig)
        st.plotly_chart(fig, use_container_width=True, key="hist_gen_parque_fig")
        _resumen_gen(g)
    else:
        gen["tec"] = gen["parque"].map(TECNOLOGIA)
        piv = (gen.pivot_table(index="fecha_hora", columns="tec", values="gen_real_mw",
                               aggfunc="sum").reset_index())
        for c in ("Solar", "Eólica"):
            if c not in piv.columns:
                piv[c] = 0.0
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=piv["fecha_hora"], y=piv["Solar"], name="Solar FV",
                                 stackgroup="g", line=dict(color=AES_AZUL, width=0.5),
                                 fillcolor="rgba(59,76,232,0.55)"))
        fig.add_trace(go.Scatter(x=piv["fecha_hora"], y=piv["Eólica"], name="Eólica",
                                 stackgroup="g", line=dict(color=AES_CYAN, width=0.5),
                                 fillcolor="rgba(77,200,220,0.55)"))
        _layout(fig)
        st.plotly_chart(fig, use_container_width=True, key="hist_gen_portfolio_fig")
        tot_mwh = (piv["Solar"].fillna(0) + piv["Eólica"].fillna(0)).sum()
        st.caption(f"Energía total del portfolio en el rango: {tot_mwh:,.0f} MWh "
                   f"(Solar {piv['Solar'].sum():,.0f} + Eólica {piv['Eólica'].sum():,.0f}).")


def _resumen_gen(g: pd.DataFrame):
    c = st.columns(4)
    c[0].metric("Energía", f"{g['gen_real_mw'].sum():,.0f} MWh")
    c[1].metric("Pico", f"{g['gen_real_mw'].max():,.1f} MW")
    c[2].metric("Promedio", f"{g['gen_real_mw'].mean():,.1f} MW")
    c[3].metric("Horas con dato", f"{len(g):,}")


def _hist_meteo(desde: str, hasta: str):
    p = st.selectbox("Parque", PARQUES_TODOS, format_func=lambda x: NOMBRE_DISPLAY[x],
                     key="hist_meteo_parque")
    df = pd.DataFrame(query_meteo_rango(p, desde, hasta))
    if df.empty:
        st.info("Sin meteo histórica en el rango/parque elegido.")
        return
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    df = df.sort_values("fecha_hora")
    fig = go.Figure()
    if TECNOLOGIA[p] == "Solar":
        fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df.get("ghi_wm2"), name="GHI",
                                 line=dict(color=AES_AMBAR, width=1.6), fill="tozeroy",
                                 fillcolor="rgba(245,158,11,0.08)",
                                 hovertemplate="%{y:.0f} W/m²<extra>GHI</extra>"))
        if "p_fv_estimada_mw" in df:
            fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df["p_fv_estimada_mw"],
                                     name="Modelo FV", yaxis="y2",
                                     line=dict(color=AES_VIOLETA, width=1.4),
                                     hovertemplate="%{y:.1f} MW<extra>Modelo FV</extra>"))
        fig.update_layout(yaxis2=dict(title="MW", overlaying="y", side="right", showgrid=False))
        _layout(fig, ytitle="W/m²")
    else:
        fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df.get("wind_speed_100m"),
                                 name="Viento 100m", line=dict(color=AES_CYAN, width=1.8),
                                 hovertemplate="%{y:.1f} m/s<extra>Viento hub</extra>"))
        if "wind_gusts_10m" in df:
            fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df["wind_gusts_10m"],
                                     name="Ráfagas 10m", line=dict(color=AES_ROJO, width=1, dash="dot"),
                                     hovertemplate="%{y:.1f} m/s<extra>Ráfagas</extra>"))
        if "p_eolica_estimada_mw" in df:
            fig.add_trace(go.Scatter(x=df["fecha_hora"], y=df["p_eolica_estimada_mw"],
                                     name="Modelo eólico", yaxis="y2",
                                     line=dict(color=AES_VIOLETA, width=1.4),
                                     hovertemplate="%{y:.1f} MW<extra>Modelo eólico</extra>"))
        fig.update_layout(yaxis2=dict(title="MW", overlaying="y", side="right", showgrid=False))
        _layout(fig, ytitle="m/s")
    st.plotly_chart(fig, use_container_width=True, key="hist_meteo_fig")


def _hist_cmg(desde: str, hasta: str):
    df = pd.DataFrame(query_cmg_rango(desde, hasta))
    if df.empty:
        st.info("Sin CMG histórico en el rango elegido.")
        return
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    nodos = sorted(df["nodo"].unique())
    sel = st.multiselect("Nodos", nodos, default=nodos[:3], key="hist_cmg_nodos")
    fig = go.Figure()
    for n in sel:
        d = df[df["nodo"] == n].sort_values("fecha_hora")
        fig.add_trace(go.Scatter(x=d["fecha_hora"], y=d["cmg_usd_mwh"], name=n,
                                 line=dict(width=1.5),
                                 hovertemplate="%{y:.1f} USD/MWh<extra>"+n+"</extra>"))
    _layout(fig, ytitle="USD/MWh")
    st.plotly_chart(fig, use_container_width=True, key="hist_cmg_fig")


def _hist_bess(desde: str, hasta: str):
    df = pd.DataFrame(query_bess_rango(desde, hasta))
    if df.empty:
        st.info("Sin datos de BESS en el rango elegido.")
        return
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    cods = sorted(df["bess"].unique())
    sel = st.selectbox("BESS", cods,
                       format_func=lambda c: BESS.get(c, {}).get("nombre", c) if isinstance(BESS.get(c), dict) else c,
                       key="hist_bess_sel")
    d = df[df["bess"] == sel].sort_values("fecha_hora")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["fecha_hora"], y=d["potencia_neta_mw"], name="Potencia neta",
                             line=dict(color=AES_VIOLETA, width=1.6), fill="tozeroy",
                             fillcolor="rgba(155,111,212,0.10)",
                             hovertemplate="%{y:.1f} MW<extra>+ descarga / − carga</extra>"))
    _layout(fig)
    st.plotly_chart(fig, use_container_width=True, key="hist_bess_fig")
    desc = d[d["potencia_neta_mw"] > 0]["potencia_neta_mw"].sum()
    carga = -d[d["potencia_neta_mw"] < 0]["potencia_neta_mw"].sum()
    c = st.columns(3)
    c[0].metric("Descarga total", f"{desc:,.0f} MWh")
    c[1].metric("Carga total", f"{carga:,.0f} MWh")
    c[2].metric("Energía neta", f"{d['potencia_neta_mw'].sum():,.0f} MWh")


# ── Render principal ─────────────────────────────────────────────────────────────

def render_tab_historicos():
    st.markdown(
        f"<div style='font-size:14px;font-weight:700;color:{AES_TEXTO};margin-bottom:2px'>"
        f"Históricos</div>"
        f"<div style='font-size:11.5px;color:{AES_MUTED};margin-bottom:12px'>"
        f"Visualiza cualquier evento del pasado dentro de todo el rango disponible en la "
        f"base. Elige el rango de fechas y el tema.</div>",
        unsafe_allow_html=True,
    )

    fmin = _fecha_min()
    hoy = date.today()
    c1, c2, c3 = st.columns([1.4, 1, 1])
    with c1:
        tema = st.selectbox("Tema", ["Generación", "Meteorología", "CMG", "BESS"],
                            key="hist_tema")
    with c2:
        ini = st.date_input("Desde", value=max(fmin, hoy - timedelta(days=7)),
                            min_value=fmin, max_value=hoy, key="hist_desde")
    with c3:
        fin = st.date_input("Hasta", value=hoy, min_value=fmin, max_value=hoy, key="hist_hasta")

    if isinstance(ini, tuple):
        ini = ini[0]
    if ini > fin:
        st.warning("La fecha 'Desde' es posterior a 'Hasta'. Ajusta el rango.")
        return

    desde = f"{ini} 00:00:00"
    hasta = f"{fin} 23:59:59"
    st.caption(f"Rango: {ini} → {fin}  ·  datos disponibles desde {fmin}.")

    if tema == "Generación":
        _hist_generacion(desde, hasta)
    elif tema == "Meteorología":
        _hist_meteo(desde, hasta)
    elif tema == "CMG":
        _hist_cmg(desde, hasta)
    elif tema == "BESS":
        _hist_bess(desde, hasta)
