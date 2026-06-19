"""Tab Forecast — tema claro, paleta AES, sin emojis, mensaje claro si no hay datos."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone

from config import NOMBRE_DISPLAY, PMAX, TECNOLOGIA, PARQUES_SOLAR, PARQUES_EOLICA, PARQUES_TODOS

AES_AZUL    = "#3B4CE8"
AES_CYAN    = "#4DC8DC"
AES_VIOLETA = "#9B6FD4"
AES_VERDE   = "#5AB848"
AES_AMBAR   = "#F59E0B"
AES_GRIS    = "#F5F7FA"
AES_BORDE   = "#E5E7EB"
AES_BLANCO  = "#FFFFFF"
AES_TEXTO   = "#1A1F36"
AES_MUTED   = "#6B7280"


@st.cache_data(ttl=1800)
def _cargar_forecast() -> pd.DataFrame:
    try:
        from utils.db import get_client
        sb = get_client()
        santiago = timezone(timedelta(hours=-3))
        ahora = datetime.now(santiago).strftime("%Y-%m-%d %H:%M:%S")
        hasta = (datetime.now(santiago) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        res = (
            sb.table("meteo_ernc")
            .select(
                "parque,fecha_hora,p_fv_estimada_mw,p_eolica_estimada_mw,"
                "ghi_wm2,wind_speed_100m,cloud_cover_pct,wind_gusts_10m,es_forecast"
            )
            .eq("es_forecast", True)
            .gte("fecha_hora", ahora)
            .lte("fecha_hora", hasta)
            .order("fecha_hora")
            .execute()
        )
        if res.data:
            df = pd.DataFrame(res.data)
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
            df["tecnologia"] = df["parque"].map(TECNOLOGIA)
            return df
    except Exception as e:
        st.warning(f"Error cargando forecast: {e}")
    return pd.DataFrame()


@st.cache_data(ttl=1800)
def _cargar_pcp_forecast() -> pd.DataFrame:
    """Carga PCP (gen programada) desde ahora hasta fin del día siguiente."""
    try:
        from utils.db import get_client
        sb = get_client()
        santiago = timezone(timedelta(hours=-3))
        ahora = datetime.now(santiago).strftime("%Y-%m-%d %H:%M:%S")
        # Hasta las 23:59 del día siguiente
        manana = (datetime.now(santiago) + timedelta(days=2)).strftime("%Y-%m-%d 00:00:00")
        res = (
            sb.table("generacion_programada_ernc")
            .select("parque,fecha_hora,gen_programada_mw")
            .gte("fecha_hora", ahora)
            .lte("fecha_hora", manana)
            .order("fecha_hora")
            .execute()
        )
        if res.data:
            df = pd.DataFrame(res.data)
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
            return df
    except Exception:
        pass
    return pd.DataFrame()


def _tabla_diaria(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["fecha"] = df["fecha_hora"].dt.date
    df["p_solar"]  = df.apply(lambda r: r["p_fv_estimada_mw"]     if r["tecnologia"] == "Solar"  else 0, axis=1)
    df["p_eolica"] = df.apply(lambda r: r["p_eolica_estimada_mw"] if r["tecnologia"] == "Eólica" else 0, axis=1)
    agg = df.groupby("fecha").agg(solar_mwh=("p_solar", "sum"), eolica_mwh=("p_eolica", "sum")).reset_index()
    agg["total_mwh"] = agg["solar_mwh"] + agg["eolica_mwh"]
    agg["fecha"] = pd.to_datetime(agg["fecha"]).dt.strftime("%a %d/%m")
    agg.rename(columns={"fecha": "Dia", "solar_mwh": "Solar FV (MWh)", "eolica_mwh": "Eolica (MWh)", "total_mwh": "Total (MWh)"}, inplace=True)
    for col in ["Solar FV (MWh)", "Eolica (MWh)", "Total (MWh)"]:
        agg[col] = agg[col].round(0).astype(int)
    return agg


def _grafico_portfolio(df: pd.DataFrame, df_pcp: pd.DataFrame) -> None:
    df_solar  = df[df["tecnologia"] == "Solar"].groupby("fecha_hora")["p_fv_estimada_mw"].sum().reset_index()
    df_eolica = df[df["tecnologia"] == "Eólica"].groupby("fecha_hora")["p_eolica_estimada_mw"].sum().reset_index()
    df_solar.columns  = ["fecha_hora", "mw"]
    df_eolica.columns = ["fecha_hora", "mw"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_eolica["fecha_hora"], y=df_eolica["mw"],
        name="Eolica estimada", fill="tozeroy",
        line=dict(color=AES_CYAN, width=1.5),
        fillcolor="rgba(77,200,220,0.20)",
        hovertemplate="%{y:.0f} MW<extra>Eolica estimada</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df_solar["fecha_hora"], y=df_solar["mw"],
        name="Solar FV estimada", fill="tozeroy",
        line=dict(color=AES_AZUL, width=1.5),
        fillcolor="rgba(59,76,232,0.18)",
        hovertemplate="%{y:.0f} MW<extra>Solar FV estimada</extra>",
    ))
    # PCP total (todos los parques sumados)
    if not df_pcp.empty:
        df_pcp_tot = df_pcp.groupby("fecha_hora")["gen_programada_mw"].sum().reset_index()
        fig.add_trace(go.Scatter(
            x=df_pcp_tot["fecha_hora"], y=df_pcp_tot["gen_programada_mw"],
            name="PCP programada", line=dict(color=AES_AMBAR, width=2, dash="dash"),
            hovertemplate="%{y:.0f} MW<extra>PCP programada CEN</extra>",
        ))
    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS, transition=dict(duration=500, easing="cubic-in-out"),
        height=320, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None, yaxis_title="MW",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key="forecast_grafico_portfolio")


def _grafico_parque(df: pd.DataFrame, parque: str, df_pcp: pd.DataFrame) -> None:
    tec  = TECNOLOGIA[parque]
    df_p = df[df["parque"] == parque].sort_values("fecha_hora")
    if df_p.empty:
        st.info("Sin datos forecast para este parque.")
        return

    y_col   = "p_fv_estimada_mw"     if tec == "Solar"  else "p_eolica_estimada_mw"
    y2_col  = "ghi_wm2"              if tec == "Solar"  else "wind_speed_100m"
    y2_lbl  = "GHI (W/m²)"          if tec == "Solar"  else "Viento 100m (m/s)"
    color   = AES_AZUL               if tec == "Solar"  else AES_CYAN
    fill_c  = "rgba(59,76,232,0.10)" if tec == "Solar"  else "rgba(77,200,220,0.12)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_p["fecha_hora"], y=df_p[y_col],
        name="Potencia estimada",
        fill="tozeroy", fillcolor=fill_c,
        line=dict(color=color, width=2),
        hovertemplate="%{y:.1f} MW<extra>Estimado modelo</extra>",
    ))
    # PCP por parque si disponible
    if not df_pcp.empty:
        df_pcp_p = df_pcp[df_pcp["parque"] == parque].sort_values("fecha_hora")
        if not df_pcp_p.empty:
            fig.add_trace(go.Scatter(
                x=df_pcp_p["fecha_hora"], y=df_pcp_p["gen_programada_mw"],
                name="PCP programada",
                line=dict(color=AES_AMBAR, width=1.5, dash="dash"),
                hovertemplate="%{y:.1f} MW<extra>PCP programada CEN</extra>",
            ))
    if y2_col in df_p.columns:
        fig.add_trace(go.Scatter(
            x=df_p["fecha_hora"], y=df_p[y2_col],
            name=y2_lbl, yaxis="y2",
            line=dict(color=AES_MUTED, width=1, dash="dot"),
            hovertemplate=f"%{{y:.1f}}<extra>{y2_lbl}</extra>",
        ))
    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS, transition=dict(duration=500, easing="cubic-in-out"),
        height=260, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None, yaxis_title="MW",
        yaxis2=dict(overlaying="y", side="right", showgrid=False, title=y2_lbl),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key=f"forecast_grafico_parque_{parque}")


def render_tab_forecast() -> None:
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:12px'>"
        f"Forecast de produccion — proximos 7 dias</div>",
        unsafe_allow_html=True,
    )

    df = _cargar_forecast()
    df_pcp = _cargar_pcp_forecast()

    if df.empty:
        st.markdown(
            f"<div style='background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;"
            f"padding:16px 20px;color:#92400E'>"
            f"<div style='font-weight:600;font-size:13px;margin-bottom:6px'>"
            f"Sin datos de forecast disponibles</div>"
            f"<div style='font-size:12px;line-height:1.6'>"
            f"La tabla <code>meteo_ernc</code> no contiene registros futuros (es_forecast=True).<br>"
            f"Para poblarla, ejecuta localmente:<br>"
            f"<code style='background:#FEF3C7;padding:2px 6px;border-radius:3px'>"
            f"python Adquisicion_meteo_ernc.py</code><br>"
            f"o espera al proximo cron de GitHub Actions (cada hora, minuto :20)."
            f"</div></div>",
            unsafe_allow_html=True,
        )
        return

    # KPIs 7 dias
    solar_tot  = df[df["tecnologia"] == "Solar"]["p_fv_estimada_mw"].sum()
    eolica_tot = df[df["tecnologia"] == "Eólica"]["p_eolica_estimada_mw"].sum()
    total_mwh  = solar_tot + eolica_tot

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "Solar FV — 7 dias",
            f"{solar_tot:,.0f} MWh",
            help="Suma de p_fv_estimada_mw (1 fila = 1 hora = 1 MWh) para todos los parques solares. Modelo: P=Ppico x GTI/1000 x [1+γ(Tc-25)]. Fuente: Open-Meteo forecast.",
        )
    with c2:
        st.metric(
            "Eolica — 7 dias",
            f"{eolica_tot:,.0f} MWh",
            help="Suma de p_eolica_estimada_mw. Modelo: P=0.5 x ρ x A x Cp x v³, cap a Pmax. Fuente: Open-Meteo forecast viento 80m+120m interpolado a 100m.",
        )
    with c3:
        st.metric(
            "Total portfolio",
            f"{total_mwh:,.0f} MWh",
            help="Solar + Eolica estimados para los proximos 7 dias segun modelo meteorologico Open-Meteo.",
        )

    st.divider()
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
        f"Potencia estimada portfolio — hora a hora</div>",
        unsafe_allow_html=True,
    )
    _grafico_portfolio(df, df_pcp)

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:16px 0 8px'>"
        f"Produccion estimada por dia</div>",
        unsafe_allow_html=True,
    )
    df_dia = _tabla_diaria(df)
    if not df_dia.empty:
        st.dataframe(df_dia, hide_index=True, use_container_width=True)

    st.divider()
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
        f"Detalle por parque</div>",
        unsafe_allow_html=True,
    )

    col_tipo, col_parque = st.columns([1, 2])
    with col_tipo:
        tipo_sel = st.radio("Tecnologia", ["Solar FV", "Eolica"], horizontal=True, key="fcst_tipo")
    parques_disp = PARQUES_SOLAR if tipo_sel == "Solar FV" else PARQUES_EOLICA
    with col_parque:
        parque_sel = st.selectbox(
            "Parque",
            parques_disp,
            format_func=lambda p: NOMBRE_DISPLAY[p],
            key="fcst_parque",
        )
    _grafico_parque(df, parque_sel, df_pcp)
