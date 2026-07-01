"""Vista Mapa & Resumen — mapa satelital, tabla de estado y serie 24h del portfolio.

Extraída de app_ernc.py (Sesión 34).
"""
import streamlit as st

from config import NOMBRE_DISPLAY, TECNOLOGIA, PARQUES_TODOS, PMAX_FP
from utils.calculos import calcular_desvio
from components.mapa_ernc import render_mapa

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


def ultima_prog_por_parque(prog_rows: list[dict]) -> dict[str, float | None]:
    # Copia exacta del helper de app_ernc (evita import circular)
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


# ── Tab Resumen ───────────────────────────────────────────────────────────────

def render_tab_resumen(gen_por_parque, gen_rows, prog_rows, parque_activo=None, bess_rows=None):
    import plotly.graph_objects as go
    import pandas as pd

    # ── Mapa satelital a ancho completo ──────────────────────────────────────
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
        f"Generacion actual por parque</div>",
        unsafe_allow_html=True,
    )
    render_mapa(gen_por_parque, parque_activo=parque_activo)

    # ── Hora del último dato real por parque (gen_rows viene ordenado desc) ───
    hora_por_parque: dict[str, object] = {}
    for r in gen_rows or []:
        pq = r["parque"]
        if pq not in hora_por_parque:
            hora_por_parque[pq] = r.get("fecha_hora")

    def _fmt_hora_dato(h):
        try:
            return pd.to_datetime(h).strftime("%d/%m %H:%M")
        except Exception:
            return "—"

    # Hora más reciente del conjunto, para el título de la tabla.
    horas_validas = [pd.to_datetime(h) for h in hora_por_parque.values() if h]
    hora_max_txt = max(horas_validas).strftime("%d/%m %H:%M") if horas_validas else "—"

    # ── Tabla de estado del portfolio, debajo del mapa y con más valor ───────
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:14px 0 8px'>"
        f"Estado del portfolio — por parque · datos al {hora_max_txt} "
        f"(gen real CEN, rezago ~4-5 h)</div>",
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
            "Hora dato":    _fmt_hora_dato(hora_por_parque.get(p)),
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
        "Hora dato = última hora con gen real CEN del parque (el CEN publica con rezago "
        "de ~4-5 h, por eso no es la hora actual; algunos parques quedan en horas distintas). "
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
    # BESS: solo la potencia de DESCARGA (inyección > 0) cuenta como potencia
    # entregada al portfolio. La carga (neto < 0) consume energía y no se grafica
    # aquí — se descarta clampeando el neto a ≥ 0.
    if bess_rows:
        df_bess = pd.DataFrame(bess_rows)
        if not df_bess.empty and "potencia_neta_mw" in df_bess.columns:
            df_bess["fecha_hora"] = pd.to_datetime(df_bess["fecha_hora"])
            df_bess = df_bess[(df_bess["fecha_hora"] >= win_min) & (df_bess["fecha_hora"] <= win_max)]
            bess_t = (df_bess.groupby("fecha_hora")["potencia_neta_mw"].sum()
                      .reset_index().rename(columns={"potencia_neta_mw": "BESS"}))
            if not bess_t.empty:
                # Solo descarga: el aporte negativo (carga) se lleva a 0.
                bess_t["BESS"] = bess_t["BESS"].clip(lower=0.0)
                piv = piv.merge(bess_t, on="fecha_hora", how="left").sort_values("fecha_hora")
                piv["BESS"] = piv["BESS"].fillna(0.0)
                fig.add_trace(go.Scatter(
                    x=piv["fecha_hora"], y=piv["BESS"], name="BESS (descarga)", stackgroup="gen",
                    line=dict(color=AES_VIOLETA, width=0.5), fillcolor="rgba(155,111,212,0.55)",
                    hovertemplate="%{y:.1f} MW<extra>BESS descarga (potencia entregada)</extra>",
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
               "(BESS: solo la descarga, como potencia entregada; la carga no se grafica); "
               "línea ámbar = programa PCP (diario D-1) y línea verde punteada = "
               "programa PID (reprograma intra-día) del CEN para el portfolio.")


