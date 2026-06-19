"""
Dashboard ERNC AES Andes — App principal Streamlit.
Parques: 6 solares FV (norte) + 5 eólicos (sur) = ~1.824 MW instalados.
"""
import os
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv

load_dotenv()

# ── Paleta AES ────────────────────────────────────────────────────────────────
AES_AZUL    = "#3B4CE8"
AES_CYAN    = "#4DC8DC"
AES_VIOLETA = "#9B6FD4"
AES_VERDE   = "#5AB848"
AES_GRIS    = "#F5F7FA"
AES_TEXTO   = "#1A1F36"
AES_MUTED   = "#6B7280"
AES_BORDE   = "#E5E7EB"
AES_BLANCO  = "#FFFFFF"

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard ERNC — AES Andes",
    page_icon="assets/logo_aes.png" if os.path.exists("assets/logo_aes.png") else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auto-refresh cada hora ─────────────────────────────────────────────────────
st_autorefresh(interval=3_600_000, key="autorefresh_ernc")

# ── CSS global — tema claro con paleta AES ────────────────────────────────────
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, .stApp {{
        font-family: 'Inter', sans-serif;
        background-color: {AES_GRIS};
        color: {AES_TEXTO};
    }}
    .block-container {{ padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1400px; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {AES_BLANCO};
        border-right: 1px solid {AES_BORDE};
    }}
    [data-testid="stSidebar"] * {{ color: {AES_TEXTO} !important; }}
    [data-testid="stSidebar"] hr {{ border-color: {AES_BORDE}; }}

    /* Botones sidebar parques */
    [data-testid="stSidebar"] .stButton button {{
        background: {AES_GRIS};
        border: 1px solid {AES_BORDE};
        color: {AES_TEXTO};
        font-size: 12px;
        text-align: left;
        border-radius: 6px;
        padding: 6px 10px;
        transition: all 0.15s;
    }}
    [data-testid="stSidebar"] .stButton button:hover {{
        background: {AES_AZUL};
        color: white;
        border-color: {AES_AZUL};
    }}
    .btn-activo button {{
        background: {AES_AZUL} !important;
        color: white !important;
        border-color: {AES_AZUL} !important;
        font-weight: 600 !important;
    }}

    /* Métricas */
    [data-testid="metric-container"] {{
        background: {AES_BLANCO};
        border-radius: 10px;
        padding: 14px 18px;
        border: 1px solid {AES_BORDE};
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}
    [data-testid="stMetricLabel"] {{ font-size: 11px; color: {AES_MUTED}; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }}
    [data-testid="stMetricValue"] {{ font-size: 22px; color: {AES_TEXTO}; font-weight: 700; }}
    [data-testid="stMetricDelta"] {{ font-size: 12px; }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background: {AES_BLANCO};
        border-bottom: 2px solid {AES_BORDE};
        gap: 4px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        border-radius: 6px 6px 0 0;
        color: {AES_MUTED};
        font-weight: 500;
        font-size: 13px;
        padding: 8px 16px;
    }}
    .stTabs [aria-selected="true"] {{
        background: transparent;
        color: {AES_AZUL};
        border-bottom: 2px solid {AES_AZUL};
        font-weight: 600;
    }}

    /* Cards */
    .aes-card {{
        background: {AES_BLANCO};
        border-radius: 10px;
        padding: 16px 20px;
        border: 1px solid {AES_BORDE};
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    }}

    /* Tablas */
    [data-testid="stDataFrame"] {{ border-radius: 8px; border: 1px solid {AES_BORDE}; overflow: hidden; }}

    /* Divider */
    hr {{ border-color: {AES_BORDE}; margin: 12px 0; }}

    /* Inputs */
    [data-testid="stSelectbox"] > div {{ border-radius: 6px; }}

    /* Tooltip personalizado */
    .aes-tooltip {{
        position: relative; display: inline-block; cursor: help;
        border-bottom: 1px dashed {AES_MUTED};
    }}
    .aes-tooltip .aes-tooltip-text {{
        visibility: hidden; width: 280px; background: {AES_TEXTO};
        color: white; font-size: 11px; line-height: 1.5;
        border-radius: 6px; padding: 8px 12px;
        position: absolute; z-index: 1000; bottom: 125%; left: 50%;
        margin-left: -140px; opacity: 0; transition: opacity 0.2s;
    }}
    .aes-tooltip:hover .aes-tooltip-text {{ visibility: visible; opacity: 1; }}

    /* Ocultar menú hamburguesa */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Imports propios ────────────────────────────────────────────────────────────
from config import (
    NOMBRE_DISPLAY, TECNOLOGIA, PARQUES_TODOS, PMAX,
    PARQUES_SOLAR, PARQUES_EOLICA, CMG_NODO, CMG_NODOS_TODOS,
)
from utils.db import (
    query_gen_real_ultimas_horas,
    query_gen_prog_ultimas_horas,
    query_cmg_ultimo,
    query_limitaciones_activas,
    query_ultima_hora_gen,
)
from components.kpis_generales import render_kpis
from components.mapa_ernc import render_mapa
from components.tab_solar import render_tab_solar
from components.tab_eolica import render_tab_eolica
from components.tab_forecast import render_tab_forecast
from components.tab_insights import render_tab_insights


# ── Carga de datos ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def cargar_datos():
    gen_rows    = query_gen_real_ultimas_horas(48)
    prog_rows   = query_gen_prog_ultimas_horas(48)
    cmg_rows    = query_cmg_ultimo()
    lim_rows    = query_limitaciones_activas()
    ultima_hora = query_ultima_hora_gen()
    return gen_rows, prog_rows, cmg_rows, lim_rows, ultima_hora


def ultima_gen_por_parque(gen_rows: list[dict]) -> dict[str, float | None]:
    vistos: set[str] = set()
    resultado: dict[str, float | None] = {p: None for p in PARQUES_TODOS}
    for r in gen_rows:
        p = r["parque"]
        if p not in vistos and p in resultado:
            resultado[p] = r.get("gen_real_mw")
            vistos.add(p)
        if len(vistos) == len(PARQUES_TODOS):
            break
    return resultado


def ultima_prog_por_parque(prog_rows: list[dict]) -> dict[str, float | None]:
    vistos: set[str] = set()
    resultado: dict[str, float | None] = {p: None for p in PARQUES_TODOS}
    for r in prog_rows:
        p = r["parque"]
        if p not in vistos and p in resultado:
            resultado[p] = r.get("gen_programada_mw")
            vistos.add(p)
        if len(vistos) == len(PARQUES_TODOS):
            break
    return resultado


def cmg_crucero(cmg_rows: list[dict]) -> float | None:
    for r in cmg_rows:
        if r["nodo"] == "CRUCERO_______220":
            return r.get("cmg_usd_mwh")
    return None


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar(gen_por_parque: dict[str, float | None]) -> str:
    parque_activo = st.session_state.get("parque_activo", PARQUES_SOLAR[0])

    with st.sidebar:
        st.markdown(
            f"<div style='padding:8px 0 4px'>"
            f"<div style='font-size:18px;font-weight:700;color:{AES_AZUL}'>AES Andes ERNC</div>"
            f"<div style='font-size:11px;color:{AES_MUTED};margin-top:2px'>11 parques renovables · ~1.824 MW</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        # Parques solares
        st.markdown(
            f"<div style='font-size:11px;font-weight:600;color:{AES_MUTED};text-transform:uppercase;"
            f"letter-spacing:0.8px;margin-bottom:6px'>Solar FV</div>",
            unsafe_allow_html=True,
        )
        for p in PARQUES_SOLAR:
            gen = gen_por_parque.get(p)
            gen_str = f"{gen:.1f} MW" if gen is not None else "— MW"
            fp = round(gen / PMAX[p] * 100, 0) if gen and PMAX[p] > 0 else None
            fp_str = f"  {fp:.0f}%" if fp else ""
            is_activo = (p == parque_activo)
            container = st.container()
            with container:
                if is_activo:
                    st.markdown("<div class='btn-activo'>", unsafe_allow_html=True)
                clicked = st.button(
                    f"{NOMBRE_DISPLAY[p]}  ·  {gen_str}{fp_str}",
                    key=f"btn_{p}",
                    use_container_width=True,
                )
                if is_activo:
                    st.markdown("</div>", unsafe_allow_html=True)
                if clicked:
                    st.session_state["parque_activo"] = p
                    st.session_state["tab_forzado"] = "solar"
                    st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Parques eólicos
        st.markdown(
            f"<div style='font-size:11px;font-weight:600;color:{AES_MUTED};text-transform:uppercase;"
            f"letter-spacing:0.8px;margin-bottom:6px'>Eólica</div>",
            unsafe_allow_html=True,
        )
        for p in PARQUES_EOLICA:
            gen = gen_por_parque.get(p)
            gen_str = f"{gen:.1f} MW" if gen is not None else "— MW"
            fp = round(gen / PMAX[p] * 100, 0) if gen and PMAX[p] > 0 else None
            fp_str = f"  {fp:.0f}%" if fp else ""
            is_activo = (p == parque_activo)
            if is_activo:
                st.markdown("<div class='btn-activo'>", unsafe_allow_html=True)
            clicked = st.button(
                f"{NOMBRE_DISPLAY[p]}  ·  {gen_str}{fp_str}",
                key=f"btn_{p}",
                use_container_width=True,
            )
            if is_activo:
                st.markdown("</div>", unsafe_allow_html=True)
            if clicked:
                st.session_state["parque_activo"] = p
                st.session_state["tab_forzado"] = "eolica"
                st.rerun()

        st.divider()

        # Acciones
        if st.button("Actualizar datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        if "pdf_bytes" in st.session_state and st.session_state["pdf_bytes"]:
            import datetime as _dt
            st.download_button(
                label="Descargar reporte PDF",
                data=st.session_state["pdf_bytes"],
                file_name=f"reporte_ernc_{_dt.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        if st.button("Generar reporte PDF", use_container_width=True, key="btn_pdf"):
            st.session_state["generar_pdf"] = True

    return st.session_state.get("parque_activo", PARQUES_SOLAR[0])


# ── Layout principal ──────────────────────────────────────────────────────────

def main():
    with st.spinner("Cargando datos..."):
        try:
            gen_rows, prog_rows, cmg_rows, lim_rows, ultima_hora = cargar_datos()
        except Exception as e:
            st.error(f"Error al conectar con Supabase: {e}")
            st.stop()

    gen_por_parque  = ultima_gen_por_parque(gen_rows)
    prog_por_parque = ultima_prog_por_parque(prog_rows)
    cmg_val         = cmg_crucero(cmg_rows)
    n_lim           = len(lim_rows)
    cmg_idx         = {r["nodo"]: r.get("cmg_usd_mwh") for r in cmg_rows}
    cmg_por_parque  = {p: cmg_idx.get(CMG_NODO.get(p)) for p in PARQUES_TODOS}

    # Generación PDF
    if st.session_state.pop("generar_pdf", False):
        from utils.insights import evaluar_insights
        from utils.pdf_report import generar_pdf
        with st.spinner("Generando PDF..."):
            insights = evaluar_insights(gen_por_parque, prog_por_parque, cmg_val, lim_rows)
            pdf_bytes = generar_pdf(
                gen_por_parque=gen_por_parque,
                prog_por_parque=prog_por_parque,
                cmg_crucero=cmg_val,
                cmg_por_parque=cmg_por_parque,
                n_limitaciones=n_lim,
                insights=insights,
                ultima_hora=ultima_hora,
            )
            st.session_state["pdf_bytes"] = pdf_bytes
        st.rerun()

    parque_activo = render_sidebar(gen_por_parque)

    # Header
    hora_label = ultima_hora[11:16] if ultima_hora else "—"
    st.markdown(
        f"<div style='display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px'>"
        f"<h1 style='font-size:22px;font-weight:700;color:{AES_TEXTO};margin:0'>"
        f"Dashboard ERNC — AES Andes</h1>"
        f"<span style='font-size:12px;color:{AES_MUTED}'>Ultima lectura: <b>{hora_label} hrs</b></span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    render_kpis(
        gen_por_parque=gen_por_parque,
        prog_por_parque=prog_por_parque,
        cmg_crucero=cmg_val,
        n_limitaciones_activas=n_lim,
        ultima_hora=ultima_hora,
    )

    st.divider()

    st.session_state.pop("tab_forzado", None)
    tab_labels = ["Mapa & Resumen", "Solar FV", "Eolica", "Forecast 7d", "Insights", "CMG", "Limitaciones"]

    tab_resumen, tab_solar, tab_eolica, tab_forecast, tab_insights, tab_cmg, tab_limitaciones = st.tabs(tab_labels)

    # Mostrar detalle del parque activo si viene desde sidebar
    parque_tec = TECNOLOGIA.get(parque_activo, "Solar")

    with tab_resumen:
        _render_tab_resumen(gen_por_parque, gen_rows, prog_rows)

    with tab_solar:
        render_tab_solar(gen_por_parque, prog_por_parque, gen_rows, prog_rows, parque_activo if parque_tec == "Solar" else None)

    with tab_eolica:
        render_tab_eolica(gen_por_parque, prog_por_parque, gen_rows, prog_rows, parque_activo if parque_tec == "Eólica" else None)

    with tab_forecast:
        render_tab_forecast()

    with tab_insights:
        render_tab_insights(
            gen_por_parque=gen_por_parque,
            prog_por_parque=prog_por_parque,
            cmg_crucero=cmg_val,
            lim_rows=lim_rows,
        )

    with tab_cmg:
        _render_tab_cmg(cmg_rows)

    with tab_limitaciones:
        _render_tab_limitaciones(lim_rows)


# ── Tab Resumen ───────────────────────────────────────────────────────────────

def _render_tab_resumen(gen_por_parque, gen_rows, prog_rows):
    import plotly.graph_objects as go
    import pandas as pd

    col_mapa, col_tabla = st.columns([3, 2])

    with col_mapa:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
            f"Generacion actual por parque</div>",
            unsafe_allow_html=True,
        )
        render_mapa(gen_por_parque)

    with col_tabla:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
            f"Estado del portfolio</div>",
            unsafe_allow_html=True,
        )
        filas = []
        for p in PARQUES_TODOS:
            gen = gen_por_parque.get(p)
            fp  = round(gen / PMAX[p] * 100, 1) if gen and PMAX[p] > 0 else None
            filas.append({
                "Parque":   NOMBRE_DISPLAY[p],
                "Tipo":     TECNOLOGIA[p],
                "Gen. MW":  f"{gen:.1f}" if gen is not None else "—",
                "FP %":     f"{fp:.1f}"  if fp  is not None else "—",
            })
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:16px 0 8px'>"
        f"Generacion total portfolio — ultimas 24 horas</div>",
        unsafe_allow_html=True,
    )
    if not gen_rows:
        st.info("Sin datos de generacion en las ultimas 24 horas.")
        return

    df_gen = pd.DataFrame(gen_rows)
    df_gen["fecha_hora"] = pd.to_datetime(df_gen["fecha_hora"])
    df_gen = df_gen[df_gen["fecha_hora"] >= df_gen["fecha_hora"].max() - pd.Timedelta(hours=24)]
    df_total = df_gen.groupby("fecha_hora")["gen_real_mw"].sum().reset_index()
    df_total.rename(columns={"gen_real_mw": "Real MW"}, inplace=True)

    if prog_rows:
        df_prog = pd.DataFrame(prog_rows)
        df_prog["fecha_hora"] = pd.to_datetime(df_prog["fecha_hora"])
        df_prog = df_prog[df_prog["fecha_hora"] >= df_prog["fecha_hora"].max() - pd.Timedelta(hours=24)]
        df_prog_t = df_prog.groupby("fecha_hora")["gen_programada_mw"].sum().reset_index()
        df_prog_t.rename(columns={"gen_programada_mw": "Programada MW"}, inplace=True)
        df_total = df_total.merge(df_prog_t, on="fecha_hora", how="left")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_total["fecha_hora"], y=df_total["Real MW"],
        name="Real", line=dict(color=AES_AZUL, width=2.5),
        fill="tozeroy", fillcolor="rgba(59,76,232,0.08)",
        hovertemplate="%{y:.1f} MW<extra>Real</extra>",
    ))
    if "Programada MW" in df_total.columns:
        fig.add_trace(go.Scatter(
            x=df_total["fecha_hora"], y=df_total["Programada MW"],
            name="Programada", line=dict(color=AES_CYAN, width=1.5, dash="dash"),
            hovertemplate="%{y:.1f} MW<extra>Programada PCP</extra>",
        ))
    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
        xaxis_title=None, yaxis_title="MW", legend_title=None,
        height=300, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key="mapa_grafico_tendencia")


# ── Tab CMG ────────────────────────────────────────────────────────────────────

def _render_tab_cmg(cmg_rows):
    import plotly.graph_objects as go
    import pandas as pd
    from utils.db import get_client
    from datetime import datetime, timedelta, timezone

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:12px'>"
        f"Costo Marginal Local — todos los nodos disponibles</div>",
        unsafe_allow_html=True,
    )

    if not cmg_rows:
        st.warning("Sin datos de CMG disponibles.")
        return

    cmg_actual = {r["nodo"]: r for r in cmg_rows}

    filas_tabla = []
    for nodo in CMG_NODOS_TODOS:
        r = cmg_actual.get(nodo)
        filas_tabla.append({
            "Nodo": nodo.replace("_", " ").strip(),
            "CMG (USD/MWh)": f"{r['cmg_usd_mwh']:.1f}" if r else "—",
            "Hora": r["fecha_hora"][11:16] if r else "—",
        })

    col_norte, col_sur, col_tabla = st.columns([1, 1, 3])
    with col_norte:
        r_n = cmg_actual.get("CRUCERO_______220")
        st.metric(
            "CRUCERO 220 kV (norte/solar)",
            f"{r_n['cmg_usd_mwh']:.1f} USD/MWh" if r_n else "—",
            delta=r_n["fecha_hora"][11:16] if r_n else None,
            help="Nodo de referencia para parques solares FV del norte (Atacama/Antofagasta). Fuente: JSON S3 Coordinador Electrico Nacional, actualiza cada ~15 min.",
        )
    with col_sur:
        r_s = cmg_actual.get("CHARRUA_______220")
        st.metric(
            "CHARRUA 220 kV (sur/eolica)",
            f"{r_s['cmg_usd_mwh']:.1f} USD/MWh" if r_s else "—",
            delta=r_s["fecha_hora"][11:16] if r_s else None,
            help="Nodo de referencia probable para parques eolicos del sur (Bio-Bio/Coquimbo). Pendiente confirmar con AES Andes. Fuente: JSON S3 CEN.",
        )
    with col_tabla:
        st.dataframe(pd.DataFrame(filas_tabla), hide_index=True, use_container_width=True)

    st.divider()
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
        f"Historico 48 horas — todos los nodos</div>",
        unsafe_allow_html=True,
    )
    try:
        sb = get_client()
        desde = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
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
            paleta = [AES_AZUL, AES_CYAN, AES_VIOLETA, AES_VERDE,
                      "#F59E0B", "#EF4444", "#6366F1", "#EC4899"]
            nodos_presentes = df_hist["nodo"].unique().tolist()
            fig = go.Figure()
            for i, nodo in enumerate(nodos_presentes):
                df_n = df_hist[df_hist["nodo"] == nodo].sort_values("fecha_hora")
                es_principal = nodo in ("CRUCERO_______220", "CHARRUA_______220")
                fig.add_trace(go.Scatter(
                    x=df_n["fecha_hora"], y=df_n["cmg_usd_mwh"],
                    name=nodo.replace("_", " ").strip(),
                    line=dict(color=paleta[i % len(paleta)],
                              width=2.5 if es_principal else 1.2,
                              dash="solid" if es_principal else "dot"),
                    hovertemplate="%{y:.1f} USD/MWh<extra>" + nodo + "</extra>",
                ))
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
    except Exception as e:
        st.warning(f"No se pudo cargar historico CMG: {e}")


# ── Tab Limitaciones ──────────────────────────────────────────────────────────

def _render_tab_limitaciones(lim_rows):
    import pandas as pd

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:12px'>"
        f"Limitaciones de transmision activas</div>",
        unsafe_allow_html=True,
    )

    if not lim_rows:
        st.success("Sin limitaciones de transmision activas.")
        return

    st.markdown(
        f"<div style='background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;"
        f"padding:10px 16px;margin-bottom:12px;font-size:13px;color:#991B1B'>"
        f"<b>{len(lim_rows)} limitacion(es) activa(s)</b></div>",
        unsafe_allow_html=True,
    )

    df = pd.DataFrame(lim_rows)
    cols_show = [c for c in [
        "parque", "instalacion_nombre", "potencia", "unidad_medida_potencia",
        "status", "fecha_perturbacion", "observacion",
    ] if c in df.columns]
    df_show = df[cols_show].copy()
    df_show.rename(columns={
        "parque": "Parque", "instalacion_nombre": "Instalacion",
        "potencia": "Potencia", "unidad_medida_potencia": "Unidad",
        "status": "Estado", "fecha_perturbacion": "Fecha inicio",
        "observacion": "Observacion",
    }, inplace=True)
    if "Parque" in df_show.columns:
        df_show["Parque"] = df_show["Parque"].map(NOMBRE_DISPLAY).fillna(df_show["Parque"])
    st.dataframe(df_show, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
