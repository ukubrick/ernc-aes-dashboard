"""Tab Insights — tema claro, paleta AES, sin emojis."""
import streamlit as st
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

_BG     = {"critico": "#FEF2F2", "alerta": "#FFFBEB", "info": "#EFF6FF", "positivo": "#F0FDF4"}
_BORDER = {"critico": AES_ROJO,  "alerta": AES_AMBAR,  "info": AES_AZUL,  "positivo": AES_VERDE}
_LABEL  = {"critico": "CRITICO", "alerta": "ALERTA",   "info": "INFO",    "positivo": "OK"}
_DOT_C  = {"critico": AES_ROJO,  "alerta": AES_AMBAR,  "info": AES_AZUL,  "positivo": AES_VERDE}


def _card(insight: Insight, idx: int = 0) -> None:
    sev = insight.severidad
    delay = f"{idx * 0.06:.2f}s"
    dot_class = "dot-critico" if sev == "critico" else ""
    card_class = f"insight-{sev}"
    # Badge background según severidad
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


def render_tab_insights(
    gen_por_parque: dict,
    prog_por_parque: dict,
    cmg_crucero: float | None,
    lim_rows: list,
) -> None:
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
