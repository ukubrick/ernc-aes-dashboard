"""Demanda programada PID por zona del SEN — serie de tiempo reutilizable.

Fuente: tabla demanda_ernc (endpoint /demanda-programada-pid/v4 del CEN). Muestra la
demanda proyectada por zona (Norte, Centro, Centro Sur, Sur) y el total del SEN. El
endpoint reprograma intra-día, por lo que la serie incluye horas futuras del programa.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from config import (
    DEMANDA_ZONAS, DEMANDA_ZONA_COLOR, TZ_CHILE,
)
from utils.db import query_demanda_ultimas_horas

AES_TEXTO  = "#1A1F36"
AES_MUTED  = "#6B7280"
AES_GRIS   = "#F5F7FA"
AES_BORDE  = "#E5E7EB"
AES_BLANCO = "#FFFFFF"


def render_demanda_zonas(horas: int = 48, key: str = "demanda") -> None:
    """Serie de tiempo apilada de la demanda programada PID por zona + total SEN."""
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:18px 0 6px'>"
        f"Demanda programada del SEN por zona (PID)</div>",
        unsafe_allow_html=True,
    )
    rows = query_demanda_ultimas_horas(horas)
    if not rows:
        st.info(
            "Sin datos de demanda todavia. Se poblara al correr Adquisicion_pid_ernc.py "
            "(o el cron del workflow PID). Requiere la tabla demanda_ernc en Supabase."
        )
        return

    df = pd.DataFrame(rows)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    df = df.sort_values("fecha_hora")

    fig = go.Figure()
    for zona in DEMANDA_ZONAS:
        dz = df[df["zona"] == zona]
        if dz.empty:
            continue
        color = DEMANDA_ZONA_COLOR.get(zona, AES_MUTED)
        rgba = _hex_a_rgba(color, 0.45)
        fig.add_trace(go.Scatter(
            x=dz["fecha_hora"], y=dz["demanda_mw"], name=zona, stackgroup="dem",
            line=dict(color=color, width=0.5), fillcolor=rgba,
            hovertemplate="%{y:,.0f} MW<extra>" + zona + "</extra>",
        ))

    # Línea "ahora" para separar pasado de proyectado intra-día
    ahora = datetime.now(TZ_CHILE).replace(tzinfo=None)
    if df["fecha_hora"].min() <= ahora <= df["fecha_hora"].max():
        fig.add_vline(x=ahora, line_dash="dash", line_color=AES_MUTED, line_width=1,
                      annotation_text="ahora", annotation_position="top",
                      annotation_font_size=9, annotation_font_color=AES_MUTED)

    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
        xaxis_title=None, yaxis_title="MW", height=320,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key=f"{key}_demanda_zonas")
    st.caption(
        "Demanda proyectada del SEN agregada por zona (programa PID intra-día). Las zonas "
        "Norte (parques solares) y Centro Sur (parques eólicos) contextualizan el consumo "
        "local frente a la generación del portfolio. El total apilado refleja la FORMA del "
        "consumo diario. Fuente: /demanda-programada-pid/v4 (API CEN SIP)."
    )


def _hex_a_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"
