"""
Dashboard ERNC AES Andes — App principal Streamlit.
Parques: 7 solares FV (norte) + 5 eólicos (sur) + 7 BESS = ~1.657 MW instalados.
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

# ── CSS global — tema claro con paleta AES (components/estilos.py) ───────────
from components.estilos import aplicar_css
aplicar_css()


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
from components.tab_historicos import render_tab_historicos
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
                st.session_state["_force_bess"] = cod
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
    "Análisis":          ["Forecast 7d", "Estadisticas", "ML Analysis", "Históricos"],
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
    elif vista == "Históricos":
        render_tab_historicos()
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


# ── Vistas extraídas (Sesión 34) ──────────────────────────────────────────────
from components.tab_resumen import render_tab_resumen as _render_tab_resumen
from components.tab_cmg import (
    render_tab_cmg as _render_tab_cmg,
    render_tab_limitaciones as _render_tab_limitaciones,
)

if __name__ == "__main__":
    main()
