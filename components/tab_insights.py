"""Tab Insights — tema claro, paleta AES, sin emojis."""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from utils.insights import Insight, evaluar_insights

AES_AZUL    = "#3B4CE8"
AES_CYAN    = "#4DC8DC"
AES_VERDE   = "#5AB848"
AES_ROJO    = "#EF4444"
AES_AMBAR   = "#F59E0B"
AES_VIOLETA = "#9B6FD4"
AES_MUTED   = "#6B7280"
AES_TEXTO   = "#1A1F36"
AES_BORDE   = "#E5E7EB"
AES_BLANCO  = "#FFFFFF"
AES_GRIS    = "#F5F7FA"

_BG     = {"critico": "#FEF2F2", "alerta": "#FFFBEB", "info": "#EFF6FF", "positivo": "#F0FDF4"}
_BORDER = {"critico": AES_ROJO,  "alerta": AES_AMBAR,  "info": AES_AZUL,  "positivo": AES_VERDE}
_LABEL  = {"critico": "CRITICO", "alerta": "ALERTA",   "info": "INFO",    "positivo": "OK"}
_DOT_C  = {"critico": AES_ROJO,  "alerta": AES_AMBAR,  "info": AES_AZUL,  "positivo": AES_VERDE}


def _card(insight: Insight, idx: int = 0) -> None:
    sev = insight.severidad
    delay = f"{idx * 0.06:.2f}s"
    dot_class = "dot-critico" if sev == "critico" else ""
    card_class = f"insight-{sev}"
    badge_bg = {
        "critico":  "rgba(239,68,68,0.12)",
        "alerta":   "rgba(245,158,11,0.12)",
        "info":     "rgba(59,76,232,0.10)",
        "positivo": "rgba(90,184,72,0.10)",
    }[sev]
    st.markdown(
        f"<div class='{card_class}' style='"
        f"background:{_BG[sev]};"
        f"border-left:4px solid {_BORDER[sev]};"
        f"border-radius:0 10px 10px 0;"
        f"padding:14px 18px;"
        f"margin-bottom:10px;"
        f"border:1px solid {_BORDER[sev]}33;"
        f"border-left-color:{_BORDER[sev]};"
        f"animation-delay:{delay};"
        f"transition:transform 0.18s ease,box-shadow 0.18s ease;"
        f"'>"
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px'>"
        f"  <div class='{dot_class}' style='width:9px;height:9px;border-radius:50%;"
        f"background:{_DOT_C[sev]};flex-shrink:0'></div>"
        f"  <span style='font-size:10px;font-weight:700;color:{_BORDER[sev]};"
        f"text-transform:uppercase;letter-spacing:1px;"
        f"background:{badge_bg};padding:2px 8px;border-radius:20px'>"
        f"    {_LABEL[sev]}"
        f"  </span>"
        f"  <span style='font-size:11px;color:{AES_MUTED};margin-left:auto;font-weight:500'>"
        f"    {insight.nombre_parque}"
        f"  </span>"
        f"</div>"
        f"<div style='font-size:13px;font-weight:700;color:{AES_TEXTO};margin-bottom:4px'>"
        f"  {insight.titulo}"
        f"</div>"
        f"<div style='font-size:12px;color:{AES_MUTED};line-height:1.6'>{insight.detalle}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=900)
def _cargar_meteo_actual() -> pd.DataFrame:
    """Último registro meteo histórico de todos los parques (es_forecast=False)."""
    try:
        from utils.db import get_client
        sb = get_client()
        desde = (datetime.now(timezone(timedelta(hours=-3))) - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
        res = (
            sb.table("meteo_ernc")
            .select(
                "parque,fecha_hora,ghi_wm2,temp_2m,temp_celda_c,"
                "wind_speed_10m,wind_speed_100m,wind_gusts_10m,"
                "wind_shear_alpha,cloudcover_low_pct,cloud_cover_pct,"
                "p_fv_estimada_mw,p_eolica_estimada_mw,is_day,es_forecast"
            )
            .eq("es_forecast", False)
            .gte("fecha_hora", desde)
            .order("fecha_hora", desc=True)
            .execute()
        )
        if res.data:
            df = pd.DataFrame(res.data)
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
            # Un registro por parque (el más reciente)
            return df.drop_duplicates(subset="parque", keep="first").reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()


def _render_subtab_alertas(gen_por_parque, prog_por_parque, cmg_crucero, lim_rows):
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:12px'>"
        f"Hallazgos automaticos del portfolio</div>",
        unsafe_allow_html=True,
    )

    with st.spinner("Evaluando condiciones..."):
        insights = evaluar_insights(gen_por_parque, prog_por_parque, cmg_crucero, lim_rows)

    if not insights:
        st.markdown(
            f"<div style='background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;"
            f"padding:14px 18px;color:#166534;font-size:13px'>"
            f"Sin alertas activas. El portfolio opera dentro de parametros normales.</div>",
            unsafe_allow_html=True,
        )
        return

    n_critico  = sum(1 for i in insights if i.severidad == "critico")
    n_alerta   = sum(1 for i in insights if i.severidad == "alerta")
    n_positivo = sum(1 for i in insights if i.severidad == "positivo")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Criticos",  n_critico,  help="Condiciones que requieren atencion inmediata.")
    with c2:
        st.metric("Alertas",   n_alerta,   help="Condiciones fuera de rango normal, monitorear.")
    with c3:
        st.metric("Positivos", n_positivo, help="Parques con rendimiento destacado.")
    with c4:
        st.metric("Total",     len(insights))

    st.divider()

    categorias = ["Todos"] + sorted({i.categoria for i in insights})
    cat_sel = st.segmented_control(
        "Categoria",
        categorias,
        default="Todos",
        key="insights_categoria",
    )

    filtrados = insights if cat_sel == "Todos" else [i for i in insights if i.categoria == cat_sel]

    if not filtrados:
        st.info("Sin hallazgos en esta categoria.")
        return

    for idx, insight in enumerate(filtrados):
        _card(insight, idx)


def _render_subtab_meteo():
    """Tabla de condiciones meteorológicas actuales de todos los parques."""
    from config import NOMBRE_DISPLAY, TECNOLOGIA, PARQUES_SOLAR, PARQUES_EOLICA

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:12px'>"
        f"Condiciones meteorologicas actuales — todos los parques</div>",
        unsafe_allow_html=True,
    )

    df = _cargar_meteo_actual()

    if df.empty:
        st.info(
            "Sin datos meteorologicos recientes. "
            "Ejecuta Adquisicion_meteo_ernc.py o espera al proximo cron (:10 UTC)."
        )
        return

    # ── Tabla Solar FV ──
    st.markdown(
        f"<div style='font-size:12px;font-weight:700;color:{AES_AZUL};text-transform:uppercase;"
        f"letter-spacing:0.8px;margin:8px 0 6px'>Solar FV</div>",
        unsafe_allow_html=True,
    )
    filas_solar = []
    for p in PARQUES_SOLAR:
        row = df[df["parque"] == p]
        if row.empty:
            filas_solar.append({
                "Parque": NOMBRE_DISPLAY[p],
                "Hora": "—",
                "GHI (W/m²)": "—",
                "Temp. celda (°C)": "—",
                "Nub. baja %": "—",
                "Modelo FV (MW)": "—",
                "Diurno": "—",
            })
        else:
            r = row.iloc[0]
            ghi   = r.get("ghi_wm2")
            tc    = r.get("temp_celda_c")
            cl    = r.get("cloudcover_low_pct")
            p_est = r.get("p_fv_estimada_mw")
            is_d  = r.get("is_day")
            hora  = str(r["fecha_hora"])[11:16] if pd.notna(r["fecha_hora"]) else "—"
            filas_solar.append({
                "Parque": NOMBRE_DISPLAY[p],
                "Hora": hora,
                "GHI (W/m²)": f"{ghi:.0f}" if ghi is not None else "—",
                "Temp. celda (°C)": f"{tc:.1f}" if tc is not None else "—",
                "Nub. baja %": f"{cl:.0f}" if cl is not None else "—",
                "Modelo FV (MW)": f"{p_est:.1f}" if p_est is not None else "—",
                "Diurno": "Si" if is_d else "No",
            })
    st.dataframe(pd.DataFrame(filas_solar), hide_index=True, use_container_width=True)

    st.markdown(
        f"<div style='font-size:10px;color:{AES_MUTED};margin-bottom:14px'>"
        f"GHI = irradiancia global horizontal [W/m²] | Tc = temperatura celda = T_amb + (NOCT-20)/800 x GHI | "
        f"Nub. baja = fraccion nubosidad baja (camanchaca si >60% con cielo total &lt;35%)"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Tabla Eólica ──
    st.markdown(
        f"<div style='font-size:12px;font-weight:700;color:{AES_CYAN};text-transform:uppercase;"
        f"letter-spacing:0.8px;margin:8px 0 6px'>Eolica</div>",
        unsafe_allow_html=True,
    )
    filas_eolica = []
    for p in PARQUES_EOLICA:
        row = df[df["parque"] == p]
        if row.empty:
            filas_eolica.append({
                "Parque": NOMBRE_DISPLAY[p],
                "Hora": "—",
                "V10m (m/s)": "—",
                "V100m (m/s)": "—",
                "Rafagas (m/s)": "—",
                "Shear α": "—",
                "Modelo EO (MW)": "—",
            })
        else:
            r = row.iloc[0]
            v10   = r.get("wind_speed_10m")
            v100  = r.get("wind_speed_100m")
            gusts = r.get("wind_gusts_10m")
            alpha = r.get("wind_shear_alpha")
            p_est = r.get("p_eolica_estimada_mw")
            hora  = str(r["fecha_hora"])[11:16] if pd.notna(r["fecha_hora"]) else "—"

            # Alerta de rafagas
            gusts_str = f"{gusts:.1f}" if gusts is not None else "—"
            if gusts and gusts > 20:
                gusts_str = f"{gusts:.1f} !"
            elif gusts and gusts > 16:
                gusts_str = f"{gusts:.1f} ~"

            # Alerta de shear
            alpha_str = f"{alpha:.3f}" if alpha is not None else "—"
            if alpha and alpha > 0.30:
                alpha_str = f"{alpha:.3f} !"

            filas_eolica.append({
                "Parque": NOMBRE_DISPLAY[p],
                "Hora": hora,
                "V10m (m/s)": f"{v10:.1f}" if v10 is not None else "—",
                "V100m (m/s)": f"{v100:.1f}" if v100 is not None else "—",
                "Rafagas (m/s)": gusts_str,
                "Shear α": alpha_str,
                "Modelo EO (MW)": f"{p_est:.1f}" if p_est is not None else "—",
            })
    st.dataframe(pd.DataFrame(filas_eolica), hide_index=True, use_container_width=True)

    st.markdown(
        f"<div style='font-size:10px;color:{AES_MUTED};margin-top:4px'>"
        f"V100m = velocidad hub interpolada a 100m (ley de potencia v80m+v120m) | "
        f"Shear α = exponente perfil vertical (>0.30 !) | "
        f"Rafagas >20 m/s = cut-out (!) | >16 m/s = alerta (~)"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_tab_insights(
    gen_por_parque: dict,
    prog_por_parque: dict,
    cmg_crucero: float | None,
    lim_rows: list,
) -> None:
    subtab_alertas, subtab_meteo = st.tabs(["Alertas operacionales", "Condiciones meteorologicas"])

    with subtab_alertas:
        _render_subtab_alertas(gen_por_parque, prog_por_parque, cmg_crucero, lim_rows)

    with subtab_meteo:
        _render_subtab_meteo()
