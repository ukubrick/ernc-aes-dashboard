"""Infotécnica — ficha consolidada de parámetros técnicos por parque (referencia).

Resume parametros_pe_pulsar + parametros_pfv_pulsar (cartas CEN, 2026-06-22):
Pmax bruta/neta, mínimos técnicos, SSCC habilitados, curva de potencia eólica,
equipos principales y la regla de cálculo aplicada en Pulsar. Solo lectura.
"""
import pandas as pd
import streamlit as st

from config import (
    NOMBRE_DISPLAY, TECNOLOGIA, PARQUES_SOLAR, PARQUES_EOLICA,
    PMAX, PMAX_FP, INFOTECNICA, TURBINA_PARQUE, BESS, BESS_HORAS,
)

AES_AZUL  = "#3B4CE8"
AES_CYAN  = "#4DC8DC"
AES_MUTED = "#6B7280"
AES_TEXTO = "#1A1F36"


def _fmt(v, suf="", dec=2):
    if v is None:
        return "—"
    if isinstance(v, (int, float)):
        return f"{v:.{dec}f}{suf}"
    return f"{v}{suf}"


def _seccion_titulo(texto: str, color: str = AES_AZUL):
    st.markdown(
        f"<div style='font-size:13px;font-weight:700;color:{color};text-transform:uppercase;"
        f"letter-spacing:1px;margin:18px 0 6px 0'>{texto}</div>",
        unsafe_allow_html=True,
    )


def _tabla_potencias(parques: list[str]) -> pd.DataFrame:
    filas = []
    for p in parques:
        info = INFOTECNICA.get(p, {})
        filas.append({
            "Código": p,
            "Parque": NOMBRE_DISPLAY[p],
            "Config dashboard (MW)": _fmt(PMAX[p], dec=2),
            "Pmax bruta CEN (MW)": _fmt(info.get("pmax_bruta_mw"), dec=3),
            "Pmax neta CEN (MW)": _fmt(info.get("pmax_neta_mw"), dec=3),
            "Pmax usada FP (MW)": _fmt(PMAX_FP[p], dec=2),
            "Pmin neta (MW)": _fmt(info.get("pmin_neta_mw"), dec=3),
            "SSCC habilitados": info.get("sscc", "—"),
        })
    return pd.DataFrame(filas)


def _tabla_curva_eolica() -> pd.DataFrame:
    filas = []
    for p in PARQUES_EOLICA:
        t = TURBINA_PARQUE.get(p, {})
        modelo = t.get("modelo") or "—"
        fab = t.get("fabricante")
        if fab and t.get("modelo"):
            modelo = f"{fab} {t['modelo']}"
        n = t.get("n_wtg")
        filas.append({
            "Código": p,
            "Parque": NOMBRE_DISPLAY[p],
            "Aerogenerador": modelo,
            "N° WTG": "—" if n is None else int(n),
            "P unit (MW)": _fmt(t.get("p_unit_mw"), dec=2),
            "Rotor (m)": "—" if t.get("rotor_m") is None else int(t["rotor_m"]),
            "Hub (m)": "—" if t.get("hub_m") is None else int(t["hub_m"]),
            "Cut-in (m/s)": _fmt(t.get("v_cutin"), dec=1),
            "Rated (m/s)": _fmt(t.get("v_rated"), dec=1),
            "Cut-out (m/s)": _fmt(t.get("v_cutout"), dec=1),
        })
    return pd.DataFrame(filas)


def _tabla_bess() -> pd.DataFrame:
    filas = []
    for cod, b in BESS.items():
        h = BESS_HORAS.get(cod)
        e = round(b["pmax_mw"] * h, 1) if h else None
        filas.append({
            "Código": cod,
            "BESS": b["nombre"],
            "Parque FV": NOMBRE_DISPLAY.get(b["parque"], b["parque"]),
            "Pmax descarga (MW)": _fmt(b["pmax_mw"], dec=2),
            "Duración (h)": _fmt(h, dec=2),
            "Energía estimada (MWh)": _fmt(e, dec=1),
        })
    return pd.DataFrame(filas)


def _fichas(parques: list[str]):
    for p in parques:
        info = INFOTECNICA.get(p, {})
        with st.expander(f"{NOMBRE_DISPLAY[p]}  ({p})"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Pmax neta CEN", _fmt(info.get("pmax_neta_mw"), " MW", 2)
                      if info.get("pmax_neta_mw") is not None else "—")
            c2.metric("Pmax usada FP", f"{PMAX_FP[p]:.1f} MW")
            c3.metric("Pmin neta", _fmt(info.get("pmin_neta_mw"), " MW", 2)
                      if info.get("pmin_neta_mw") is not None else "—")
            st.markdown(f"**SSCC habilitados:** {info.get('sscc', '—')}")
            st.markdown(f"**Equipos principales:** {info.get('equipos', '—')}")
            if info.get("nota"):
                st.info(info["nota"])
            st.caption(f"Fuente: {info.get('fuente', '—')}")


def render_tab_infotecnica():
    st.markdown(
        f"<h2 style='font-size:22px;font-weight:800;color:{AES_TEXTO};margin:0 0 2px 0'>"
        f"Infotécnica de parques</h2>"
        f"<div style='font-size:12px;color:{AES_MUTED};margin-bottom:6px'>"
        f"Parámetros técnicos consolidados de las cartas CEN y fichas de fabricante "
        f"(compilado 2026-06-22). Estos valores alimentan los cálculos de factor de "
        f"planta y los modelos físicos del dashboard.</div>",
        unsafe_allow_html=True,
    )

    st.info(
        "Regla de cálculo Pulsar — Factor de planta: se prioriza **Pmax neta CEN "
        "aceptada** > potencia neta verificada SSCC > potencia total instalada "
        "documentada. La capacidad de configuración del dashboard se mantiene solo "
        "como referencia de proyecto/API, no como base del cálculo energético."
    )

    _seccion_titulo("Plantas fotovoltaicas — potencias y SSCC", AES_AZUL)
    st.dataframe(_tabla_potencias(PARQUES_SOLAR), use_container_width=True, hide_index=True)

    _seccion_titulo("Parques eólicos — potencias y SSCC", AES_CYAN)
    st.dataframe(_tabla_potencias(PARQUES_EOLICA), use_container_width=True, hide_index=True)

    _seccion_titulo("Curva de potencia eólica por parque", AES_CYAN)
    st.dataframe(_tabla_curva_eolica(), use_container_width=True, hide_index=True)
    st.caption(
        "Modelo físico: curva cúbica con cut-in → rampa hasta rated → meseta a Pmax "
        "neta → 0 sobre cut-out. Default Pulsar 3/12/25 m/s cuando no hay ficha específica."
    )

    _seccion_titulo("Sistemas de almacenamiento (BESS)", AES_AZUL)
    st.dataframe(_tabla_bess(), use_container_width=True, hide_index=True)
    st.caption(
        "Energía estimada = Pmax descarga × duración declarada. La API CEN no publica "
        "MWh; donde falta la duración se asume 4 h para SoC/ciclos."
    )

    _seccion_titulo("Fichas por parque", AES_AZUL)
    st.markdown("**Plantas fotovoltaicas**")
    _fichas(PARQUES_SOLAR)
    st.markdown("**Parques eólicos**")
    _fichas(PARQUES_EOLICA)
