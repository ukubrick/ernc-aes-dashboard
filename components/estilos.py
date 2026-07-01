"""CSS global del dashboard — tema claro con paleta AES (extraído de app_ernc, S34)."""
import streamlit as st

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


def aplicar_css() -> None:
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

