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
        desde = (datetime.now(timezone(timedelta(hours=-3))) - timedelta(hours=120)).strftime("%Y-%m-%d %H:%M:%S")
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

    # Modelo FV — solo horas diurnas (filtrar is_day=False para no llenar el gráfico de ceros)
    if not df_meteo.empty and "p_fv_estimada_mw" in df_meteo.columns:
        df_dia = df_meteo[df_meteo["is_day"] == True].copy() if "is_day" in df_meteo.columns else df_meteo.copy()
        if not df_dia.empty:
            fig.add_trace(go.Scatter(
                x=df_dia["fecha_hora"], y=df_dia["p_fv_estimada_mw"],
                name="Modelo FV",
                line=dict(color=AES_VIOLETA, width=1.5, dash="dot"),
                fill="tozeroy", fillcolor="rgba(155,111,212,0.06)",
                hovertemplate=(
                    "%{y:.1f} MW"
                    "<extra>Modelo FV: P = Pₙᴵᶜᵒ × GTI/1000 × [1 + γ(Tᴄ⁻25)]"
                    "<br>γ = -0.4%/°C | NOCT = 45°C | GTI = irradiancia en plano inclinado"
                    "</extra>"
                ),
            ))

    if not df_prog.empty:
        df_p = df_prog[df_prog["parque"] == parque]
        if not df_p.empty:
            fig.add_trace(go.Scatter(
                x=df_p["fecha_hora"], y=df_p["gen_programada_mw"],
                name="PCP programada",
                line=dict(color=AES_AMBAR, width=1.8, dash="dash"),
                hovertemplate="%{y:.1f} MW<extra>Programada CEN PCP — declarada por el generador D-1</extra>",
            ))

    if not df_gen.empty:
        df_r = df_gen[df_gen["parque"] == parque]
        if not df_r.empty:
            # Filtrar valores negativos atípicos (pueden aparecer por despacho negativo del BESS)
            df_r = df_r[df_r["gen_real_mw"] >= 0].copy()
            fig.add_trace(go.Scatter(
                x=df_r["fecha_hora"], y=df_r["gen_real_mw"],
                name="Generacion real",
                line=dict(color=AES_AZUL, width=2.5),
                fill="tozeroy", fillcolor="rgba(59,76,232,0.08)",
                hovertemplate="%{y:.1f} MW<extra>Gen. real CEN gen-real/v3</extra>",
            ))

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=AES_BLANCO,
        plot_bgcolor=AES_GRIS,
        transition=dict(duration=500, easing="cubic-in-out"),
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None,
        yaxis_title="MW",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE, rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True, key=f"solar_grafico_gen_{parque}")


def _grafico_ghi(df_meteo: pd.DataFrame, parque: str) -> None:
    if df_meteo.empty or "ghi_wm2" not in df_meteo.columns:
        return

    fig = go.Figure()
    hist = df_meteo[df_meteo["es_forecast"] == False]
    fore = df_meteo[df_meteo["es_forecast"] == True]

    if not hist.empty:
        fig.add_trace(go.Scatter(
            x=hist["fecha_hora"], y=hist["ghi_wm2"],
            name="GHI historico",
            line=dict(color=AES_AMBAR, width=2),
            fill="tozeroy", fillcolor="rgba(245,158,11,0.08)",
            hovertemplate="%{y:.0f} W/m²<extra>GHI hist. — Global Horizontal Irradiance (shortwave_radiation Open-Meteo)</extra>",
        ))
    if not fore.empty:
        fig.add_trace(go.Scatter(
            x=fore["fecha_hora"], y=fore["ghi_wm2"],
            name="GHI forecast",
            line=dict(color=AES_AMBAR, width=1.5, dash="dot"),
            hovertemplate="%{y:.0f} W/m²<extra>GHI forecast Open-Meteo (7 d)</extra>",
        ))
    if "cloudcover_low_pct" in df_meteo.columns:
        fig.add_trace(go.Scatter(
            x=df_meteo["fecha_hora"], y=df_meteo["cloudcover_low_pct"],
            name="Nubosidad baja %",
            yaxis="y2",
            line=dict(color=AES_MUTED, width=1, dash="dot"),
            hovertemplate="%{y:.0f}%<extra>Nubosidad baja (camanchaca si >60% con cielo total <35%)</extra>",
        ))

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=AES_BLANCO,
        plot_bgcolor=AES_GRIS,
        transition=dict(duration=500, easing="cubic-in-out"),
        height=220,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None,
        yaxis_title="W/m²",
        yaxis2=dict(title="Nubosidad %", overlaying="y", side="right", range=[0, 100], showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key=f"solar_grafico_ghi_{parque}")


def _panel_metricas(gen_por_parque, prog_por_parque, df_meteo, parque_sel):
    """Fila de métricas horizontales debajo del gráfico de generación."""
    gen  = gen_por_parque.get(parque_sel)
    prog = prog_por_parque.get(parque_sel)
    fp   = calcular_factor_planta(gen, PMAX[parque_sel])
    dev  = calcular_desvio(gen, prog)

    ghi = tc = None
    if not df_meteo.empty:
        hist_m = df_meteo[df_meteo["es_forecast"] == False]
        if len(hist_m) > 0:
            u   = hist_m.iloc[-1]
            ghi = u.get("ghi_wm2")
            tc  = u.get("temp_celda_c")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric(
            "Generacion actual",
            f"{gen:.1f} MW" if gen is not None else "—",
            help=f"Ultimo valor gen_real_mw para {NOMBRE_DISPLAY[parque_sel]}. Fuente: CEN gen-real/v3.",
        )
    with c2:
        st.metric(
            "Cap. instalada",
            f"{PMAX[parque_sel]:.1f} MW",
            help=f"Potencia maxima declarada en API CEN para {NOMBRE_DISPLAY[parque_sel]}.",
        )
    with c3:
        st.metric(
            "Factor de planta",
            f"{fp:.1f}%" if fp else "—",
            help="FP = Gen.real / Cap.instalada x 100. Fraccion de la capacidad en uso.",
        )
    with c4:
        color = _SEM.get(dev["semaforo"], AES_MUTED) if dev["desvio_pct"] is not None else AES_MUTED
        desvio_str = f"{dev['desvio_pct']:+.1f}%" if dev["desvio_pct"] is not None else "—"
        st.metric(
            "Desvio vs PCP",
            desvio_str,
            delta=f"{dev['desvio_mw']:+.1f} MW" if dev["desvio_mw"] is not None else None,
            help="Desvio = (Gen.real - PCP) / PCP x 100. Verde: <15%, Amarillo: 15-25%, Rojo: >25%.",
        )
    with c5:
        st.metric(
            "GHI",
            f"{ghi:.0f} W/m²" if ghi else "—",
            help=(
                "Global Horizontal Irradiance [W/m²]. Irradiancia solar total sobre superficie horizontal. "
                "Fuente: Open-Meteo shortwave_radiation, sin API key, resolucion horaria."
            ),
        )
    with c6:
        st.metric(
            "Temp. celda",
            f"{tc:.1f} °C" if tc else "—",
            help=(
                "Temperatura de celda FV [degC]. "
                "Formula: Tc = T_amb + (NOCT - 20) / 800 x GHI x f_viento. "
                "NOCT = 45 degC. A mayor Tc, menor eficiencia (gamma = -0.4%/degC). "
                "Fuente: calculos.py usando Open-Meteo."
            ),
        )


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

    col_sel, col_ventana = st.columns([3, 1])
    with col_sel:
        parque_sel = st.selectbox(
            "Parque solar",
            PARQUES_SOLAR,
            index=PARQUES_SOLAR.index(parque_activo) if parque_activo in PARQUES_SOLAR else 0,
            format_func=lambda p: NOMBRE_DISPLAY[p],
            key="solar_parque_sel",
        )
    with col_ventana:
        horas_ventana = st.selectbox(
            "Ventana",
            [24, 48, 72, 120],
            index=1,
            format_func=lambda h: f"Ultimas {h} h",
            key="solar_ventana_horas",
        )

    corte = pd.Timestamp.now(tz="America/Santiago") - pd.Timedelta(hours=horas_ventana)
    df_gen  = pd.DataFrame(gen_rows)
    df_prog = pd.DataFrame(prog_rows) if prog_rows else pd.DataFrame()
    if not df_gen.empty:
        df_gen["fecha_hora"] = pd.to_datetime(df_gen["fecha_hora"])
        df_gen = df_gen[df_gen["parque"].isin(PARQUES_SOLAR)]
        df_gen = df_gen[df_gen["fecha_hora"] >= corte]
    if not df_prog.empty:
        df_prog["fecha_hora"] = pd.to_datetime(df_prog["fecha_hora"])
        df_prog = df_prog[df_prog["parque"].isin(PARQUES_SOLAR)]
        df_prog = df_prog[df_prog["fecha_hora"] >= corte]

    df_meteo = _df_meteo(parque_sel)

    # ── Título + gráfico generación a ancho completo ──
    nombre_ventana = f"ultimas {horas_ventana} h"
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:6px'>"
        f"Generacion — {NOMBRE_DISPLAY[parque_sel]} ({nombre_ventana})</div>",
        unsafe_allow_html=True,
    )
    _grafico_gen(df_gen, df_prog, df_meteo, parque_sel)

    # ── Fila de métricas horizontales ──
    _panel_metricas(gen_por_parque, prog_por_parque, df_meteo, parque_sel)

    # ── Fórmulas del modelo en expander ──
    with st.expander("Variables y formulas del modelo FV", expanded=False):
        st.markdown(
            f"""
<div style='font-size:12px;line-height:1.9;color:{AES_TEXTO}'>

**Series de tiempo mostradas**
| Serie | Color | Descripcion |
|-------|-------|-------------|
| Generacion real | Azul solido | Gen. real CEN (gen-real/v3). Datos BESS excluidos por llave_opreal. Negativos filtrados. |
| PCP programada | Ambar rayado | Generacion programada declarada D-1 ante el Coordinador (SIPUB gen-programada-pcp/v4). |
| Modelo FV | Violeta punteado | Estimacion fisico-estadistica. Solo horas diurnas. Ceros nocturnos excluidos del grafico. |

**Modelo de potencia FV**

P = P_pico × (GTI / 1000) × [1 + γ × (T_c − 25)]

- **P_pico**: capacidad instalada [MW]
- **GTI**: irradiancia en plano inclinado a tilt=20°, azimuth=0° (norte) [W/m²]
- **γ = −0.004 /°C**: coeficiente de temperatura de potencia (silicio monocristalino tipico)
- **T_c**: temperatura de celda [°C] = T_amb + (NOCT−20)/800 × GHI × f_viento
  - NOCT = 45°C (Normal Operating Cell Temperature)
  - f_viento ≈ 0.9 a 1.0 (corrección por viento)

**Irradiancia GHI + nubosidad baja**
- **GHI** (shortwave_radiation): irradiancia global horizontal [W/m²] — recurso solar disponible
- **Nubosidad baja %** (cloudcover_low): fraccion cubierta por nubes bajas. Si >60% con cielo total <35%: posible camanchaca

Fuente meteorologica: **Open-Meteo** (gratuita, sin API key, actualizacion horaria)
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:16px 0 6px'>"
        f"Irradiancia GHI + nubosidad baja — {NOMBRE_DISPLAY[parque_sel]}</div>",
        unsafe_allow_html=True,
    )
    _grafico_ghi(df_meteo, parque_sel)
