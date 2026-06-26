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

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pulsar — AES Andes",
    page_icon="assets/logo_pulsar.png" if os.path.exists("assets/logo_pulsar.png") else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auto-refresh cada hora ─────────────────────────────────────────────────────
st_autorefresh(interval=3_600_000, key="autorefresh_ernc")

# ── CSS global — tema claro con paleta AES ────────────────────────────────────
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ── Animaciones ──────────────────────────────────────────────────────── */
    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(16px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes fadeInLeft {{
        from {{ opacity: 0; transform: translateX(-12px); }}
        to   {{ opacity: 1; transform: translateX(0); }}
    }}
    @keyframes pulse-border {{
        0%, 100% {{ box-shadow: 0 0 0 0 rgba(239,68,68,0.5); }}
        50%       {{ box-shadow: 0 0 0 6px rgba(239,68,68,0.0); }}
    }}
    @keyframes shimmer {{
        0%   {{ background-position: -400px 0; }}
        100% {{ background-position: 400px 0; }}
    }}
    @keyframes dot-pulse {{
        0%, 100% {{ transform: scale(1); opacity: 1; }}
        50%       {{ transform: scale(1.5); opacity: 0.6; }}
    }}
    @keyframes pulse-green {{
        0%   {{ box-shadow: 0 0 0 0 rgba(90,184,72,0.7); }}
        70%  {{ box-shadow: 0 0 0 7px rgba(90,184,72,0.0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(90,184,72,0.0); }}
    }}
    @keyframes pulse-red {{
        0%   {{ box-shadow: 0 0 0 0 rgba(239,68,68,0.7); }}
        70%  {{ box-shadow: 0 0 0 7px rgba(239,68,68,0.0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(239,68,68,0.0); }}
    }}
    .status-dot {{
        display:inline-block; width:9px; height:9px; border-radius:50%;
        flex-shrink:0; margin-right:8px;
    }}
    .status-dot.ok   {{ background:#5AB848; animation: pulse-green 1.8s infinite; }}
    .status-dot.bad  {{ background:#EF4444; animation: pulse-red 1.8s infinite; }}

    /* ── Base ─────────────────────────────────────────────────────────────── */
    html, body, .stApp {{
        font-family: 'Inter', sans-serif;
        background-color: {AES_GRIS};
        color: {AES_TEXTO};
    }}
    .block-container {{
        padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1400px;
        animation: fadeInUp 0.5s ease both;
    }}

    /* ── Sidebar ──────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(160deg, {AES_AZUL_OSC} 0%, #111540 60%, #0d1035 100%);
        border-right: none;
        box-shadow: 4px 0 20px rgba(0,0,0,0.25);
    }}
    [data-testid="stSidebar"] * {{ color: rgba(255,255,255,0.88) !important; }}
    [data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.12) !important; }}
    /* Logo más arriba: recortar el padding superior del contenido del sidebar */
    [data-testid="stSidebarUserContent"] {{ padding-top: 0.4rem !important; }}
    [data-testid="stSidebar"] .block-container {{ padding-top: 0.4rem !important; }}

    /* Botones sidebar */
    [data-testid="stSidebar"] .stButton button {{
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
        color: rgba(255,255,255,0.82) !important;
        font-size: 12px;
        text-align: left;
        border-radius: 8px;
        padding: 7px 12px;
        transition: all 0.20s cubic-bezier(0.4,0,0.2,1);
    }}
    [data-testid="stSidebar"] .stButton button:hover {{
        background: rgba(77,200,220,0.22);
        border-color: {AES_CYAN};
        color: white !important;
        transform: translateX(3px);
    }}
    .btn-activo button {{
        background: linear-gradient(90deg, {AES_CYAN} 0%, #38b5cc 100%) !important;
        color: {AES_AZUL_OSC} !important;
        border-color: {AES_CYAN} !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(77,200,220,0.40) !important;
    }}

    /* ── st.metric (paneles Solar/Eólica/BESS) ───────────────────────────────
       Los KPIs del portfolio son cards HTML (kpis_generales.py); este bloque
       estiliza los st.metric de los paneles internos de cada vista. */
    [data-testid="metric-container"] {{
        background: {AES_BLANCO};
        border-radius: 12px;
        padding: 16px 18px;
        border: 1px solid {AES_BORDE};
        border-top: 4px solid {AES_AZUL};
        box-shadow: 0 2px 12px rgba(59,76,232,0.08);
        transition: transform 0.20s ease, box-shadow 0.20s ease;
        animation: fadeInUp 0.5s ease both;
    }}
    [data-testid="metric-container"]:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(59,76,232,0.15);
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 10px; color: {AES_MUTED}; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.8px;
    }}
    [data-testid="stMetricValue"] {{ font-size: 22px; color: {AES_TEXTO}; font-weight: 800; }}
    [data-testid="stMetricDelta"] {{ font-size: 12px; font-weight: 600; }}

    /* Delay escalonado + borde-top de color por posición del st.metric */
    [data-testid="metric-container"]:nth-child(1) {{ animation-delay: 0.05s; border-top-color: {AES_AZUL}; }}
    [data-testid="metric-container"]:nth-child(2) {{ animation-delay: 0.10s; border-top-color: {AES_AZUL}; }}
    [data-testid="metric-container"]:nth-child(3) {{ animation-delay: 0.15s; border-top-color: {AES_CYAN}; }}
    [data-testid="metric-container"]:nth-child(4) {{ animation-delay: 0.20s; border-top-color: #F59E0B; }}
    [data-testid="metric-container"]:nth-child(5) {{ animation-delay: 0.25s; border-top-color: {AES_VIOLETA}; }}
    [data-testid="metric-container"]:nth-child(6) {{ animation-delay: 0.30s; border-top-color: {AES_CYAN}; }}
    [data-testid="metric-container"]:nth-child(7) {{ animation-delay: 0.35s; border-top-color: #EF4444; }}

    /* ── Barra de navegación (botones tipo tab) ────────────────────────────── */
    /* Solo afecta botones del área principal — los del sidebar tienen su propio scope */
    .block-container .stButton button {{
        font-size: 13px;
        font-weight: 600;
        padding: 11px 14px;
        min-height: 46px;
        line-height: 1.2;
        white-space: normal;
        border-radius: 10px;
        transition: all 0.18s cubic-bezier(0.4,0,0.2,1);
    }}
    /* Botón inactivo (secondary) — aspecto de tab en reposo */
    .block-container .stButton button[kind="secondary"],
    .block-container .stButton button[data-testid="stBaseButton-secondary"] {{
        background: {AES_BLANCO};
        color: {AES_MUTED};
        border: 1px solid {AES_BORDE};
    }}
    .block-container .stButton button[kind="secondary"]:hover,
    .block-container .stButton button[data-testid="stBaseButton-secondary"]:hover {{
        background: rgba(59,76,232,0.06);
        color: {AES_AZUL};
        border-color: {AES_AZUL};
    }}
    /* Botón activo (primary) — gradiente azul AES */
    .block-container .stButton button[kind="primary"],
    .block-container .stButton button[data-testid="stBaseButton-primary"] {{
        background: linear-gradient(135deg, {AES_AZUL} 0%, {AES_AZUL_OSC} 100%);
        color: white;
        border: 1px solid {AES_AZUL_OSC};
        box-shadow: 0 4px 12px rgba(59,76,232,0.28);
    }}

    /* ── Menú de navegación (barra de categorías tipo escritorio) ─────────── */
    /* Cada categoría es un st.popover a todo el ancho que se despliega hacia
       abajo mostrando sus vistas como botones. Patrón replicado del dashboard
       CTM (ver CLAUDE.md — Sesión 21). */
    [data-testid="stPopover"] > div > button {{
        width: 100%;
        background: linear-gradient(180deg, #FFFFFF 0%, #F3F5FF 100%);
        border: 1.6px solid #C7CDF5;
        border-radius: 10px;
        min-height: 48px;
        font-weight: 700;
        font-size: 14px;
        color: {AES_AZUL_OSC};
        justify-content: center;
        transition: all 0.20s cubic-bezier(0.4,0,0.2,1);
    }}
    [data-testid="stPopover"] > div > button:hover {{
        border-color: {AES_AZUL};
        box-shadow: 0 4px 16px rgba(59,76,232,0.20);
        transform: translateY(-1px);
    }}
    [data-testid="stPopover"] > div > button[aria-expanded="true"] {{
        background: linear-gradient(135deg, {AES_AZUL} 0%, {AES_AZUL_OSC} 100%);
        color: #fff;
        border-color: {AES_AZUL_OSC};
        box-shadow: 0 4px 12px rgba(59,76,232,0.30);
    }}

    /* ── Cards genéricas ──────────────────────────────────────────────────── */
    .aes-card {{
        background: {AES_BLANCO};
        border-radius: 12px;
        padding: 18px 22px;
        border: 1px solid {AES_BORDE};
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        margin-bottom: 14px;
        transition: box-shadow 0.20s ease;
        animation: fadeInUp 0.4s ease both;
    }}
    .aes-card:hover {{ box-shadow: 0 6px 20px rgba(0,0,0,0.10); }}

    /* Card insight crítico pulsante */
    .insight-critico {{
        animation: fadeInLeft 0.4s ease both, pulse-border 2s ease-in-out infinite;
    }}
    .insight-alerta {{
        animation: fadeInLeft 0.4s ease both;
    }}
    .insight-positivo {{
        animation: fadeInLeft 0.4s ease both;
    }}

    /* Dot pulsante en críticos */
    .dot-critico {{
        animation: dot-pulse 1.5s ease-in-out infinite;
    }}

    /* ── Gráficos Plotly ──────────────────────────────────────────────────── */
    [data-testid="stPlotlyChart"] {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        animation: fadeInUp 0.5s ease both;
        transition: box-shadow 0.2s ease;
    }}
    [data-testid="stPlotlyChart"]:hover {{
        box-shadow: 0 6px 20px rgba(59,76,232,0.12);
    }}

    /* ── Mapa pydeck ──────────────────────────────────────────────────────── */
    [data-testid="stDeckGlJsonChart"] {{
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        animation: fadeInUp 0.6s ease both;
    }}

    /* ── Tablas ───────────────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        border-radius: 10px; border: 1px solid {AES_BORDE};
        overflow: hidden;
        animation: fadeInUp 0.45s ease both;
    }}

    /* ── Varios ───────────────────────────────────────────────────────────── */
    hr {{ border-color: {AES_BORDE}; margin: 12px 0; }}
    [data-testid="stSelectbox"] > div {{ border-radius: 8px; }}

    .aes-tooltip {{
        position: relative; display: inline-block; cursor: help;
        border-bottom: 1px dashed {AES_MUTED};
    }}
    .aes-tooltip .aes-tooltip-text {{
        visibility: hidden; width: 280px; background: {AES_TEXTO};
        color: white; font-size: 11px; line-height: 1.5;
        border-radius: 8px; padding: 10px 14px;
        position: absolute; z-index: 1000; bottom: 125%; left: 50%;
        margin-left: -140px; opacity: 0; transition: opacity 0.25s;
        box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }}
    .aes-tooltip:hover .aes-tooltip-text {{ visibility: visible; opacity: 1; }}

    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Imports propios ────────────────────────────────────────────────────────────
from config import (
    NOMBRE_DISPLAY, TECNOLOGIA, PARQUES_TODOS, PMAX, PMAX_FP,
    PARQUES_SOLAR, PARQUES_EOLICA, CMG_NODO, CMG_NODOS_TODOS,
    APP_VERSION,
)
from utils.db import (
    query_gen_real_ultimas_horas,
    query_gen_prog_ultimas_horas,
    query_bess_ultimas_horas,
    query_cmg_ultimo,
    query_cmg_programado,
    query_limitaciones_activas,
    query_ultima_hora_gen,
    query_ultimas_actualizaciones,
)
from utils.calculos import calcular_desvio
from components.kpis_generales import render_kpis
from components.mapa_ernc import render_mapa
from components.tab_solar import render_tab_solar
from components.tab_eolica import render_tab_eolica
from components.tab_forecast import render_tab_forecast
from components.tab_insights import render_tab_insights
from components.tab_estadisticas import render_tab_estadisticas
from components.tab_ml import render_tab_ml
from components.tab_meteo_sistema import render_tab_meteo_sistema
from components.tab_bess import render_tab_bess
from components.tab_infotecnica import render_tab_infotecnica


# ── Carga de datos ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def cargar_datos():
    # 168h = 7 días para soportar la ventana máxima del selector en Solar/Eólica
    gen_rows    = query_gen_real_ultimas_horas(168)
    prog_rows   = query_gen_prog_ultimas_horas(168)
    bess_rows   = query_bess_ultimas_horas(168)
    cmg_rows    = query_cmg_ultimo()
    lim_rows    = query_limitaciones_activas()
    ultima_hora = query_ultima_hora_gen()
    actualizaciones = query_ultimas_actualizaciones()
    return gen_rows, prog_rows, bess_rows, cmg_rows, lim_rows, ultima_hora, actualizaciones


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


def cmg_promedio_sen(cmg_rows: list[dict]) -> float | None:
    """Promedio de CMG de los nodos del SEN, excluyendo P.MONTT (otro sistema)."""
    vals = [r.get("cmg_usd_mwh") for r in cmg_rows
            if r.get("nodo") != "P.MONTT_______220" and r.get("cmg_usd_mwh") is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


# ── Sidebar ────────────────────────────────────────────────────────────────────

def _fmt_hora(ts: str | None) -> str:
    """Formatea timestamp 'YYYY-MM-DD HH:MM:SS' como 'DD/MM HH:MM'."""
    if not ts:
        return "—"
    try:
        return ts[8:10] + "/" + ts[5:7] + " " + ts[11:16]
    except Exception:
        return "—"


def _estado_fuente(ts: str | None, horas_max: float = 12.0) -> str:
    """Devuelve 'ok' si la fuente tiene datos recientes (<= horas_max), si no 'bad'.

    Sirve como semáforo de conexión: verde palpitante = datos fluyendo en el cron.
    """
    if not ts:
        return "bad"
    try:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        dt = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
        ahora = datetime.now(ZoneInfo("America/Santiago")).replace(tzinfo=None)
        return "ok" if (ahora - dt) <= timedelta(hours=horas_max) else "bad"
    except Exception:
        return "bad"


def _bloque_fuentes(act: dict) -> str:
    """HTML del panel 'Fuentes de datos' con semáforo de conexión palpitante."""
    fuentes = [
        ("Gen. real CEN",   act.get("gen_real"), 12.0),
        ("PCP programada",  act.get("gen_prog"), 24.0),
        ("Meteo Open-Meteo", act.get("meteo"),   12.0),
        ("CMG CEN S3",      act.get("cmg"),       6.0),
        ("NASA POWER",      act.get("nasa"),    2400.0),   # rezago ~85 días (validación solar)
    ]
    # NASA POWER tiene rezago de ~2-3 meses (validación, no tiempo real) → no cuenta para
    # el semáforo global de conexión, pero sí se muestra su fila/estado.
    _sin_health = {"NASA POWER"}
    filas = ""
    n_ok = 0
    n_health = 0
    for label, ts, hmax in fuentes:
        estado = _estado_fuente(ts, hmax)
        if label not in _sin_health:
            n_health += 1
            if estado == "ok":
                n_ok += 1
        filas += (
            f"<div style='display:flex;align-items:center;margin-bottom:7px'>"
            f"<span class='status-dot {estado}'></span>"
            f"<span style='font-size:11px;color:rgba(255,255,255,0.80)'>{label}</span>"
            f"<span style='margin-left:auto;font-size:10px;color:rgba(255,255,255,0.50)'>"
            f"{_fmt_hora(ts)}</span></div>"
        )
    estado_global = "Conectado" if n_ok == n_health else (
        "Parcial" if n_ok > 0 else "Sin conexion")
    color_global = "#5AB848" if n_ok == n_health else ("#F59E0B" if n_ok else "#EF4444")
    return (
        f"<div style='padding:12px 14px;background:rgba(255,255,255,0.07);"
        f"border-radius:8px;border:1px solid rgba(255,255,255,0.12);margin-bottom:6px'>"
        f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:10px'>"
        f"<span style='font-size:10px;font-weight:700;color:{AES_CYAN};text-transform:uppercase;"
        f"letter-spacing:1px'>Fuentes de datos</span>"
        f"<span style='font-size:9px;font-weight:700;color:{color_global};text-transform:uppercase;"
        f"letter-spacing:0.5px'>{estado_global}</span></div>"
        f"{filas}</div>"
    )


def render_sidebar(gen_por_parque: dict[str, float | None], actualizaciones: dict | None = None,
                   bess_rows: list | None = None) -> str:
    # None = ningún parque seleccionado explícitamente → el mapa muestra Chile completo
    parque_activo = st.session_state.get("parque_activo", None)

    with st.sidebar:
        # Header premium — logo Pulsar con fondo blanco eliminado via PIL
        _logo_path = "assets/logo_pulsar.png"
        if os.path.exists(_logo_path):
            import base64 as _b64
            import io as _io
            from PIL import Image as _PILImage
            import numpy as _np

            # El PNG trae el logo blanco con el patrón de transparencia (checkerboard)
            # horneado como píxeles: fondo 242-249, logo blanco 251-255. Se keyea por
            # luminancia con corte en 251 → fondo totalmente transparente, logo en blanco.
            _img = _PILImage.open(_logo_path).convert("RGB")
            _arr = _np.array(_img, dtype=_np.float32)
            _bright = _arr.mean(axis=2)
            _alpha = _np.clip((_bright - 251.0) * 80, 0, 255).astype(_np.uint8)
            _rgba = _np.zeros((_arr.shape[0], _arr.shape[1], 4), dtype=_np.uint8)
            _rgba[:, :, :3] = 255
            _rgba[:, :, 3] = _alpha
            _out = _PILImage.fromarray(_rgba, "RGBA").resize((420, 420), _PILImage.LANCZOS)
            _buf = _io.BytesIO()
            _out.save(_buf, format="PNG")
            _logo_b64 = _b64.b64encode(_buf.getvalue()).decode()

            st.markdown(
                f"<div style='padding:2px 4px 6px;text-align:center'>"
                f"<img src='data:image/png;base64,{_logo_b64}' "
                f"style='width:210px;display:block;margin:0 auto;' />"
                f"<div style='display:inline-block;margin-top:6px;padding:1px 9px;border-radius:10px;"
                f"background:rgba(77,200,220,0.18);border:1px solid rgba(77,200,220,0.35);"
                f"font-size:10px;font-weight:700;letter-spacing:0.5px;color:#4DC8DC'>{APP_VERSION}</div>"
                f"<div style='font-size:11px;color:rgba(255,255,255,0.55);margin-top:6px'>"
                f"Creado por <b style='color:rgba(255,255,255,0.80)'>Erick Herrera</b></div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='padding:16px 4px 12px;text-align:center'>"
                f"<div style='font-size:22px;font-weight:800;color:white;letter-spacing:-0.5px'>Pulsar</div>"
                f"<div style='display:inline-block;margin-top:6px;padding:1px 9px;border-radius:10px;"
                f"background:rgba(77,200,220,0.18);border:1px solid rgba(77,200,220,0.35);"
                f"font-size:10px;font-weight:700;letter-spacing:0.5px;color:#4DC8DC'>{APP_VERSION}</div>"
                f"<div style='font-size:11px;color:rgba(255,255,255,0.55);margin-top:6px'>"
                f"Creado por <b style='color:rgba(255,255,255,0.80)'>Erick Herrera</b></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Fuentes de datos — semáforo de conexión palpitante, en la parte alta
        st.markdown(_bloque_fuentes(actualizaciones or {}), unsafe_allow_html=True)

        st.divider()

        # Parques solares
        st.markdown(
            f"<div style='font-size:10px;font-weight:700;color:{AES_CYAN};text-transform:uppercase;"
            f"letter-spacing:1.2px;margin-bottom:8px;padding-left:2px'>Solar FV</div>",
            unsafe_allow_html=True,
        )
        for p in PARQUES_SOLAR:
            gen = gen_por_parque.get(p)
            gen_str = f"{gen:.1f} MW" if gen is not None else "— MW"
            fp = round(gen / PMAX_FP[p] * 100, 0) if gen and PMAX_FP[p] > 0 else None
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
                    st.session_state["vista"] = "Parques"
                    st.session_state["_parque_tec"] = "Solar"   # fuerza el toggle de tecnología
                    st.session_state["_sync_parque"] = p   # one-shot: fuerza el selectbox una vez
                    st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Parques eólicos
        st.markdown(
            f"<div style='font-size:10px;font-weight:700;color:{AES_CYAN};text-transform:uppercase;"
            f"letter-spacing:1.2px;margin-bottom:8px;padding-left:2px;margin-top:4px'>Eólica</div>",
            unsafe_allow_html=True,
        )
        for p in PARQUES_EOLICA:
            gen = gen_por_parque.get(p)
            gen_str = f"{gen:.1f} MW" if gen is not None else "— MW"
            fp = round(gen / PMAX_FP[p] * 100, 0) if gen and PMAX_FP[p] > 0 else None
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
                st.session_state["vista"] = "Parques"
                st.session_state["_parque_tec"] = "Eólica"   # fuerza el toggle de tecnología
                st.session_state["_sync_parque"] = p   # one-shot: fuerza el selectbox una vez
                st.rerun()

        # ── BESS (almacenamiento) ──
        from config import BESS as _BESS_CFG
        _bess_net = {}
        if bess_rows:
            import pandas as _pd
            _bdf = _pd.DataFrame(bess_rows)
            if not _bdf.empty and "bess" in _bdf.columns:
                _bdf["fecha_hora"] = _pd.to_datetime(_bdf["fecha_hora"])
                _ult = _bdf.sort_values("fecha_hora").drop_duplicates("bess", keep="last")
                _bess_net = dict(zip(_ult["bess"], _ult["potencia_neta_mw"]))

        st.markdown(
            f"<div style='font-size:10px;font-weight:700;color:{AES_CYAN};text-transform:uppercase;"
            f"letter-spacing:1.2px;margin:12px 0 8px;padding-left:2px'>BESS · Almacenamiento</div>",
            unsafe_allow_html=True,
        )
        for cod, b in _BESS_CFG.items():
            neta = _bess_net.get(cod)
            if neta is None:
                estado_str = "— MW"
            elif neta > 1:
                estado_str = f"▲ {neta:.0f} MW desc."
            elif neta < -1:
                estado_str = f"▼ {abs(neta):.0f} MW carga"
            else:
                estado_str = "reposo"
            if st.button(f"{b['nombre'].replace('BESS ', '')}  ·  {estado_str}",
                         key=f"btn_bess_{cod}", use_container_width=True):
                st.session_state["vista"] = "BESS"
                st.session_state["_force_cat"] = "Operación"
                st.rerun()

        st.divider()

        # Acciones
        if st.button("Actualizar datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.caption("El reporte PDF está en Referencia → Reportes.")


    return st.session_state.get("parque_activo", None)


# ── Navegación principal (vista única) ──────────────────────────────────────────

# Navegación en 2 niveles: categorías → vistas. Reduce el desorden de tener
# muchos botones sueltos. La categoría activa se deriva de la vista activa y
# se puede cambiar con las pestañas-categoría (animación fadeInUp en los botones).
CATEGORIAS = {
    "Operación":         ["Mapa & Resumen", "Parques", "BESS"],
    "Análisis":          ["Forecast 7d", "Estadisticas", "ML Analysis"],
    "Mercado & Alertas": ["Mercado & Sistema", "Alertas"],
    "Referencia":        ["Referencia"],
}
VISTAS = [v for grupo in CATEGORIAS.values() for v in grupo]


def _categoria_de(vista: str) -> str:
    for cat, vistas in CATEGORIAS.items():
        if vista in vistas:
            return cat
    return next(iter(CATEGORIAS))


def _navegacion() -> str:
    """Navegación tipo barra de menú de escritorio. Devuelve la vista activa.

    Cada categoría es un `st.popover` a todo el ancho que se despliega hacia abajo
    mostrando sus vistas como botones (primary = vista activa). La categoría activa
    muestra inline la vista seleccionada. Patrón replicado del dashboard CTM
    (ver CLAUDE.md — Sesión 21). Usa la variable de estado normal `vista` (no key de
    widget) para que el sidebar pueda forzar la vista escribiendo en session_state.
    """
    vista = st.session_state.get("vista", VISTAS[0])
    if vista not in VISTAS:
        vista = VISTAS[0]

    # `_force_cat` quedó obsoleto: la categoría activa se deriva de la vista. Se
    # consume para limpiar estado heredado de la navegación de 2 niveles anterior.
    st.session_state.pop("_force_cat", None)
    st.session_state.pop("nav_cat", None)

    st.markdown("<div class='menubar'>", unsafe_allow_html=True)
    cols = st.columns(len(CATEGORIAS))
    for col, (cat, vistas_cat) in zip(cols, CATEGORIAS.items()):
        with col:
            activa = vista in vistas_cat
            etiqueta = f"{cat}  ·  {vista}" if (activa and vista != cat) else cat
            with st.popover(etiqueta, use_container_width=True):
                for v in vistas_cat:
                    if st.button(
                        v, key=f"nav_{v}", use_container_width=True,
                        type="primary" if v == vista else "secondary",
                    ):
                        st.session_state["vista"] = v
                        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    return vista


# ── Layout principal ──────────────────────────────────────────────────────────

def _logo_keyed_html(color: tuple[int, int, int] = (255, 255, 255), width_px: int = 150) -> str | None:
    """Devuelve un <img> base64 del logo Pulsar con el fondo (checkerboard horneado)
    eliminado por key de luminancia y recoloreado al `color` indicado. El PNG entregado
    viene flatten en RGB: fondo 242–249, logo blanco 251–255 (ver CLAUDE.md Sesión 16)."""
    path = "assets/logo_pulsar.png"
    if not os.path.exists(path):
        return None
    try:
        import base64 as _b64, io as _io
        from PIL import Image as _PILImage
        import numpy as _np
        img = _PILImage.open(path).convert("RGB")
        arr = _np.asarray(img).astype(_np.float32)
        bright = arr.mean(axis=2)
        alpha = _np.clip((bright - 251.0) * 80.0, 0, 255).astype(_np.uint8)
        r, g, b = color
        rgba = _np.zeros((*alpha.shape, 4), dtype=_np.uint8)
        rgba[..., 0] = r; rgba[..., 1] = g; rgba[..., 2] = b; rgba[..., 3] = alpha
        out = _PILImage.fromarray(rgba, "RGBA")
        w, h = out.size
        out = out.resize((width_px, int(h * width_px / w)), _PILImage.LANCZOS)
        buf = _io.BytesIO()
        out.save(buf, format="PNG")
        b64 = _b64.b64encode(buf.getvalue()).decode()
        return f"<img src='data:image/png;base64,{b64}' width='{width_px}' style='display:inline-block'/>"
    except Exception:
        return None


def _password_correcto() -> bool:
    """Gate de acceso con contraseña compartida (pass en st.secrets o fallback 'carbon')."""
    if st.session_state.get("_auth_ok"):
        return True

    try:
        esperado = st.secrets.get("APP_PASSWORD") or os.environ.get("APP_PASSWORD") or "carbon"
    except Exception:
        esperado = os.environ.get("APP_PASSWORD") or "carbon"

    # Pantalla de login centrada con el logo (keyed a negro sobre fondo transparente)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
        logo_html = _logo_keyed_html(color=(26, 31, 54), width_px=150)  # AES_TEXTO ~ negro azulado
        if logo_html:
            st.markdown(
                f"<div style='text-align:center;margin-bottom:6px'>{logo_html}</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<h2 style='color:{AES_TEXTO};font-weight:800;margin:4px 0 2px 0;text-align:center'>Pulsar — AES Andes</h2>"
            f"<p style='color:{AES_MUTED};font-size:13px;margin:0 0 16px 0;text-align:center'>Ingresa la contraseña para acceder al dashboard.</p>",
            unsafe_allow_html=True,
        )
        pwd = st.text_input("Contraseña", type="password", key="_pwd_input",
                            label_visibility="collapsed", placeholder="Contraseña")
        if st.button("Ingresar", type="primary", use_container_width=True):
            if pwd == esperado:
                st.session_state["_auth_ok"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    return False


def main():

    if not _password_correcto():
        st.stop()

    with st.spinner("Cargando datos..."):
        try:
            gen_rows, prog_rows, bess_rows, cmg_rows, lim_rows, ultima_hora, actualizaciones = cargar_datos()
        except Exception as e:
            st.error(f"Error al conectar con Supabase: {e}")
            st.stop()

    gen_por_parque  = ultima_gen_por_parque(gen_rows)
    prog_por_parque = ultima_prog_por_parque(prog_rows)
    cmg_val         = cmg_crucero(cmg_rows)
    n_lim           = len(lim_rows)
    cmg_idx         = {r["nodo"]: r.get("cmg_usd_mwh") for r in cmg_rows}
    cmg_por_parque  = {p: cmg_idx.get(CMG_NODO.get(p)) for p in PARQUES_TODOS}

    cmg_prom = cmg_promedio_sen(cmg_rows)

    # Generación PDF
    if st.session_state.pop("generar_pdf", False):
        from utils.insights import evaluar_insights
        from utils.pdf_report import generar_pdf
        from utils.recomendaciones import generar_recomendaciones
        with st.spinner("Generando PDF..."):
            insights = evaluar_insights(gen_por_parque, prog_por_parque, cmg_val, lim_rows)
            insights = [i for i in insights if i.categoria != "limitacion"]
            recs = generar_recomendaciones(gen_por_parque, prog_por_parque, cmg_por_parque,
                                           cmg_prom, bess_rows, lim_rows)
            pdf_bytes = generar_pdf(
                gen_por_parque=gen_por_parque,
                prog_por_parque=prog_por_parque,
                cmg_crucero=cmg_val,
                cmg_por_parque=cmg_por_parque,
                n_limitaciones=n_lim,
                insights=insights,
                ultima_hora=ultima_hora,
                bess_rows=bess_rows,
                recomendaciones=recs,
                cmg_promedio=cmg_prom,
            )
            st.session_state["pdf_bytes"] = pdf_bytes
        st.rerun()

    parque_activo = render_sidebar(gen_por_parque, actualizaciones, bess_rows=bess_rows)

    # Header
    st.markdown(
        f"<h1 style='font-size:30px;font-weight:800;color:{AES_TEXTO};margin:0 0 8px 0;letter-spacing:-0.5px'>"
        f"Pulsar — AES Andes</h1>",
        unsafe_allow_html=True,
    )

    render_kpis(
        gen_por_parque=gen_por_parque,
        prog_por_parque=prog_por_parque,
        cmg_crucero=cmg_val,
        n_limitaciones_activas=n_lim,
        ultima_hora=ultima_hora,
        cmg_rows=cmg_rows,
        bess_rows=bess_rows,
    )

    st.divider()

    # ── Navegación de vista única ────────────────────────────────────────────
    # Se renderiza SOLO la vista activa. Esto evita el bug de Plotly dentro de
    # st.tabs: los paneles de tabs inactivos quedan con display:none, el gráfico
    # se inicializa midiendo ancho 0 y aparece comprimido hasta el siguiente
    # rerun. Con vista única el gráfico siempre se monta visible y a ancho real.
    vista = _navegacion()
    parque_tec = TECNOLOGIA.get(parque_activo, "Solar") if parque_activo else None

    if vista == "Mapa & Resumen":
        _render_tab_resumen(gen_por_parque, gen_rows, prog_rows, parque_activo, bess_rows)
    elif vista == "Parques":
        _render_parques(gen_por_parque, prog_por_parque, gen_rows, prog_rows,
                        parque_activo, parque_tec)
    elif vista == "BESS":
        render_tab_bess(bess_rows)
    elif vista == "Forecast 7d":
        render_tab_forecast()
    elif vista == "Estadisticas":
        render_tab_estadisticas(gen_rows=gen_rows, prog_rows=prog_rows, cmg_rows=cmg_rows,
                                 bess_rows=bess_rows)
    elif vista == "ML Analysis":
        render_tab_ml()
    elif vista == "Mercado & Sistema":
        _render_mercado_sistema(cmg_rows, lim_rows)
    elif vista == "Alertas":
        _render_alertas(gen_por_parque, prog_por_parque, cmg_val, lim_rows, ultima_hora,
                        cmg_por_parque, cmg_prom, bess_rows)
    elif vista == "Referencia":
        _render_referencia()


# ── Vistas-contenedor (agrupan sub-secciones con un selector interno) ───────────
# Se usa st.radio (no st.tabs) para la sub-navegación: st.tabs deja los paneles
# inactivos con display:none y los gráficos Plotly se inicializan con ancho 0.

def _render_parques(gen_por_parque, prog_por_parque, gen_rows, prog_rows,
                    parque_activo, parque_tec):
    # El sidebar puede forzar la tecnología (one-shot) al saltar a un parque.
    forzada = st.session_state.pop("_parque_tec", None)
    if forzada in ("Solar", "Eólica"):
        st.session_state["parques_tec"] = forzada
    elif "parques_tec" not in st.session_state:
        st.session_state["parques_tec"] = parque_tec if parque_tec in ("Solar", "Eólica") else "Solar"

    tec = st.radio("Tecnología", ["Solar", "Eólica"], horizontal=True,
                   key="parques_tec", label_visibility="collapsed")
    if tec == "Solar":
        solar_activo = parque_activo if parque_tec == "Solar" else None
        render_tab_solar(gen_por_parque, prog_por_parque, gen_rows, prog_rows, solar_activo)
    else:
        eolica_activo = parque_activo if parque_tec == "Eólica" else None
        render_tab_eolica(gen_por_parque, prog_por_parque, gen_rows, prog_rows, eolica_activo)


def _render_mercado_sistema(cmg_rows, lim_rows):
    sub = st.radio("Sección", ["CMG", "Limitaciones", "Meteo & Sistema"],
                   horizontal=True, key="mercado_sub", label_visibility="collapsed")
    if sub == "CMG":
        _render_tab_cmg(cmg_rows)
    elif sub == "Limitaciones":
        _render_tab_limitaciones(lim_rows)
    else:
        render_tab_meteo_sistema(cmg_rows)


def _render_alertas(gen_por_parque, prog_por_parque, cmg_val, lim_rows, ultima_hora,
                    cmg_por_parque, cmg_prom, bess_rows):
    sub = st.radio("Sección", ["Alarmas automáticas", "Recomendaciones"],
                   horizontal=True, key="alertas_sub", label_visibility="collapsed")
    if sub == "Alarmas automáticas":
        render_tab_insights(
            gen_por_parque=gen_por_parque,
            prog_por_parque=prog_por_parque,
            cmg_crucero=cmg_val,
            lim_rows=lim_rows,
            ultima_hora=ultima_hora,
        )
    else:
        _render_tab_recomendaciones(gen_por_parque, prog_por_parque, cmg_por_parque,
                                    cmg_prom, bess_rows, lim_rows)


def _render_referencia():
    sub = st.radio("Sección", ["Infotécnica", "Glosario"],
                   horizontal=True, key="referencia_sub", label_visibility="collapsed")
    if sub == "Infotécnica":
        render_tab_infotecnica()
    else:
        from components.tab_glosario import render_tab_glosario
        render_tab_glosario()


# ── Referencia: Recomendaciones ─────────────────────────────────────────────────

_REC_COLOR = {"alta": AES_ROJO, "media": AES_AMBAR, "baja": AES_VERDE}
_REC_BG    = {"alta": "#FEF2F2", "media": "#FFFBEB", "baja": "#F0FDF4"}
_REC_LABEL = {"alta": "Prioridad alta", "media": "Prioridad media", "baja": "Informativo"}
_REC_HORIZ = {"ahora": "Ahora", "corto": "Corto plazo", "futuro": "A futuro"}


def _render_tab_recomendaciones(gen_por_parque, prog_por_parque, cmg_por_parque,
                                cmg_prom, bess_rows, lim_rows):
    from utils.recomendaciones import generar_recomendaciones

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:4px'>"
        f"Recomendaciones operacionales</div>"
        f"<div style='font-size:11.5px;color:{AES_MUTED};margin-bottom:14px'>"
        f"Acciones sugeridas a partir del estado actual del portfolio (generación, desvíos, "
        f"CMG, BESS y limitaciones). Orientan decisiones de ahora y a futuro.</div>",
        unsafe_allow_html=True,
    )

    recs = generar_recomendaciones(gen_por_parque, prog_por_parque, cmg_por_parque,
                                   cmg_prom, bess_rows, lim_rows)

    n_alta = sum(1 for r in recs if r.prioridad == "alta")
    n_media = sum(1 for r in recs if r.prioridad == "media")
    c1, c2, c3 = st.columns(3)
    c1.metric("Prioridad alta", n_alta)
    c2.metric("Prioridad media", n_media)
    c3.metric("Total recomendaciones", len(recs))

    for r in recs:
        col = _REC_COLOR.get(r.prioridad, AES_MUTED)
        bg  = _REC_BG.get(r.prioridad, AES_GRIS)
        st.markdown(
            f"<div style='background:{bg};border-left:4px solid {col};border-radius:0 10px 10px 0;"
            f"border:1px solid {col}33;border-left-color:{col};padding:14px 18px;margin-bottom:10px'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px'>"
            f"<span style='font-size:13px;font-weight:700;color:{AES_TEXTO}'>{r.titulo}</span>"
            f"<span style='font-size:10px;font-weight:700;color:{col};text-transform:uppercase;"
            f"letter-spacing:0.6px'>{_REC_LABEL.get(r.prioridad,'')} · {_REC_HORIZ.get(r.horizonte,'')}</span>"
            f"</div>"
            f"<div style='font-size:12px;color:{AES_MUTED};line-height:1.6'>{r.detalle}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_tab_reportes():
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:4px'>"
        f"Reporte PDF del portfolio</div>"
        f"<div style='font-size:11.5px;color:{AES_MUTED};margin-bottom:14px'>"
        f"Documento operacional con resumen ejecutivo, estado por parque, BESS, "
        f"recomendaciones y alarmas automáticas. Se genera en el momento con los datos actuales.</div>",
        unsafe_allow_html=True,
    )

    if st.button("Generar reporte PDF", type="primary", key="btn_pdf_ref"):
        st.session_state["generar_pdf"] = True
        st.rerun()

    if st.session_state.get("pdf_bytes"):
        import datetime as _dt
        st.success("Reporte generado. Descárgalo a continuación.")
        st.download_button(
            label="Descargar reporte PDF",
            data=st.session_state["pdf_bytes"],
            file_name=f"reporte_pulsar_{_dt.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
        )


# ── Tab Resumen ───────────────────────────────────────────────────────────────

def _render_tab_resumen(gen_por_parque, gen_rows, prog_rows, parque_activo=None, bess_rows=None):
    import plotly.graph_objects as go
    import pandas as pd

    # ── Mapa satelital a ancho completo ──────────────────────────────────────
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
        f"Generacion actual por parque</div>",
        unsafe_allow_html=True,
    )
    render_mapa(gen_por_parque, parque_activo=parque_activo)

    # ── Tabla de estado del portfolio, debajo del mapa y con más valor ───────
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:14px 0 8px'>"
        f"Estado del portfolio — por parque</div>",
        unsafe_allow_html=True,
    )
    prog_por_parque = ultima_prog_por_parque(prog_rows) if prog_rows else {}
    filas = []
    for p in PARQUES_TODOS:
        gen  = gen_por_parque.get(p)
        prog = prog_por_parque.get(p)
        pmax = PMAX_FP[p]
        fp   = round(gen / pmax * 100, 1) if gen is not None and pmax > 0 else None
        usocap = round(gen / pmax * 100, 0) if gen is not None and pmax > 0 else None
        dev = calcular_desvio(gen, prog)
        filas.append({
            "Parque":       NOMBRE_DISPLAY[p],
            "Tipo":         TECNOLOGIA[p],
            "Gen. MW":      round(gen, 1) if gen is not None else None,
            "Pmax neta MW": round(pmax, 1),
            "FP %":         fp,
            "% capacidad":  usocap,
            "PCP MW":       round(prog, 1) if prog is not None else None,
            "Desvío %":     dev["desvio_pct"],
        })
    df_estado = pd.DataFrame(filas)
    st.dataframe(
        df_estado, hide_index=True, use_container_width=True,
        column_config={
            "% capacidad": st.column_config.ProgressColumn(
                "% capacidad", min_value=0, max_value=100, format="%d%%"),
            "FP %": st.column_config.NumberColumn("FP %", format="%.1f"),
            "Desvío %": st.column_config.NumberColumn("Desvío %", format="%+.1f"),
        },
    )
    st.caption(
        "FP = gen / Pmax neta CEN. % capacidad = uso instantáneo sobre la Pmax neta. "
        "Desvío = (gen − PCP)/PCP de la misma hora; verde ≤15%, ámbar ≤25%, rojo >25%."
    )

    # ── Serie de tiempo 24h: total + desglose por tecnología (apilado) ───────
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:16px 0 8px'>"
        f"Generacion del portfolio — ultimas 24 horas</div>",
        unsafe_allow_html=True,
    )
    if not gen_rows:
        st.info("Sin datos de generacion en las ultimas 24 horas.")
        return

    df_gen = pd.DataFrame(gen_rows)
    df_gen["fecha_hora"] = pd.to_datetime(df_gen["fecha_hora"])
    win_max = df_gen["fecha_hora"].max()
    win_min = win_max - pd.Timedelta(hours=24)
    df_gen = df_gen[df_gen["fecha_hora"] >= win_min].copy()
    df_gen["tec"] = df_gen["parque"].map(TECNOLOGIA)
    piv = df_gen.pivot_table(index="fecha_hora", columns="tec", values="gen_real_mw",
                             aggfunc="sum").reset_index()
    for col in ("Solar", "Eólica"):
        if col not in piv.columns:
            piv[col] = 0.0
    piv["Total"] = piv["Solar"].fillna(0) + piv["Eólica"].fillna(0)

    if prog_rows:
        # La programación se publica hacia el futuro; se alinea a la MISMA ventana del
        # gráfico de generación (no a su propio máximo) para que aparezca completa.
        # PCP y PID se suman por separado para no duplicar el total del portfolio.
        df_prog = pd.DataFrame(prog_rows)
        df_prog["fecha_hora"] = pd.to_datetime(df_prog["fecha_hora"])
        df_prog = df_prog[(df_prog["fecha_hora"] >= win_min) & (df_prog["fecha_hora"] <= win_max)]
        if "fuente" not in df_prog.columns:
            df_prog["fuente"] = "CEN_PCP"
        df_pcp_t = (df_prog[df_prog["fuente"] == "CEN_PCP"]
                    .groupby("fecha_hora")["gen_programada_mw"].sum().reset_index()
                    .rename(columns={"gen_programada_mw": "Programada"}))
        df_pid_t = (df_prog[df_prog["fuente"] == "CEN_PID"]
                    .groupby("fecha_hora")["gen_programada_mw"].sum().reset_index()
                    .rename(columns={"gen_programada_mw": "Programada_PID"}))
        if not df_pcp_t.empty:
            piv = piv.merge(df_pcp_t, on="fecha_hora", how="left")
        if not df_pid_t.empty:
            piv = piv.merge(df_pid_t, on="fecha_hora", how="left")
        piv = piv.sort_values("fecha_hora")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=piv["fecha_hora"], y=piv["Solar"], name="Solar FV", stackgroup="gen",
        line=dict(color=AES_AZUL, width=0.5), fillcolor="rgba(59,76,232,0.55)",
        hovertemplate="%{y:.1f} MW<extra>Solar FV</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=piv["fecha_hora"], y=piv["Eólica"], name="Eólica", stackgroup="gen",
        line=dict(color=AES_CYAN, width=0.5), fillcolor="rgba(77,200,220,0.55)",
        hovertemplate="%{y:.1f} MW<extra>Eólica</extra>",
    ))
    # BESS: potencia neta del portfolio por hora (>0 descarga = inyecta, <0 carga =
    # consume). Plotly apila lo positivo sobre la generación y lo negativo bajo cero.
    if bess_rows:
        df_bess = pd.DataFrame(bess_rows)
        if not df_bess.empty and "potencia_neta_mw" in df_bess.columns:
            df_bess["fecha_hora"] = pd.to_datetime(df_bess["fecha_hora"])
            df_bess = df_bess[(df_bess["fecha_hora"] >= win_min) & (df_bess["fecha_hora"] <= win_max)]
            bess_t = (df_bess.groupby("fecha_hora")["potencia_neta_mw"].sum()
                      .reset_index().rename(columns={"potencia_neta_mw": "BESS"}))
            if not bess_t.empty:
                piv = piv.merge(bess_t, on="fecha_hora", how="left").sort_values("fecha_hora")
                piv["BESS"] = piv["BESS"].fillna(0.0)
                fig.add_trace(go.Scatter(
                    x=piv["fecha_hora"], y=piv["BESS"], name="BESS (neto)", stackgroup="gen",
                    line=dict(color=AES_VIOLETA, width=0.5), fillcolor="rgba(155,111,212,0.55)",
                    hovertemplate="%{y:.1f} MW<extra>BESS neto (+ descarga / − carga)</extra>",
                ))
    if "Programada" in piv.columns:
        fig.add_trace(go.Scatter(
            x=piv["fecha_hora"], y=piv["Programada"],
            name="Programada PCP", line=dict(color=AES_AMBAR, width=1.8, dash="dash"),
            hovertemplate="%{y:.1f} MW<extra>Programada PCP (diario D-1)</extra>",
        ))
    if "Programada_PID" in piv.columns:
        fig.add_trace(go.Scatter(
            x=piv["fecha_hora"], y=piv["Programada_PID"],
            name="Programada PID", line=dict(color=AES_VERDE, width=1.6, dash="dot"),
            hovertemplate="%{y:.1f} MW<extra>Programada PID (reprograma intra-día)</extra>",
        ))
    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
        xaxis_title=None, yaxis_title="MW", legend_title=None,
        height=320, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key="mapa_grafico_tendencia")
    st.caption("Área apilada = aporte de Solar FV, Eólica y BESS a la generación total "
               "(BESS neto: positivo = descarga inyectando, negativo = carga bajo cero); "
               "línea ámbar = programa PCP (diario D-1) y línea verde punteada = "
               "programa PID (reprograma intra-día) del CEN para el portfolio.")


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


def _render_tab_cmg(cmg_rows):
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
    from components.demanda import render_demanda_zonas
    render_demanda_zonas(horas=48, key="cmg")


# ── Tab Limitaciones ──────────────────────────────────────────────────────────

def _render_tab_limitaciones(lim_rows):
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


if __name__ == "__main__":
    main()
