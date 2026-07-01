"""Vista CMG (precios, programado, demanda) + limitaciones e instrucciones CEN.

Extraída de app_ernc.py (Sesión 34).
"""
import streamlit as st

from config import NOMBRE_DISPLAY, CMG_NODOS_TODOS
from utils.db import query_cmg_programado

AES_AZUL    = "#3B4CE8"
AES_AZUL_OSC = "#2530B0"
AES_CYAN    = "#4DC8DC"
AES_VIOLETA = "#9B6FD4"
AES_VERDE   = "#5AB848"
AES_ROJO    = "#EF4444"
AES_AMBAR   = "#F59E0B"
AES_GRIS    = "#F5F7FA"
AES_TEXTO   = "#1A1F36"
AES_MUTED   = "#6B7280"
AES_BORDE   = "#E5E7EB"
AES_BLANCO  = "#FFFFFF"


# ── Tab CMG ────────────────────────────────────────────────────────────────────

def _cmg_alertas(cmg_actual, df_hist):
    """Genera alertas de precio: costo cero/vertimiento, CMG muy alto, desacople entre nodos."""
    import pandas as pd
    alertas = []  # (prioridad, titulo, detalle)
    vals = {n: r["cmg_usd_mwh"] for n, r in cmg_actual.items() if r.get("cmg_usd_mwh") is not None}
    if vals:
        nodo_min = min(vals, key=vals.get); v_min = vals[nodo_min]
        nodo_max = max(vals, key=vals.get); v_max = vals[nodo_max]
        if v_min <= 0.5:
            alertas.append(("alta", "CMG en costo cero — vertimiento",
                            f"{nodo_min.replace('_',' ').strip()} en {v_min:.1f} USD/MWh: energia sin valor, riesgo de curtailment forzado."))
        if v_max >= 200:
            alertas.append(("alta", "CMG muy alto — oportunidad de ingreso",
                            f"{nodo_max.replace('_',' ').strip()} en {v_max:.1f} USD/MWh: ingreso por MWh excepcional."))
        spread = v_max - v_min
        if spread > 50:
            alertas.append(("media", "Desacople de nodos (congestion)",
                            f"Spread {spread:.0f} USD/MWh entre {nodo_max.replace('_',' ').strip()} y {nodo_min.replace('_',' ').strip()}: sistema congestionado."))
    # Máximo histórico de la ventana
    if df_hist is not None and not df_hist.empty:
        fila_max = df_hist.loc[df_hist["cmg_usd_mwh"].idxmax()]
        if vals and fila_max["cmg_usd_mwh"] >= max(vals.values()) and fila_max["cmg_usd_mwh"] >= 150:
            alertas.append(("media", "Maximo de la ventana ahora mismo",
                            f"{fila_max['nodo'].replace('_',' ').strip()} marca el maximo de 48h: {fila_max['cmg_usd_mwh']:.1f} USD/MWh."))
    return alertas


def render_tab_cmg(cmg_rows):
    import plotly.graph_objects as go
    import pandas as pd
    from utils.db import get_client
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:10px'>"
        f"Costo Marginal Local — todos los nodos disponibles</div>",
        unsafe_allow_html=True,
    )

    if not cmg_rows:
        st.warning("Sin datos de CMG disponibles.")
        return

    cmg_actual = {r["nodo"]: r for r in cmg_rows}

    # Histórico 48h (hora Santiago, no UTC) — se usa para serie, máximos y alertas
    df_hist = pd.DataFrame()
    try:
        sb = get_client()
        santiago = ZoneInfo("America/Santiago")
        desde = (datetime.now(santiago) - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
        res = (
            sb.table("cmg_ernc")
            .select("nodo,cmg_usd_mwh,fecha_hora")
            .in_("nodo", CMG_NODOS_TODOS)
            .gte("fecha_hora", desde)
            .order("fecha_hora")
            .execute()
        )
        if res.data:
            df_hist = pd.DataFrame(res.data)
            df_hist["fecha_hora"] = pd.to_datetime(df_hist["fecha_hora"])
    except Exception as e:
        st.warning(f"No se pudo cargar historico CMG: {e}")

    # ── Alertas de precio ──
    alertas = _cmg_alertas(cmg_actual, df_hist)
    if alertas:
        _bg = {"alta": "#FEF2F2", "media": "#FFFBEB"}
        _bd = {"alta": AES_ROJO, "media": "#F59E0B"}
        _lb = {"alta": "ALERTA", "media": "ATENCION"}
        for sev, titulo, detalle in alertas:
            st.markdown(
                f"<div style='background:{_bg[sev]};border-left:4px solid {_bd[sev]};"
                f"border-radius:0 8px 8px 0;padding:9px 16px;margin-bottom:7px'>"
                f"<span style='font-size:9px;font-weight:700;color:{_bd[sev]};letter-spacing:1px;"
                f"background:{_bd[sev]}22;padding:2px 8px;border-radius:20px'>{_lb[sev]}</span> "
                f"<span style='font-size:13px;font-weight:600;color:{AES_TEXTO}'>{titulo}</span>"
                f"<div style='font-size:12px;color:{AES_MUTED};margin-top:2px'>{detalle}</div></div>",
                unsafe_allow_html=True,
            )

    # ── Serie de tiempo PRIMERO ──
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:10px 0 6px'>"
        f"Historico 48 horas — todos los nodos</div>",
        unsafe_allow_html=True,
    )
    if not df_hist.empty:
        paleta = [AES_AZUL, AES_CYAN, AES_VIOLETA, AES_VERDE,
                  "#F59E0B", "#EF4444", "#6366F1", "#EC4899"]
        nodos_presentes = df_hist["nodo"].unique().tolist()
        fig = go.Figure()
        for i, nodo in enumerate(nodos_presentes):
            df_n = df_hist[df_hist["nodo"] == nodo].sort_values("fecha_hora")
            fig.add_trace(go.Scatter(
                x=df_n["fecha_hora"], y=df_n["cmg_usd_mwh"],
                name=nodo.replace("_", " ").strip(),
                line=dict(color=paleta[i % len(paleta)], width=1.6, dash="dot"),
                hovertemplate="%{y:.1f} USD/MWh<extra>" + nodo + "</extra>",
            ))
        fig.add_hline(y=0, line_dash="dot", line_color=AES_ROJO, line_width=1,
                      annotation_text="Costo cero", annotation_position="bottom right",
                      annotation_font_size=9, annotation_font_color=AES_ROJO)
        fig.update_layout(
            template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
            xaxis_title=None, yaxis_title="USD/MWh", height=380,
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
            hovermode="x unified",
        )
        fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
        fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
        st.plotly_chart(fig, use_container_width=True, key="cmg_grafico_historico")
    else:
        st.info("Sin historico CMG en las ultimas 48 horas.")

    # ── Tabla con métricas DESPUÉS (incluye máximo de la ventana) ──
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:14px 0 6px'>"
        f"Detalle por nodo — valor actual y maximo 48h</div>",
        unsafe_allow_html=True,
    )
    max_por_nodo = (
        df_hist.groupby("nodo")["cmg_usd_mwh"].max().to_dict() if not df_hist.empty else {}
    )
    min_por_nodo = (
        df_hist.groupby("nodo")["cmg_usd_mwh"].min().to_dict() if not df_hist.empty else {}
    )
    filas_tabla = []
    for nodo in CMG_NODOS_TODOS:
        r = cmg_actual.get(nodo)
        filas_tabla.append({
            "Nodo": nodo.replace("_", " ").strip(),
            "CMG actual": f"{r['cmg_usd_mwh']:.1f}" if r else "—",
            "Max 48h": f"{max_por_nodo[nodo]:.1f}" if nodo in max_por_nodo else "—",
            "Min 48h": f"{min_por_nodo[nodo]:.1f}" if nodo in min_por_nodo else "—",
            "Hora": r["fecha_hora"][11:16] if r else "—",
        })
    st.dataframe(pd.DataFrame(filas_tabla), hide_index=True, use_container_width=True)
    st.caption(
        "CMG = costo marginal del sistema por nodo (USD/MWh). Los nodos convergen cuando "
        "no hay congestion y se desacoplan cuando la red se satura. Alertas: costo cero "
        "(<0.5, vertimiento), CMG alto (>200, oportunidad de ingreso) y desacople "
        "(spread >50 entre nodos). Fuente: JSON S3 del Coordinador, actualiza cada ~15 min."
    )

    # ── Ranking de CMG actual por nodo (barras horizontales) ──
    vals = [(n.replace("_", " ").strip(), cmg_actual[n].get("cmg_usd_mwh"))
            for n in CMG_NODOS_TODOS
            if cmg_actual.get(n) and cmg_actual[n].get("cmg_usd_mwh") is not None]
    if vals:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:18px 0 6px'>"
            f"Ranking de CMG actual por nodo</div>",
            unsafe_allow_html=True,
        )
        vals.sort(key=lambda x: x[1])
        fig_rank = go.Figure(go.Bar(
            x=[v[1] for v in vals], y=[v[0] for v in vals], orientation="h",
            marker_color=[AES_ROJO if v[1] < 5 else (AES_VERDE if v[1] > 100 else AES_AZUL) for v in vals],
            text=[f"{v[1]:.0f}" for v in vals], textposition="outside",
            hovertemplate="%{y}: %{x:.1f} USD/MWh<extra></extra>",
        ))
        fig_rank.update_layout(
            template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
            height=300, margin=dict(l=0, r=40, t=6, b=0),
            xaxis_title="USD/MWh", showlegend=False,
        )
        fig_rank.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
        st.plotly_chart(fig_rank, use_container_width=True, key="cmg_ranking_barras")

    # ── CMG programado (futuro proyectado por el Coordinador) ──
    prog_rows = query_cmg_programado(72)
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:18px 0 6px'>"
        f"CMG programado PCP — proyeccion del Coordinador por nodo</div>",
        unsafe_allow_html=True,
    )
    if prog_rows:
        df_prog = pd.DataFrame(prog_rows)
        df_prog["fecha_hora"] = pd.to_datetime(df_prog["fecha_hora"])
        paleta_p = [AES_AZUL, AES_CYAN, AES_VIOLETA, AES_VERDE,
                    "#F59E0B", "#EF4444", "#6366F1", "#EC4899"]
        nodos_p = df_prog["nodo"].unique().tolist()
        figp = go.Figure()
        for i, nodo in enumerate(nodos_p):
            df_n = df_prog[df_prog["nodo"] == nodo].sort_values("fecha_hora")
            figp.add_trace(go.Scatter(
                x=df_n["fecha_hora"], y=df_n["cmg_usd_mwh"],
                name=nodo.replace("_", " ").strip(),
                line=dict(color=paleta_p[i % len(paleta_p)], width=1.6, dash="dot"),
                hovertemplate="%{y:.1f} USD/MWh<extra>" + nodo + "</extra>",
            ))
        # Marca el "ahora" para separar visualmente pasado vs futuro proyectado
        _ahora = datetime.now(santiago).replace(tzinfo=None)
        figp.add_vline(x=_ahora, line_dash="dash", line_color=AES_MUTED, line_width=1,
                       annotation_text="ahora", annotation_position="top",
                       annotation_font_size=9, annotation_font_color=AES_MUTED)
        figp.update_layout(
            template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
            xaxis_title=None, yaxis_title="USD/MWh", height=360,
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
            hovermode="x unified",
        )
        figp.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
        figp.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
        st.plotly_chart(figp, use_container_width=True, key="cmg_grafico_programado")
        st.caption(
            "CMG programado PCP: proyeccion horaria del costo marginal que publica el "
            "Coordinador (programa del dia). Util para anticipar ingresos y arbitraje BESS. "
            "Fuente: /cmg-programado-pcp/v4 (API CEN SIP)."
        )
    else:
        st.info(
            "Sin CMG programado todavia. Se poblara al correr Adquisicion_ernc.py "
            "(o el cron horario) con el endpoint cmg-programado-pcp."
        )

    # ── Demanda del SEN por zona (contexto de mercado) ──
    from components.demanda import render_demanda_zonas, render_demanda_pronostico
    render_demanda_zonas(horas=48, key="cmg")
    render_demanda_pronostico(key="cmg")


# ── Tab Limitaciones ──────────────────────────────────────────────────────────

def render_tab_limitaciones(lim_rows):
    import pandas as pd

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:12px'>"
        f"Limitaciones de transmision — activas y ultimos 30 dias</div>",
        unsafe_allow_html=True,
    )

    if not lim_rows:
        st.success("Sin limitaciones de transmision en los ultimos 30 dias.")
        return

    df = pd.DataFrame(lim_rows)

    # Separar activas (sin retorno) vs históricas (con retorno)
    activas   = df[df["fecha_efectiva_retorno"].isna()] if "fecha_efectiva_retorno" in df.columns else df
    historicas = df[df["fecha_efectiva_retorno"].notna()] if "fecha_efectiva_retorno" in df.columns else pd.DataFrame()

    n_activas = len(activas)
    if n_activas > 0:
        st.markdown(
            f"<div style='background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;"
            f"padding:10px 16px;margin-bottom:12px;font-size:13px;color:#991B1B'>"
            f"<b>{n_activas} limitacion(es) activa(s) — sin fecha de retorno confirmada</b></div>",
            unsafe_allow_html=True,
        )
    else:
        st.success("Sin limitaciones activas en este momento.")

    def _tabla_lim(df_lim: pd.DataFrame, titulo: str) -> None:
        if df_lim.empty:
            return
        st.markdown(
            f"<div style='font-size:12px;font-weight:600;color:{AES_TEXTO};margin:10px 0 6px'>{titulo}</div>",
            unsafe_allow_html=True,
        )
        cols_show = [c for c in [
            "parque", "instalacion_nombre", "potencia", "unidad_medida_potencia",
            "status", "fecha_perturbacion", "fecha_efectiva_retorno", "observacion",
        ] if c in df_lim.columns]
        df_show = df_lim[cols_show].copy()
        df_show.rename(columns={
            "parque": "Parque", "instalacion_nombre": "Instalacion",
            "potencia": "Potencia", "unidad_medida_potencia": "Unidad",
            "status": "Estado", "fecha_perturbacion": "Inicio",
            "fecha_efectiva_retorno": "Retorno", "observacion": "Observacion",
        }, inplace=True)
        if "Parque" in df_show.columns:
            df_show["Parque"] = df_show["Parque"].map(NOMBRE_DISPLAY).fillna(df_show["Parque"])
        st.dataframe(df_show, hide_index=True, use_container_width=True)

    _tabla_lim(activas, "Limitaciones activas")
    _tabla_lim(historicas, f"Historico ultimos 30 dias ({len(historicas)} registros)")

    _render_instrucciones()


def _render_instrucciones():
    """Instrucciones operacionales del CEN a los parques/BESS (curtailment ordenado)."""
    import pandas as pd
    from utils.db import query_instrucciones_ultimas

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:18px 0 6px'>"
        f"Instrucciones operacionales del CEN — ultimas 72 h</div>",
        unsafe_allow_html=True,
    )
    rows = query_instrucciones_ultimas(horas=72)
    if not rows:
        st.caption(
            "Sin instrucciones registradas para el portfolio en la ventana (o tabla "
            "instrucciones_ernc aun no creada en Supabase — ver bloque Sesion 34 de schema.sql)."
        )
        return

    df = pd.DataFrame(rows)
    df["Parque"] = df["parque"].map(NOMBRE_DISPLAY).fillna(df["parque"])
    cols = ["Parque", "fecha_hora", "despacho_mw", "consigna", "instruccion_cmg", "motivo"]
    df_show = df[[c for c in cols if c in df.columns]].rename(columns={
        "fecha_hora": "Fecha/hora", "despacho_mw": "Despacho (MW)",
        "consigna": "Consigna", "instruccion_cmg": "Instruccion", "motivo": "Motivo",
    })
    st.dataframe(df_show, hide_index=True, use_container_width=True, height=280)
    st.caption(
        "Instrucciones dadas por el CEN a los centros de control (fuente: "
        "instrucciones-operacionales-cmg). Una consigna CI/LIM con despacho bajo la "
        "capacidad disponible indica curtailment ordenado — distinto de una falla o soiling."
    )


