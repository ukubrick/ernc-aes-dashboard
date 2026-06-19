"""Tab Eolica — tema claro, paleta AES, tooltips explicativos."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone

from config import NOMBRE_DISPLAY, PMAX, PARQUES_EOLICA
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
            .select(
                "fecha_hora,wind_speed_10m,wind_speed_80m,wind_speed_100m,"
                "wind_gusts_10m,wind_dir_80m,wind_shear_alpha,"
                "densidad_aire,p_eolica_estimada_mw,boundary_layer_height,"
                "temp_2m,es_forecast"
            )
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


def _kpis_eolica(gen_por_parque: dict, prog_por_parque: dict, parque_activo: str | None) -> None:
    cols = st.columns(len(PARQUES_EOLICA))
    for i, p in enumerate(PARQUES_EOLICA):
        gen    = gen_por_parque.get(p)
        fp     = calcular_factor_planta(gen, PMAX[p])
        nombre = NOMBRE_DISPLAY[p]
        gen_str = "—" if gen is None else f"{gen:.1f}"
        fp_str  = "—" if fp  is None else f"{fp:.1f}%"
        is_sel  = (p == parque_activo)
        borde_color = AES_CYAN if is_sel else AES_BORDE
        bg_color    = "#EBF9FB" if is_sel else AES_BLANCO
        with cols[i]:
            st.markdown(
                f"<div style='background:{bg_color};border-radius:8px;padding:10px 12px;"
                f"border:1px solid {borde_color}'>"
                f"<div style='font-size:10px;color:{AES_MUTED};margin-bottom:2px;text-transform:uppercase;letter-spacing:0.5px'>{nombre}</div>"
                f"<div style='font-size:19px;font-weight:700;color:{AES_TEXTO}'>"
                f"{gen_str} <span style='font-size:11px;font-weight:400;color:{AES_MUTED}'>MW</span></div>"
                f"<div style='font-size:11px;color:{AES_MUTED}'>FP: "
                f"<b style='color:{AES_CYAN}'>{fp_str}</b></div>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _grafico_gen(gen_rows: list, prog_rows: list, df_meteo: pd.DataFrame, parque: str) -> None:
    fig = go.Figure()

    if not df_meteo.empty and "p_eolica_estimada_mw" in df_meteo.columns:
        fig.add_trace(go.Scatter(
            x=df_meteo["fecha_hora"], y=df_meteo["p_eolica_estimada_mw"],
            name="Modelo eolico", line=dict(color=AES_VIOLETA, width=1.5, dash="dot"),
            fill="tozeroy", fillcolor="rgba(155,111,212,0.06)",
            hovertemplate="%{y:.1f} MW<extra>Modelo: P=0.5xρxAxCpxv³</extra>",
        ))

    if prog_rows:
        df_p = pd.DataFrame(prog_rows)
        df_p["fecha_hora"] = pd.to_datetime(df_p["fecha_hora"])
        df_p = df_p[df_p["parque"] == parque].sort_values("fecha_hora")
        if not df_p.empty:
            fig.add_trace(go.Scatter(
                x=df_p["fecha_hora"], y=df_p["gen_programada_mw"],
                name="PCP", line=dict(color=AES_AMBAR, width=1.5, dash="dash"),
                hovertemplate="%{y:.1f} MW<extra>Programada CEN PCP</extra>",
            ))

    if gen_rows:
        df_r = pd.DataFrame(gen_rows)
        df_r["fecha_hora"] = pd.to_datetime(df_r["fecha_hora"])
        df_r = df_r[df_r["parque"] == parque].sort_values("fecha_hora")
        if not df_r.empty:
            fig.add_trace(go.Scatter(
                x=df_r["fecha_hora"], y=df_r["gen_real_mw"],
                name="Real", line=dict(color=AES_CYAN, width=2.5),
                fill="tozeroy", fillcolor="rgba(77,200,220,0.10)",
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
    st.plotly_chart(fig, use_container_width=True, key="eolica_grafico_gen")


def _grafico_viento(df_meteo: pd.DataFrame) -> None:
    if df_meteo.empty:
        return

    fig = go.Figure()
    for col, label, color, width in [
        ("wind_speed_10m",  "Viento 10m",  AES_MUTED, 1.2),
        ("wind_speed_100m", "Viento 100m (hub)", AES_CYAN, 2.2),
    ]:
        if col in df_meteo.columns:
            hist = df_meteo[df_meteo["es_forecast"] == False]
            fore = df_meteo[df_meteo["es_forecast"] == True]
            if not hist.empty:
                fig.add_trace(go.Scatter(
                    x=hist["fecha_hora"], y=hist[col],
                    name=label, line=dict(color=color, width=width),
                    hovertemplate=f"%{{y:.1f}} m/s<extra>{label}</extra>",
                ))
            if not fore.empty:
                fig.add_trace(go.Scatter(
                    x=fore["fecha_hora"], y=fore[col],
                    name=f"{label} fcst", line=dict(color=color, width=1, dash="dot"),
                    showlegend=False,
                    hovertemplate=f"%{{y:.1f}} m/s<extra>{label} forecast</extra>",
                ))

    if "wind_gusts_10m" in df_meteo.columns:
        fig.add_trace(go.Scatter(
            x=df_meteo["fecha_hora"], y=df_meteo["wind_gusts_10m"],
            name="Rafagas", line=dict(color=AES_ROJO, width=1, dash="dot"),
            hovertemplate="%{y:.1f} m/s<extra>Rafagas maximas 10m</extra>",
        ))

    if "wind_shear_alpha" in df_meteo.columns:
        fig.add_trace(go.Scatter(
            x=df_meteo["fecha_hora"], y=df_meteo["wind_shear_alpha"],
            name="Shear α", yaxis="y2",
            line=dict(color=AES_VIOLETA, width=1, dash="dot"),
            hovertemplate="%{y:.3f}<extra>Wind shear α (ley de potencia: v=v_ref x (h/h_ref)^α)</extra>",
        ))

    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
        height=240, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None, yaxis_title="m/s",
        yaxis2=dict(title="α", overlaying="y", side="right", range=[0, 0.6], showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key="eolica_grafico_viento")


def render_tab_eolica(
    gen_por_parque: dict,
    prog_por_parque: dict,
    gen_rows: list,
    prog_rows: list,
    parque_activo: str | None = None,
) -> None:
    if parque_activo is None:
        parque_activo = PARQUES_EOLICA[0]

    _kpis_eolica(gen_por_parque, prog_por_parque, parque_activo)
    st.divider()

    parque_sel = st.selectbox(
        "Parque eolico",
        PARQUES_EOLICA,
        index=PARQUES_EOLICA.index(parque_activo) if parque_activo in PARQUES_EOLICA else 0,
        format_func=lambda p: NOMBRE_DISPLAY[p],
        key="eolica_parque_sel",
    )

    df_meteo = _df_meteo(parque_sel)

    col_gen, col_info = st.columns([3, 1])

    with col_gen:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:6px'>"
            f"Generacion — {NOMBRE_DISPLAY[parque_sel]} (ultimas 48 h)</div>",
            unsafe_allow_html=True,
        )
        _grafico_gen(gen_rows, prog_rows, df_meteo, parque_sel)

    with col_info:
        gen  = gen_por_parque.get(parque_sel)
        prog = prog_por_parque.get(parque_sel)
        fp   = calcular_factor_planta(gen, PMAX[parque_sel])
        dev  = calcular_desvio(gen, prog)

        st.metric(
            "Generacion actual",
            f"{gen:.1f} MW" if gen is not None else "—",
            help=f"Ultimo valor gen_real_mw para {NOMBRE_DISPLAY[parque_sel]}. Fuente: CEN gen-real/v3.",
        )
        st.metric(
            "Cap. instalada",
            f"{PMAX[parque_sel]:.1f} MW",
            help=f"Potencia maxima declarada en CEN para {NOMBRE_DISPLAY[parque_sel]}.",
        )
        st.metric(
            "Factor de planta",
            f"{fp:.1f}%" if fp else "—",
            help="FP = Gen.real / Cap.instalada x 100.",
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
                v100  = u.get("wind_speed_100m")
                alpha = u.get("wind_shear_alpha")
                gusts = u.get("wind_gusts_10m")
                st.divider()
                st.metric(
                    "Viento 100m",
                    f"{v100:.1f} m/s" if v100 else "—",
                    help="Velocidad de viento interpolada a 100m (altura hub tipica) usando ley de potencia: v100 = v80 x (100/80)^α. Fuente: Open-Meteo windspeed_80m + windspeed_120m.",
                )
                st.metric(
                    "Rafagas maximas",
                    f"{gusts:.1f} m/s" if gusts else "—",
                    help="Rafagas maximas a 10m. Cut-out tipico ~20 m/s. Fuente: Open-Meteo windgusts_10m.",
                )
                st.metric(
                    "Wind shear α",
                    f"{alpha:.3f}" if alpha else "—",
                    help="Exponente de la ley de potencia del perfil de viento: v(h) = v_ref x (h/h_ref)^α. α > 0.30 indica atm. estable con estelas persistentes. Calculado de v80m y v120m.",
                )

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:12px 0 6px'>"
        f"Velocidad de viento + shear + rafagas</div>",
        unsafe_allow_html=True,
    )
    _grafico_viento(df_meteo)
