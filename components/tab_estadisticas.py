"""Tab Estadísticas — producción acumulada, desvío, ingresos USD, ranking FP."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config import (
    NOMBRE_DISPLAY, PMAX, PMAX_FP, PMAX_FP_TOTAL, TECNOLOGIA,
    PARQUES_TODOS, PARQUES_SOLAR, PARQUES_EOLICA, CMG_NODO,
    BESS, BESS_HORAS,
)

# Factor de emisión evitado del SEN chileno (tCO2/MWh, referencia ~0.4).
_FACTOR_CO2 = 0.4

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
    bess_rows: list | None = None,
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
        fp_prom = (mwh / (PMAX_FP[p] * n_horas) * 100) if n_horas > 0 and PMAX_FP[p] > 0 else None

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
            "pmax_mw":     PMAX_FP[p],
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
        st.metric("Produccion total", f"{total_mwh:,.0f} MWh",)
    with c2:
        st.metric("Solar FV", f"{solar_mwh:,.0f} MWh",)
    with c3:
        st.metric("Eolica", f"{eolica_mwh:,.0f} MWh",)
    with c4:
        st.metric("Ingreso estimado", f"USD {total_ingreso:,.0f}",)

    # ── Segunda fila: indicadores derivados ──────────────────────────────────
    fp_portfolio = (total_mwh / (PMAX_FP_TOTAL * n_horas_ref) * 100) if n_horas_ref else None
    df_fp = df_stats[df_stats["fp_prom"].notna()]
    mejor = df_fp.sort_values("fp_prom", ascending=False).iloc[0] if not df_fp.empty else None
    co2_evit = total_mwh * _FACTOR_CO2
    precio_medio = (total_ingreso / total_mwh) if total_mwh else None
    # Cumplimiento PCP: % de parques dentro de ±15% de desvío
    df_pcp = df_stats[df_stats["desvio_pct"].notna()]
    cumpl = (df_pcp["desvio_pct"].abs() <= 15).mean() * 100 if not df_pcp.empty else None

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.metric("FP portfolio", f"{fp_portfolio:.1f}%" if fp_portfolio is not None else "—")
    with d2:
        st.metric("Mejor parque (FP)",
                  f"{mejor['fp_prom']:.1f}%" if mejor is not None else "—",
                  delta=mejor["nombre"] if mejor is not None else None, delta_color="off")
    with d3:
        st.metric("Precio medio capturado",
                  f"{precio_medio:,.1f} USD/MWh" if precio_medio is not None else "—")
    with d4:
        st.metric("CO₂ evitado (aprox.)", f"{co2_evit:,.0f} tCO₂")
    st.caption(
        f"FP portfolio = MWh / (Pmax neta total × horas). CO₂ evitado ≈ producción × "
        f"{_FACTOR_CO2} tCO₂/MWh (factor SEN referencial). "
        + (f"Cumplimiento PCP (±15%): {cumpl:.0f}% de los parques." if cumpl is not None else "")
    )

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
            template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS, transition=dict(duration=500, easing="cubic-in-out"),
            height=340, margin=dict(l=0, r=60, t=10, b=0),
            xaxis_title="MWh", yaxis_title=None,
            showlegend=False,
        )
        fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
        fig.update_yaxes(showgrid=False)
        st.plotly_chart(fig, use_container_width=True, key="stats_bar_mwh")

    st.divider()

    # ── Mix energético + perfil horario ─────────────────────────────────────
    df_gen["tec"] = df_gen["parque"].map(TECNOLOGIA)
    col_mix, col_perfil = st.columns([1, 2])

    with col_mix:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
            f"Mix de produccion (MWh)</div>",
            unsafe_allow_html=True,
        )
        fig_mix = go.Figure(go.Pie(
            labels=["Solar FV", "Eolica"],
            values=[solar_mwh, eolica_mwh],
            hole=0.58,
            marker_colors=[AES_AZUL, AES_CYAN],
            textinfo="percent",
            hovertemplate="%{label}: %{value:,.0f} MWh (%{percent})<extra></extra>",
        ))
        fig_mix.update_layout(
            template="plotly_white", paper_bgcolor=AES_BLANCO,
            height=300, margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, x=0.5, xanchor="center"),
            annotations=[dict(text=f"{total_mwh:,.0f}<br>MWh", x=0.5, y=0.5,
                              font_size=15, showarrow=False, font_color=AES_TEXTO)],
        )
        st.plotly_chart(fig_mix, use_container_width=True, key="stats_mix_donut")

    with col_perfil:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
            f"Produccion horaria del portfolio por tecnologia (MW)</div>",
            unsafe_allow_html=True,
        )
        piv = df_gen.groupby(["fecha_hora", "tec"])["gen_real_mw"].sum().reset_index()
        fig_area = go.Figure()
        for tec, color, fill in [
            ("Solar", AES_AZUL, "rgba(59,76,232,0.35)"),
            ("Eólica", AES_CYAN, "rgba(77,200,220,0.40)"),
        ]:
            sub = piv[piv["tec"] == tec].sort_values("fecha_hora")
            if sub.empty:
                continue
            fig_area.add_trace(go.Scatter(
                x=sub["fecha_hora"], y=sub["gen_real_mw"],
                name="Solar FV" if tec == "Solar" else "Eolica",
                mode="lines", stackgroup="one",
                line=dict(width=0.5, color=color),
                fillcolor=fill,
                hovertemplate="%{y:,.0f} MW<extra>" + tec + "</extra>",
            ))
        fig_area.update_layout(
            template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
            height=300, margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title=None, yaxis_title="MW",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            hovermode="x unified",
        )
        fig_area.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
        fig_area.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
        st.plotly_chart(fig_area, use_container_width=True, key="stats_area_tec")

    # ── Heatmap factor de planta por hora del día ───────────────────────────
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:16px 0 8px'>"
        f"Factor de planta promedio por hora del dia (%) — patron diario por parque</div>",
        unsafe_allow_html=True,
    )
    df_gen["hora_dia"] = df_gen["fecha_hora"].dt.hour
    hm = df_gen.groupby(["parque", "hora_dia"])["gen_real_mw"].mean().reset_index()
    hm["fp"] = hm.apply(
        lambda r: (r["gen_real_mw"] / PMAX_FP[r["parque"]] * 100) if PMAX_FP.get(r["parque"]) else None,
        axis=1,
    )
    orden = [p for p in PARQUES_TODOS if p in hm["parque"].unique()]
    pivot = hm.pivot(index="parque", columns="hora_dia", values="fp").reindex(orden)
    if not pivot.empty:
        fig_hm = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[f"{h:02d}h" for h in pivot.columns],
            y=[NOMBRE_DISPLAY[p] for p in pivot.index],
            colorscale=[[0, "#F5F7FA"], [0.5, AES_CYAN], [1, AES_AZUL]],
            colorbar=dict(title="FP %"),
            hovertemplate="%{y} · %{x}: %{z:.0f}%<extra></extra>",
        ))
        fig_hm.update_layout(
            template="plotly_white", paper_bgcolor=AES_BLANCO,
            height=360, margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_hm, use_container_width=True, key="stats_heatmap_fp")

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

    csv = df_stats.drop(columns=["parque"], errors="ignore").rename(columns={
        "nombre": "parque", "tecnologia": "tipo", "pmax_mw": "pmax_neta_mw",
        "mwh": "produccion_mwh", "fp_prom": "fp_prom_pct",
        "desvio_pct": "desvio_pcp_pct", "ingreso_usd": "ingreso_usd_estimado",
        "n_horas": "horas",
    }).to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descargar estadísticas (CSV)", data=csv,
        file_name="estadisticas_portfolio_ernc.csv", mime="text/csv",
        key="stats_csv",
    )

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
            template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS, transition=dict(duration=500, easing="cubic-in-out"),
            height=280, margin=dict(l=0, r=0, t=20, b=0),
            xaxis_title=None, yaxis_title="Desvio %",
            showlegend=False,
        )
        fig2.update_xaxes(showgrid=False)
        fig2.update_yaxes(showgrid=True, gridcolor=AES_BORDE, zeroline=True, zerolinecolor=AES_BORDE)
        st.plotly_chart(fig2, use_container_width=True, key="stats_bar_desvio")

    # ── Skill de pronóstico vs PCP/PID ──────────────────────────────────────
    _seccion_skill(df_gen, df_prog)

    # ── BESS — almacenamiento del portfolio ─────────────────────────────────
    _seccion_bess(bess_rows)


def _seccion_skill(df_gen: pd.DataFrame, df_prog: pd.DataFrame) -> None:
    """Calidad del programa oficial (PCP día-antes y PID intra-día) vs generación real.

    MAE y sesgo hora a hora por parque. Es la base del informe de cumplimiento de
    pronóstico: cuantifica cuánto se equivoca el programa que se declara al CEN."""
    if df_prog.empty or "fuente" not in df_prog.columns:
        return

    st.divider()
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:4px 0 8px'>"
        f"Skill del programa oficial (PCP / PID) vs generacion real</div>",
        unsafe_allow_html=True,
    )

    filas = []
    for p in PARQUES_TODOS:
        gp = df_gen[df_gen["parque"] == p][["fecha_hora", "gen_real_mw"]]
        if gp.empty:
            continue
        fila = {"Parque": NOMBRE_DISPLAY[p], "_pmax": PMAX_FP.get(p) or 1}
        for fuente, etiqueta in (("CEN_PCP", "PCP"), ("CEN_PID", "PID")):
            pf = df_prog[(df_prog["parque"] == p) & (df_prog["fuente"] == fuente)]
            m = gp.merge(pf[["fecha_hora", "gen_programada_mw"]], on="fecha_hora", how="inner")
            m = m.dropna(subset=["gen_real_mw", "gen_programada_mw"])
            if len(m) < 12:
                fila[f"MAE {etiqueta} (MW)"] = None
                fila[f"Sesgo {etiqueta} (MW)"] = None
                continue
            err = m["gen_real_mw"] - m["gen_programada_mw"]
            fila[f"MAE {etiqueta} (MW)"] = round(float(err.abs().mean()), 1)
            fila[f"Sesgo {etiqueta} (MW)"] = round(float(err.mean()), 1)
            fila[f"_horas_{etiqueta}"] = len(m)
        filas.append(fila)

    if not filas:
        st.caption("Sin horas comunes entre generacion real y programas PCP/PID en la ventana.")
        return

    df_skill = pd.DataFrame(filas)
    df_skill["MAE PCP (% Pmax)"] = (df_skill.get("MAE PCP (MW)") / df_skill["_pmax"] * 100).round(1)
    cols = [c for c in ["Parque", "MAE PCP (MW)", "Sesgo PCP (MW)", "MAE PID (MW)",
                        "Sesgo PID (MW)", "MAE PCP (% Pmax)"] if c in df_skill.columns]
    st.dataframe(df_skill[cols], hide_index=True, use_container_width=True)
    st.caption(
        "MAE = error medio absoluto hora a hora del programa vs lo realmente generado "
        "(menor es mejor). Sesgo > 0 = el parque genero MAS de lo programado (sub-declara); "
        "< 0 = genero menos (sobre-declara, expuesto a desvios). El PID deberia tener menor "
        "MAE que el PCP por ser intra-dia; si no, hay espacio para mejorar la declaracion. "
        "Ventana: la misma de la seccion (168 h)."
    )


def _seccion_bess(bess_rows: list | None) -> None:
    st.divider()
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:6px 0 8px'>"
        f"Almacenamiento BESS — energía y ciclos del período</div>",
        unsafe_allow_html=True,
    )
    if not bess_rows:
        st.info("Sin datos de BESS en el período. Se poblará con la adquisición horaria.")
        return

    df = pd.DataFrame(bess_rows)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    # 1 fila = 1 hora → MW ≈ MWh. Descarga = inyección, carga = retiro.
    df["desc_mwh"] = df["inyeccion_mw"].clip(lower=0)
    df["carga_mwh"] = df["retiro_mw"].clip(lower=0)

    filas = []
    for cod, b in BESS.items():
        sub = df[df["bess"] == cod]
        if sub.empty:
            continue
        desc = sub["desc_mwh"].sum()
        carga = sub["carga_mwh"].sum()
        energia = b["pmax_mw"] * (BESS_HORAS.get(cod) or 4.0)
        ciclos = desc / energia if energia > 0 else 0
        rt = (desc / carga * 100) if carga > 0 else None   # eficiencia round-trip aparente
        filas.append({
            "BESS": b["nombre"], "Parque": b["parque"],
            "Descarga (MWh)": round(desc, 1), "Carga (MWh)": round(carga, 1),
            "Energía neta (MWh)": round(desc - carga, 1),
            "Ciclos eq.": round(ciclos, 2),
            "Round-trip (%)": round(rt, 0) if rt is not None else None,
        })
    if not filas:
        st.info("Sin registros BESS para los códigos conocidos.")
        return
    dfb = pd.DataFrame(filas)

    tot_desc = dfb["Descarga (MWh)"].sum()
    tot_carga = dfb["Carga (MWh)"].sum()
    rt_glob = (tot_desc / tot_carga * 100) if tot_carga > 0 else None
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Descarga total", f"{tot_desc:,.0f} MWh")
    c2.metric("Carga total", f"{tot_carga:,.0f} MWh")
    c3.metric("Energía neta", f"{tot_desc - tot_carga:+,.0f} MWh")
    c4.metric("Round-trip global", f"{rt_glob:.0f}%" if rt_glob else "—")

    # Barras: carga vs descarga por BESS
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dfb["BESS"], y=dfb["Descarga (MWh)"], name="Descarga",
                         marker_color=AES_VERDE))
    fig.add_trace(go.Bar(x=dfb["BESS"], y=-dfb["Carga (MWh)"], name="Carga",
                         marker_color=AES_AZUL))
    fig.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                      barmode="relative", height=300, margin=dict(l=0, r=0, t=20, b=0),
                      yaxis_title="MWh (descarga + / carga −)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)))
    fig.add_hline(y=0, line_color=AES_MUTED, line_width=1)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key="stats_bess_bar")
    st.dataframe(dfb, hide_index=True, use_container_width=True)
    st.caption(
        "Descarga = energía entregada al sistema; carga = tomada de la red. Ciclos eq. = "
        "descarga / capacidad de energía (Pmax × duración). Round-trip = descarga/carga (aparente, "
        "incluye energía propia del parque que carga el BESS, no solo de red)."
    )
    csv = dfb.to_csv(index=False).encode("utf-8")
    st.download_button("Descargar BESS (CSV)", data=csv,
                       file_name="estadisticas_bess_ernc.csv", mime="text/csv", key="stats_bess_csv")
