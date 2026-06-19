"""Tab Estadísticas — producción acumulada, desvío, ingresos USD, ranking FP."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config import NOMBRE_DISPLAY, PMAX, TECNOLOGIA, PARQUES_TODOS, PARQUES_SOLAR, PARQUES_EOLICA, CMG_NODO

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

_COLOR_TEC = {"Solar": AES_AZUL, "Eólica": AES_CYAN}
_SEM = {"verde": AES_VERDE, "amarillo": AES_AMBAR, "rojo": AES_ROJO}


def _sem_desvio(pct: float | None) -> str:
    if pct is None:
        return "—"
    if abs(pct) <= 15:
        return "verde"
    if abs(pct) <= 25:
        return "amarillo"
    return "rojo"


def render_tab_estadisticas(
    gen_rows: list,
    prog_rows: list,
    cmg_rows: list,
) -> None:
    if not gen_rows:
        st.info("Sin datos de generacion disponibles para calcular estadisticas.")
        return

    # ── Preparar DataFrames ──────────────────────────────────────────────────
    df_gen = pd.DataFrame(gen_rows)
    df_gen["fecha_hora"] = pd.to_datetime(df_gen["fecha_hora"])
    df_gen = df_gen.sort_values("fecha_hora")

    df_prog = pd.DataFrame(prog_rows) if prog_rows else pd.DataFrame()
    if not df_prog.empty:
        df_prog["fecha_hora"] = pd.to_datetime(df_prog["fecha_hora"])

    # Índice CMG por nodo (último valor disponible)
    cmg_idx = {r["nodo"]: r.get("cmg_usd_mwh", 0) for r in (cmg_rows or [])}

    # ── Calcular métricas por parque ────────────────────────────────────────
    filas = []
    for p in PARQUES_TODOS:
        df_p = df_gen[df_gen["parque"] == p]
        n_horas = len(df_p)
        mwh = df_p["gen_real_mw"].sum()  # 1 fila = 1 hora → MWh directos
        fp_prom = (mwh / (PMAX[p] * n_horas) * 100) if n_horas > 0 and PMAX[p] > 0 else None

        # Desvío vs PCP
        desvio_pct = None
        if not df_prog.empty:
            df_pp = df_prog[df_prog["parque"] == p]
            if not df_pp.empty:
                merged = df_p.merge(df_pp[["fecha_hora", "gen_programada_mw"]], on="fecha_hora", how="inner")
                if not merged.empty and merged["gen_programada_mw"].sum() > 0:
                    desvio_pct = (
                        (merged["gen_real_mw"].sum() - merged["gen_programada_mw"].sum())
                        / merged["gen_programada_mw"].sum() * 100
                    )

        # Ingreso estimado (MWh × CMG del nodo asignado)
        nodo = CMG_NODO.get(p)
        cmg_val = cmg_idx.get(nodo, 0) or 0
        ingreso_usd = mwh * cmg_val

        filas.append({
            "parque":      p,
            "nombre":      NOMBRE_DISPLAY[p],
            "tecnologia":  TECNOLOGIA[p],
            "pmax_mw":     PMAX[p],
            "mwh":         round(mwh, 1),
            "fp_prom":     round(fp_prom, 1) if fp_prom is not None else None,
            "desvio_pct":  round(desvio_pct, 1) if desvio_pct is not None else None,
            "ingreso_usd": round(ingreso_usd, 0),
            "n_horas":     n_horas,
        })

    df_stats = pd.DataFrame(filas)

    # ── KPIs resumen ────────────────────────────────────────────────────────
    total_mwh     = df_stats["mwh"].sum()
    solar_mwh     = df_stats[df_stats["tecnologia"] == "Solar"]["mwh"].sum()
    eolica_mwh    = df_stats[df_stats["tecnologia"] == "Eólica"]["mwh"].sum()
    total_ingreso = df_stats["ingreso_usd"].sum()
    n_horas_ref   = int(df_stats["n_horas"].max())

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:12px'>"
        f"Estadisticas del portfolio — ultimas {n_horas_ref} horas disponibles</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Produccion total", f"{total_mwh:,.0f} MWh",
                  help=f"Suma de gen_real_mw hora a hora para los 11 parques en las ultimas {n_horas_ref} horas.")
    with c2:
        st.metric("Solar FV", f"{solar_mwh:,.0f} MWh",
                  help="Produccion acumulada de los 6 parques solares en el periodo.")
    with c3:
        st.metric("Eolica", f"{eolica_mwh:,.0f} MWh",
                  help="Produccion acumulada de los 5 parques eolicos en el periodo.")
    with c4:
        st.metric("Ingreso estimado", f"USD {total_ingreso:,.0f}",
                  help="Ingreso = MWh x CMG del nodo asignado a cada parque. CMG es el ultimo valor disponible, no el historico hora a hora.")

    st.divider()

    # ── Ranking por factor de planta ────────────────────────────────────────
    col_rank, col_bar = st.columns([1, 2])

    with col_rank:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
            f"Ranking factor de planta promedio</div>",
            unsafe_allow_html=True,
        )
        df_rank = df_stats[df_stats["fp_prom"].notna()].sort_values("fp_prom", ascending=False).reset_index(drop=True)
        for i, row in df_rank.iterrows():
            color = _COLOR_TEC[row["tecnologia"]]
            fp = row["fp_prom"]
            borde = "2px solid " + color if i == 0 else f"1px solid {AES_BORDE}"
            st.markdown(
                f"<div style='display:flex;align-items:center;justify-content:space-between;"
                f"padding:6px 10px;margin-bottom:4px;border-radius:6px;"
                f"border:{borde};background:{AES_BLANCO}'>"
                f"<div>"
                f"<span style='font-size:11px;color:{AES_MUTED};margin-right:6px'>#{i+1}</span>"
                f"<span style='font-size:12px;font-weight:600;color:{AES_TEXTO}'>{row['nombre']}</span>"
                f"</div>"
                f"<span style='font-size:13px;font-weight:700;color:{color}'>{fp:.1f}%</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    with col_bar:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
            f"Produccion acumulada por parque (MWh)</div>",
            unsafe_allow_html=True,
        )
        df_bar = df_stats.sort_values("mwh", ascending=True)
        colors = [_COLOR_TEC[t] for t in df_bar["tecnologia"]]
        fig = go.Figure(go.Bar(
            x=df_bar["mwh"],
            y=df_bar["nombre"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:,.0f}" for v in df_bar["mwh"]],
            textposition="outside",
            hovertemplate="%{y}: %{x:,.0f} MWh<extra></extra>",
        ))
        fig.update_layout(
            template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
            height=340, margin=dict(l=0, r=60, t=10, b=0),
            xaxis_title="MWh", yaxis_title=None,
            showlegend=False,
        )
        fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
        fig.update_yaxes(showgrid=False)
        st.plotly_chart(fig, use_container_width=True, key="stats_bar_mwh")

    st.divider()

    # ── Tabla completa ──────────────────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
        f"Detalle por parque</div>",
        unsafe_allow_html=True,
    )

    filas_tabla = []
    for _, row in df_stats.sort_values("mwh", ascending=False).iterrows():
        dev = row["desvio_pct"]
        sem = _sem_desvio(dev)
        color_dev = _SEM.get(sem, AES_MUTED)
        dev_str = f"{dev:+.1f}%" if dev is not None else "—"
        filas_tabla.append({
            "Parque":        row["nombre"],
            "Tipo":          row["tecnologia"],
            "Produccion MWh": f"{row['mwh']:,.0f}",
            "FP prom %":     f"{row['fp_prom']:.1f}%" if row["fp_prom"] is not None else "—",
            "Desvio PCP":    dev_str,
            "Ingreso USD":   f"${row['ingreso_usd']:,.0f}",
        })

    st.dataframe(pd.DataFrame(filas_tabla), hide_index=True, use_container_width=True)

    # ── Gráfico desvío vs PCP ───────────────────────────────────────────────
    df_dev = df_stats[df_stats["desvio_pct"].notna()].sort_values("desvio_pct")
    if not df_dev.empty:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:16px 0 8px'>"
            f"Desvio promedio vs PCP por parque</div>",
            unsafe_allow_html=True,
        )
        bar_colors = [
            AES_VERDE if abs(v) <= 15 else (AES_AMBAR if abs(v) <= 25 else AES_ROJO)
            for v in df_dev["desvio_pct"]
        ]
        fig2 = go.Figure(go.Bar(
            x=df_dev["nombre"],
            y=df_dev["desvio_pct"],
            marker_color=bar_colors,
            text=[f"{v:+.1f}%" for v in df_dev["desvio_pct"]],
            textposition="outside",
            hovertemplate="%{x}: %{y:+.1f}%<extra>Desvio vs PCP</extra>",
        ))
        fig2.add_hline(y=15,  line_dash="dot", line_color=AES_AMBAR, line_width=1)
        fig2.add_hline(y=-15, line_dash="dot", line_color=AES_AMBAR, line_width=1)
        fig2.add_hline(y=25,  line_dash="dot", line_color=AES_ROJO,  line_width=1)
        fig2.add_hline(y=-25, line_dash="dot", line_color=AES_ROJO,  line_width=1)
        fig2.update_layout(
            template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
            height=280, margin=dict(l=0, r=0, t=20, b=0),
            xaxis_title=None, yaxis_title="Desvio %",
            showlegend=False,
        )
        fig2.update_xaxes(showgrid=False)
        fig2.update_yaxes(showgrid=True, gridcolor=AES_BORDE, zeroline=True, zerolinecolor=AES_BORDE)
        st.plotly_chart(fig2, use_container_width=True, key="stats_bar_desvio")
