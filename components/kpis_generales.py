"""KPIs generales del portfolio ERNC — tema claro, paleta AES, tooltips explicativos."""
import streamlit as st

from config import (
    PMAX_TOTAL, PMAX_TOTAL_SOLAR, PMAX_TOTAL_EOLICA,
    PARQUES_SOLAR, PARQUES_EOLICA,
)
from utils.calculos import calcular_factor_planta, calcular_desvio

# Paleta AES
AES_AZUL    = "#3B4CE8"
AES_CYAN    = "#4DC8DC"
AES_VIOLETA = "#9B6FD4"
AES_VERDE   = "#5AB848"
AES_ROJO    = "#EF4444"
AES_AMBAR   = "#F59E0B"
AES_MUTED   = "#6B7280"
AES_TEXTO   = "#1A1F36"

_SEM_COLOR = {"verde": AES_VERDE, "amarillo": AES_AMBAR, "rojo": AES_ROJO}


def render_kpis(
    gen_por_parque: dict,
    prog_por_parque: dict,
    cmg_crucero: float | None,
    n_limitaciones_activas: int,
    ultima_hora: str | None,
) -> None:
    gen_total  = sum(v for v in gen_por_parque.values() if v is not None)
    gen_solar  = sum(gen_por_parque.get(p) or 0 for p in PARQUES_SOLAR)
    gen_eolica = sum(gen_por_parque.get(p) or 0 for p in PARQUES_EOLICA)
    prog_total = sum(v for v in prog_por_parque.values() if v is not None)

    fp_total   = calcular_factor_planta(gen_total,  PMAX_TOTAL)
    fp_solar   = calcular_factor_planta(gen_solar,  PMAX_TOTAL_SOLAR)
    fp_eolica  = calcular_factor_planta(gen_eolica, PMAX_TOTAL_EOLICA)
    desvio     = calcular_desvio(gen_total, prog_total)
    semaforo   = desvio["semaforo"]
    desvio_pct = desvio["desvio_pct"]
    ingreso    = round(gen_total * (cmg_crucero or 0) / 1000, 1) if cmg_crucero else None

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        st.metric(
            label="Generacion Total",
            value=f"{gen_total:,.1f} MW",
            delta=f"FP {fp_total:.1f}%" if fp_total else None,
            help=(
                f"Suma de generacion real de los 11 parques en la ultima hora disponible. "
                f"Cap. instalada total: {PMAX_TOTAL:,.0f} MW. "
                f"Fuente: API CEN gen-real/v3. "
                f"Ultima lectura: {ultima_hora[11:16] if ultima_hora else '—'} hrs."
            ),
        )

    with c2:
        st.metric(
            label="Solar FV",
            value=f"{gen_solar:,.1f} MW",
            delta=f"FP {fp_solar:.1f}%" if fp_solar else None,
            help=(
                f"Generacion real de los 6 parques solares FV (norte). "
                f"Cap. instalada solar: {PMAX_TOTAL_SOLAR:,.0f} MW. "
                f"Factor de planta = Gen.real / Cap.instalada x 100. "
                f"Fuente: CEN gen-real/v3, id_central por parque."
            ),
        )

    with c3:
        st.metric(
            label="Eolica",
            value=f"{gen_eolica:,.1f} MW",
            delta=f"FP {fp_eolica:.1f}%" if fp_eolica else None,
            help=(
                f"Generacion real de los 5 parques eolicos (sur). "
                f"Cap. instalada eolica: {PMAX_TOTAL_EOLICA:,.0f} MW. "
                f"Factor de planta = Gen.real / Cap.instalada x 100. "
                f"Fuente: CEN gen-real/v3."
            ),
        )

    with c4:
        dev_val = f"{desvio_pct:+.1f}%" if desvio_pct is not None else "—"
        dev_mw  = f"{desvio['desvio_mw']:+.1f} MW" if desvio["desvio_mw"] is not None else None
        color   = _SEM_COLOR.get(semaforo, AES_MUTED)
        st.metric(
            label="Desvio vs PCP",
            value=dev_val,
            delta=dev_mw,
            delta_color="normal",
            help=(
                "Desvio = (Gen.real - Gen.programada) / Gen.programada x 100. "
                "Verde: |desvio| <= 15% | Amarillo: 15-25% | Rojo: >25%. "
                "Fuente programada: CEN gen-programada-pcp/v4, llave_gen por parque."
            ),
        )
        if semaforo:
            st.markdown(
                f"<div style='width:8px;height:8px;border-radius:50%;"
                f"background:{color};margin-top:-12px;display:inline-block'></div>",
                unsafe_allow_html=True,
            )

    with c5:
        st.metric(
            label="CMG Crucero 220",
            value=f"{cmg_crucero:.1f} USD/MWh" if cmg_crucero else "—",
            delta=f"~{ingreso:.0f} kUSD/h" if ingreso else None,
            help=(
                "Costo Marginal Local del nodo CRUCERO_______220 (referencia parques solares norte). "
                "Ingreso estimado = Gen.total x CMG / 1000 (kUSD/hora). "
                "Fuente: JSON S3 Coordinador Electrico Nacional, actualiza cada ~15 min. "
                "URL: cen-template-graph-pweb-prod.s3.us-east-1.amazonaws.com"
            ),
        )

    with c6:
        lim_color = AES_ROJO if n_limitaciones_activas > 0 else AES_VERDE
        lim_delta = "activas" if n_limitaciones_activas > 0 else "sin restricciones"
        st.metric(
            label="Limitaciones",
            value=str(n_limitaciones_activas),
            delta=lim_delta,
            delta_color="inverse" if n_limitaciones_activas > 0 else "normal",
            help=(
                "Limitaciones de transmision activas que afectan al portfolio. "
                "Activa = fecha_efectiva_retorno IS NULL. "
                "Fuente: CEN limitaciones-transmision/v4, ventana 30 dias. "
                "Campo correlativo llega como float, se castea a int."
            ),
        )
