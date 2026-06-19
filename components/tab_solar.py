"""Tab Solar FV — tema claro, paleta AES, tooltips explicativos."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone

from config import NOMBRE_DISPLAY, PMAX, PARQUES_SOLAR
from utils.calculos import calcular_factor_planta, calcular_desvio

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

_SEM = {"verde": AES_VERDE, "amarillo": AES_AMBAR, "rojo": AES_ROJO}


def _df_meteo(parque: str) -> pd.DataFrame:
    try:
        from utils.db import get_client
        sb = get_client()
        desde = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
        res = (
            sb.table("meteo_ernc")
            .select("fecha_hora,ghi_wm2,gti_wm2,temp_2m,temp_celda_c,p_fv_estimada_mw,cloudcover_low_pct,cloud_cover_pct,is_day,es_forecast")
            .eq("parque", parque)
            .gte("fecha_hora", desde)
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


def _kpis_solar(gen_por_parque: dict, prog_por_parque: dict, parque_activo: str | None) -> None:
    cols = st.columns(len(PARQUES_SOLAR))
    for i, p in enumerate(PARQUES_SOLAR):
        gen    = gen_por_parque.get(p)
        prog   = prog_por_parque.get(p)
        fp     = calcular_factor_planta(gen, PMAX[p])
        dev    = calcular_desvio(gen, prog)
        nombre = NOMBRE_DISPLAY[p]
        gen_str = "—" if gen is None else f"{gen:.1f}"
        fp_str  = "—" if fp  is None else f"{fp:.1f}%"
        is_sel  = (p == parque_activo)
        borde_color = AES_AZUL if is_sel else AES_BORDE
        bg_color    = "#EEF1FD" if is_sel else AES_BLANCO
        with cols[i]:
            st.markdown(
                f"<div style='background:{bg_color};border-radius:8px;padding:10px 12px;"
                f"border:1px solid {borde_color};cursor:pointer'>"
                f"<div style='font-size:10px;color:{AES_MUTED};margin-bottom:2px;text-transform:uppercase;letter-spacing:0.5px'>{nombre}</div>"
                f"<div style='font-size:19px;font-weight:700;color:{AES_TEXTO}'>"
                f"{gen_str} <span style='font-size:11px;font-weight:400;color:{AES_MUTED}'>MW</span></div>"
                f"<div style='font-size:11px;color:{AES_MUTED}'>FP: "
                f"<b style='color:{AES_AZUL}'>{fp_str}</b></div>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _grafico_gen(df_gen: pd.DataFrame, df_prog: pd.DataFrame, df_meteo: pd.DataFrame, parque: str) -> None:
    fig = go.Figure()

    if not df_meteo.empty and "p_fv_estimada_mw" in df_meteo.columns:
        fig.add_trace(go.Scatter(
            x=df_meteo["fecha_hora"], y=df_meteo["p_fv_estimada_mw"],
            name="Modelo FV", line=dict(color=AES_VIOLETA, width=1.5, dash="dot"),
            fill="tozeroy", fillcolor="rgba(155,111,212,0.06)",
            hovertemplate="%{y:.1f} MW<extra>Modelo FV (P=Ppico x GTI/1000 x [1+γ(Tc-25)])</extra>",
        ))

    if not df_prog.empty:
        df_p = df_prog[df_prog["parque"] == parque]
        if not df_p.empty:
            fig.add_trace(go.Scatter(
                x=df_p["fecha_hora"], y=df_p["gen_programada_mw"],
                name="PCP", line=dict(color=AES_CYAN, width=1.5, dash="dash"),
                hovertemplate="%{y:.1f} MW<extra>Programada CEN PCP</extra>",
            ))

    if not df_gen.empty:
        df_r = df_gen[df_gen["parque"] == parque]
        if not df_r.empty:
            fig.add_trace(go.Scatter(
                x=df_r["fecha_hora"], y=df_r["gen_real_mw"],
                name="Real", line=dict(color=AES_AZUL, width=2.5),
                fill="tozeroy", fillcolor="rgba(59,76,232,0.08)",
                hovertemplate="%{y:.1f} MW<extra>Gen. real CEN</extra>",
            ))

    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
        height=280, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None, yaxis_title="MW",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True)


def _grafico_ghi(df_meteo: pd.DataFrame) -> None:
    if df_meteo.empty or "ghi_wm2" not in df_meteo.columns:
        return

    fig = go.Figure()
    hist = df_meteo[df_meteo["es_forecast"] == False]
    fore = df_meteo[df_meteo["es_forecast"] == True]

    if not hist.empty:
        fig.add_trace(go.Scatter(
            x=hist["fecha_hora"], y=hist["ghi_wm2"],
            name="GHI historico", line=dict(color=AES_AMBAR, width=2),
            fill="tozeroy", fillcolor="rgba(245,158,11,0.08)",
            hovertemplate="%{y:.0f} W/m²<extra>GHI historico</extra>",
        ))
    if not fore.empty:
        fig.add_trace(go.Scatter(
            x=fore["fecha_hora"], y=fore["ghi_wm2"],
            name="GHI forecast", line=dict(color=AES_AMBAR, width=1.5, dash="dot"),
            hovertemplate="%{y:.0f} W/m²<extra>GHI forecast Open-Meteo</extra>",
        ))
    if "cloudcover_low_pct" in df_meteo.columns:
        fig.add_trace(go.Scatter(
            x=df_meteo["fecha_hora"], y=df_meteo["cloudcover_low_pct"],
            name="Nubosidad baja %", yaxis="y2",
            line=dict(color=AES_MUTED, width=1, dash="dot"),
            hovertemplate="%{y:.0f}%<extra>Nubosidad baja (camanchaca)</extra>",
        ))

    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
        height=200, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None, yaxis_title="W/m²",
        yaxis2=dict(title="%", overlaying="y", side="right", range=[0, 100], showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True)


def render_tab_solar(
    gen_por_parque: dict,
    prog_por_parque: dict,
    gen_rows: list[dict],
    prog_rows: list[dict],
    parque_activo: str | None = None,
) -> None:
    if parque_activo is None:
        parque_activo = PARQUES_SOLAR[0]

    _kpis_solar(gen_por_parque, prog_por_parque, parque_activo)
    st.divider()

    parque_sel = st.selectbox(
        "Parque solar",
        PARQUES_SOLAR,
        index=PARQUES_SOLAR.index(parque_activo) if parque_activo in PARQUES_SOLAR else 0,
        format_func=lambda p: NOMBRE_DISPLAY[p],
        key="solar_parque_sel",
    )

    corte = pd.Timestamp.now(tz="America/Santiago") - pd.Timedelta(hours=48)
    df_gen  = pd.DataFrame(gen_rows)
    df_prog = pd.DataFrame(prog_rows) if prog_rows else pd.DataFrame()
    if not df_gen.empty:
        df_gen["fecha_hora"] = pd.to_datetime(df_gen["fecha_hora"])
        df_gen = df_gen[df_gen["parque"].isin(PARQUES_SOLAR)]
    if not df_prog.empty:
        df_prog["fecha_hora"] = pd.to_datetime(df_prog["fecha_hora"])
        df_prog = df_prog[df_prog["parque"].isin(PARQUES_SOLAR)]

    df_meteo = _df_meteo(parque_sel)

    col_gen, col_info = st.columns([3, 1])

    with col_gen:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:6px'>"
            f"Generacion — {NOMBRE_DISPLAY[parque_sel]} (ultimas 48 h)</div>",
            unsafe_allow_html=True,
        )
        _grafico_gen(df_gen, df_prog, df_meteo, parque_sel)

    with col_info:
        gen  = gen_por_parque.get(parque_sel)
        prog = prog_por_parque.get(parque_sel)
        fp   = calcular_factor_planta(gen, PMAX[parque_sel])
        dev  = calcular_desvio(gen, prog)

        st.metric(
            "Generacion actual",
            f"{gen:.1f} MW" if gen is not None else "—",
            help=f"Ultimo valor de gen_real_mw para {NOMBRE_DISPLAY[parque_sel]}. Fuente: CEN gen-real/v3.",
        )
        st.metric(
            "Cap. instalada",
            f"{PMAX[parque_sel]:.1f} MW",
            help=f"Potencia maxima declarada en la API CEN para {NOMBRE_DISPLAY[parque_sel]}.",
        )
        st.metric(
            "Factor de planta",
            f"{fp:.1f}%" if fp else "—",
            help="Factor de planta = Gen.real / Cap.instalada x 100. Indica que fraccion de la capacidad se esta utilizando.",
        )
        if dev["desvio_pct"] is not None:
            color = _SEM.get(dev["semaforo"], AES_MUTED)
            st.markdown(
                f"<div style='font-size:11px;color:{AES_MUTED};margin-top:10px'>Desvio vs PCP</div>"
                f"<div style='font-size:22px;font-weight:700;color:{color}'>"
                f"{dev['desvio_pct']:+.1f}%</div>"
                f"<div style='font-size:10px;color:{AES_MUTED}'>{dev['desvio_mw']:+.1f} MW</div>",
                unsafe_allow_html=True,
            )

        if not df_meteo.empty:
            hist_m = df_meteo[df_meteo["es_forecast"] == False]
            if len(hist_m) > 0:
                u = hist_m.iloc[-1]
                st.divider()
                ghi = u.get("ghi_wm2")
                tc  = u.get("temp_celda_c")
                st.metric(
                    "GHI",
                    f"{ghi:.0f} W/m²" if ghi else "—",
                    help="Global Horizontal Irradiance. Irradiancia solar global horizontal medida en W/m². Fuente: Open-Meteo (shortwave_radiation), sin costo, sin API key.",
                )
                st.metric(
                    "Temp. celda",
                    f"{tc:.1f} °C" if tc else "—",
                    help="Temperatura de celda FV calculada: Tc = T_amb + (NOCT-20)/800 x GHI x factor_viento. NOCT=45°C. A mayor temperatura, menor eficiencia (γ = -0.4%/°C).",
                )

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:12px 0 6px'>"
        f"Irradiancia GHI + nubosidad baja</div>",
        unsafe_allow_html=True,
    )
    _grafico_ghi(df_meteo)
