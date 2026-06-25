"""
Tab BESS — almacenamiento de AES Andes. Carga/descarga, estado de carga (SoC)
estimado, ciclos y arbitraje vs CMG del nodo del parque asociado.
Datos: tabla generacion_bess_ernc (adquisición CEN gen-real/v3).
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta, timezone

from config import BESS, BESS_HORAS, CMG_NODO

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

# Duración asumida del BESS (h) para estimar capacidad de energía a partir de Pmax.
# La API CEN no publica MWh; 4h es el estándar de los BESS solares de Chile.
# Duración por defecto (h) cuando la energía declarada (BESS_HORAS) no existe.
# La API CEN no publica los MWh reales del BESS → se asume 4 h donde falte.
_HORAS_BESS = 4.0


def _cmg_hist_nodo(nodo: str, horas: int) -> pd.DataFrame:
    try:
        from utils.db import get_client
        sb = get_client()
        santiago = timezone(timedelta(hours=-3))
        desde = (datetime.now(santiago) - timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S")
        res = (sb.table("cmg_ernc")
                 .select("fecha_hora,cmg_usd_mwh")
                 .eq("nodo", nodo)
                 .gte("fecha_hora", desde)
                 .order("fecha_hora")
                 .execute())
        if res.data:
            df = pd.DataFrame(res.data)
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"]).dt.tz_localize(None)
            return df
    except Exception:
        pass
    return pd.DataFrame()


def render_tab_bess(bess_rows: list | None = None) -> None:
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:6px'>"
        f"Sistemas de almacenamiento BESS — AES Andes</div>",
        unsafe_allow_html=True,
    )

    if not bess_rows:
        st.info(
            "Sin datos de BESS todavía. Crea la tabla con el bloque BESS de schema.sql "
            "en Supabase y ejecuta Adquisicion_ernc.py (o espera el cron). "
            "Los 5 BESS de AES (Andes Solar IIA/IIB/III/IV y Bolero) "
            "se poblarán automáticamente."
        )
        return

    df = pd.DataFrame(bess_rows)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"]).dt.tz_localize(None)

    codigos = [c for c in BESS if c in df["bess"].unique()] or list(BESS.keys())
    bess_sel = st.selectbox(
        "BESS", codigos, format_func=lambda c: BESS[c]["nombre"], key="bess_sel",
    )
    meta = BESS[bess_sel]
    pmax = meta["pmax_mw"]
    horas_bess = BESS_HORAS.get(bess_sel) or _HORAS_BESS
    cap_mwh = pmax * horas_bess

    d = df[df["bess"] == bess_sel].sort_values("fecha_hora").copy()
    if d.empty:
        st.info("Sin registros para este BESS en la ventana.")
        return

    # ── KPIs de estado ──
    ult = d.iloc[-1]
    neta = ult["potencia_neta_mw"]
    if neta > 1:
        estado, col_estado = "Descargando", AES_VERDE
    elif neta < -1:
        estado, col_estado = "Cargando", AES_AZUL
    else:
        estado, col_estado = "En reposo", AES_MUTED

    d24 = d[d["fecha_hora"] >= d["fecha_hora"].max() - pd.Timedelta(hours=24)]
    desc_mwh = d24["inyeccion_mw"].sum()
    carga_mwh = d24["retiro_mw"].sum()
    rt_efic = (desc_mwh / carga_mwh * 100) if carga_mwh > 5 else None
    ciclos = desc_mwh / cap_mwh if cap_mwh else None

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(
            f"<div style='font-size:10px;font-weight:700;color:{AES_MUTED};text-transform:uppercase'>Estado</div>"
            f"<div style='font-size:20px;font-weight:800;color:{col_estado}'>{estado}</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.metric("Potencia neta", f"{neta:+.1f} MW")
    with c3:
        st.metric("Cap. descarga", f"{pmax:.0f} MW")
    with c4:
        st.metric("Descarga 24h", f"{desc_mwh:,.0f} MWh")
    with c5:
        st.metric("Carga 24h", f"{carga_mwh:,.0f} MWh")
    with c6:
        st.metric("Ciclos eq. 24h", f"{ciclos:.2f}" if ciclos is not None else "—")
    st.caption(
        f"Potencia neta = inyección − retiro (>0 descarga, <0 carga). Capacidad de "
        f"energía estimada en {cap_mwh:.0f} MWh ({pmax:.0f} MW × {horas_bess:.1f} h "
        f"{'declaradas' if BESS_HORAS.get(bess_sel) else 'asumidas'}). "
        f"Ciclos eq. = MWh descargados / capacidad. Eficiencia ida-vuelta 24h: "
        + (f"{rt_efic:.0f}%." if rt_efic is not None else "sin carga suficiente para estimarla.")
    )

    # ── Estado de carga (SoC) estimado por integración del flujo neto ──
    # SoC sube al cargar (retiro) y baja al descargar (inyección). Se acota a [0, cap]
    # y se ancla en el mínimo de la ventana para que no derive a negativos.
    d["delta"] = d["retiro_mw"] - d["inyeccion_mw"]
    d["soc_raw"] = d["delta"].cumsum()
    d["soc"] = (d["soc_raw"] - d["soc_raw"].min()).clip(upper=cap_mwh)

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:10px 0 6px'>"
        f"Carga / descarga y estado de carga estimado — {meta['nombre']}</div>",
        unsafe_allow_html=True,
    )
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=d["fecha_hora"], y=d["inyeccion_mw"], name="Descarga (inyección)",
        marker_color=AES_VERDE, opacity=0.85,
        hovertemplate="%{y:.1f} MW<extra>Descarga</extra>",
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=d["fecha_hora"], y=-d["retiro_mw"], name="Carga (retiro)",
        marker_color=AES_AZUL, opacity=0.85,
        hovertemplate="%{y:.1f} MW<extra>Carga</extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=d["fecha_hora"], y=d["soc"], name="SoC estimado (MWh)",
        line=dict(color=AES_VIOLETA, width=2),
        hovertemplate="%{y:.0f} MWh<extra>SoC estimado</extra>",
    ), secondary_y=True)
    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
        barmode="relative", height=340, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="MW (+desc / −carga)", secondary_y=False,
                     showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(title_text="SoC (MWh)", secondary_y=True, showgrid=False,
                     range=[0, cap_mwh * 1.05])
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key=f"bess_grafico_{bess_sel}")

    # Estadísticas extra + exportación de la serie del BESS seleccionado
    e1, e2, e3, e4 = st.columns(4)
    h_desc = int((d24["inyeccion_mw"] > 0.5).sum())
    h_carga = int((d24["retiro_mw"] > 0.5).sum())
    h_reposo = int(len(d24) - h_desc - h_carga)
    with e1:
        st.metric("Máx. descarga", f"{d['inyeccion_mw'].max():.1f} MW")
    with e2:
        st.metric("Máx. carga", f"{d['retiro_mw'].max():.1f} MW")
    with e3:
        st.metric("Horas descarga / carga 24h", f"{h_desc} / {h_carga}")
    with e4:
        st.metric("Energía neta 24h", f"{desc_mwh - carga_mwh:+,.0f} MWh")

    exp = d[["fecha_hora", "inyeccion_mw", "retiro_mw", "potencia_neta_mw", "soc"]].copy()
    exp.columns = ["fecha_hora", "descarga_mw", "carga_mw", "potencia_neta_mw", "soc_estimado_mwh"]
    st.download_button(
        f"Descargar serie {meta['nombre']} (CSV)",
        data=exp.to_csv(index=False).encode("utf-8"),
        file_name=f"bess_{bess_sel}.csv", mime="text/csv", key=f"bess_csv_{bess_sel}",
    )

    # ── Resumen de todos los BESS (carga/descarga últimas 24h) ───────────────
    _resumen_todos_bess(df)

    # ── Arbitraje vs CMG del nodo del parque ──
    nodo = CMG_NODO.get(meta["parque"])
    horas_win = int((d["fecha_hora"].max() - d["fecha_hora"].min()).total_seconds() // 3600) + 6
    df_cmg = _cmg_hist_nodo(nodo, horas_win) if nodo else pd.DataFrame()
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:14px 0 6px'>"
        f"Arbitraje de energía vs CMG ({(nodo or '—').replace('_',' ').strip()})</div>",
        unsafe_allow_html=True,
    )
    if df_cmg.empty:
        st.info("Sin histórico de CMG para el nodo asociado; no se puede calcular arbitraje.")
        return

    m = d.merge(df_cmg, on="fecha_hora", how="inner")
    if m.empty:
        st.info("No hay horas con CMG y BESS coincidentes para calcular arbitraje.")
        return
    m["ingreso_desc"] = m["inyeccion_mw"] * m["cmg_usd_mwh"]
    m["costo_carga"]  = m["retiro_mw"] * m["cmg_usd_mwh"]
    m["margen"]       = m["ingreso_desc"] - m["costo_carga"]

    ingreso = m["ingreso_desc"].sum()
    costo   = m["costo_carga"].sum()
    margen  = ingreso - costo
    cmg_desc = (m["ingreso_desc"].sum() / m["inyeccion_mw"].sum()) if m["inyeccion_mw"].sum() > 0 else None
    cmg_carga = (m["costo_carga"].sum() / m["retiro_mw"].sum()) if m["retiro_mw"].sum() > 0 else None

    a1, a2, a3, a4 = st.columns(4)
    with a1:
        st.metric("Ingreso por descarga", f"{ingreso:,.0f} USD")
    with a2:
        st.metric("Costo de carga", f"{costo:,.0f} USD")
    with a3:
        st.metric("Margen de arbitraje", f"{margen:+,.0f} USD",
                  delta="favorable" if margen > 0 else "desfavorable",
                  delta_color="normal" if margen > 0 else "inverse")
    with a4:
        spread = (cmg_desc - cmg_carga) if (cmg_desc is not None and cmg_carga is not None) else None
        st.metric("Spread descarga−carga", f"{spread:+.1f} USD/MWh" if spread is not None else "—")
    st.caption(
        "Margen = Σ(descarga·CMG) − Σ(carga·CMG) hora a hora con el CMG del nodo. "
        "Un BESS rentable carga cuando el CMG es bajo (mediodía solar) y descarga "
        "cuando es alto (punta de la tarde): spread descarga−carga positivo = arbitraje exitoso."
    )


def _resumen_todos_bess(df: pd.DataFrame) -> None:
    """Tabla comparativa de los BESS: estado, carga/descarga y horas en las últimas 24h."""
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:16px 0 6px'>"
        f"Resumen de todos los BESS — últimas 24 horas</div>",
        unsafe_allow_html=True,
    )
    filas = []
    for cod, meta in BESS.items():
        d = df[df["bess"] == cod].sort_values("fecha_hora")
        if d.empty:
            filas.append({"BESS": meta["nombre"], "Parque": meta["parque"],
                          "Estado": "sin datos", "Neta MW": None, "Descarga MWh": None,
                          "Carga MWh": None, "Horas desc.": None, "Horas carga": None,
                          "Ciclos eq.": None})
            continue
        d24 = d[d["fecha_hora"] >= d["fecha_hora"].max() - pd.Timedelta(hours=24)]
        neta = float(d.iloc[-1]["potencia_neta_mw"])
        estado = "Descargando" if neta > 1 else ("Cargando" if neta < -1 else "Reposo")
        desc = float(d24["inyeccion_mw"].sum())
        carga = float(d24["retiro_mw"].sum())
        cap = meta["pmax_mw"] * (BESS_HORAS.get(cod) or _HORAS_BESS)
        filas.append({
            "BESS": meta["nombre"], "Parque": meta["parque"], "Estado": estado,
            "Neta MW": round(neta, 1), "Descarga MWh": round(desc, 0),
            "Carga MWh": round(carga, 0),
            "Horas desc.": int((d24["inyeccion_mw"] > 0.5).sum()),
            "Horas carga": int((d24["retiro_mw"] > 0.5).sum()),
            "Ciclos eq.": round(desc / cap, 2) if cap else None,
        })
    dfr = pd.DataFrame(filas)
    st.dataframe(dfr, hide_index=True, use_container_width=True)
    st.download_button(
        "Descargar resumen BESS (CSV)",
        data=dfr.to_csv(index=False).encode("utf-8"),
        file_name="bess_resumen_24h.csv", mime="text/csv", key="bess_csv_resumen",
    )
