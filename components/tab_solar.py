"""Tab Solar FV — tema claro, paleta AES, tooltips explicativos."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone

from config import NOMBRE_DISPLAY, PMAX, PMAX_FP, PARQUES_SOLAR
from utils.calculos import calcular_factor_planta, calcular_desvio

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

_SEM = {"verde": AES_VERDE, "amarillo": AES_AMBAR, "rojo": AES_ROJO}


def _df_meteo(parque: str) -> pd.DataFrame:
    try:
        from utils.db import get_client
        sb = get_client()
        desde = (datetime.now(timezone(timedelta(hours=-3))) - timedelta(hours=168)).strftime("%Y-%m-%d %H:%M:%S")
        res = (
            sb.table("meteo_ernc")
            .select("fecha_hora,ghi_wm2,gti_wm2,temp_2m,temp_celda_c,p_fv_estimada_mw,cloudcover_low_pct,cloud_cover_pct,is_day,es_forecast")
            .eq("parque", parque)
            .gte("fecha_hora", desde)
            .order("fecha_hora")
            .execute()
        )
        if res.data:
            df = pd.DataFrame(res.data)
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"]).dt.tz_localize(None)
            return df
    except Exception:
        pass
    return pd.DataFrame()


def _kpis_solar(gen_por_parque: dict, prog_por_parque: dict, parque_activo: str | None) -> None:
    """Tarjetas-botón: clic selecciona el parque (actualiza el selectbox y el gráfico)."""
    cols = st.columns(len(PARQUES_SOLAR))
    for i, p in enumerate(PARQUES_SOLAR):
        gen    = gen_por_parque.get(p)
        fp     = calcular_factor_planta(gen, PMAX_FP[p])
        nombre = NOMBRE_DISPLAY[p]
        gen_str = "—" if gen is None else f"{gen:.1f}"
        fp_str  = "—" if fp  is None else f"{fp:.0f}%"
        is_sel  = (p == parque_activo)
        with cols[i]:
            if st.button(
                f"{nombre}\n\n{gen_str} MW · FP {fp_str}",
                key=f"kpi_solar_{p}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                st.session_state["solar_parque_sel"] = p
                st.rerun()


def _grafico_gen(df_gen: pd.DataFrame, df_prog: pd.DataFrame, df_meteo: pd.DataFrame, parque: str, corte: pd.Timestamp) -> None:
    # Rango X desde datos reales — evita espacio vacío si la ventana supera los datos disponibles
    _xmins, _xmaxs = [], []
    _dr = df_gen[df_gen["parque"] == parque] if not df_gen.empty else pd.DataFrame()
    if not _dr.empty:
        _xmins.append(_dr["fecha_hora"].min()); _xmaxs.append(_dr["fecha_hora"].max())
    _dp = df_prog[df_prog["parque"] == parque] if not df_prog.empty else pd.DataFrame()
    if not _dp.empty:
        _xmins.append(_dp["fecha_hora"].min()); _xmaxs.append(_dp["fecha_hora"].max())
    x_min = min(_xmins) if _xmins else corte
    x_max = max(_xmaxs) if _xmaxs else None

    fig = go.Figure()

    # Modelo FV: histórico, con la línea ROTA de noche (NaN + connectgaps=False).
    # Antes se filtraban los puntos nocturnos y Plotly los unía con una diagonal
    # que simulaba "potencia de noche" — artefacto, no dato real.
    if not df_meteo.empty and "p_fv_estimada_mw" in df_meteo.columns:
        df_mod = df_meteo[df_meteo["es_forecast"] != True].copy() if "es_forecast" in df_meteo.columns else df_meteo.copy()
        df_mod = df_mod.sort_values("fecha_hora")
        if "is_day" in df_mod.columns:
            is_day_mask = df_mod["is_day"].apply(
                lambda v: bool(v) if not isinstance(v, str) else v.lower() == "true"
            )
            # Noche → NaN para que la traza se corte en vez de dibujar diagonal
            df_mod.loc[~is_day_mask, "p_fv_estimada_mw"] = float("nan")
        if df_mod["p_fv_estimada_mw"].notna().any():
            fig.add_trace(go.Scatter(
                x=df_mod["fecha_hora"], y=df_mod["p_fv_estimada_mw"],
                name="Modelo FV",
                line=dict(color=AES_VIOLETA, width=1.2, dash="dot"),
                connectgaps=False,
                fill="tozeroy", fillcolor="rgba(155,111,212,0.04)",
                hovertemplate="%{y:.1f} MW<extra>Modelo FV</extra>",
            ))

    # PCP encima del modelo — ámbar más grueso y opaco para distinguirse del real
    if not df_prog.empty:
        df_p = df_prog[df_prog["parque"] == parque]
        if not df_p.empty:
            fig.add_trace(go.Scatter(
                x=df_p["fecha_hora"], y=df_p["gen_programada_mw"],
                name="PCP programada",
                line=dict(color="#D97706", width=2.2, dash="dash"),
                hovertemplate="%{y:.1f} MW<extra>PCP programada — declarada D-1 ante CEN</extra>",
            ))

    # Real al tope — azul sólido pero con fillcolor muy suave para no enterrar la PCP
    if not df_gen.empty:
        df_r = df_gen[df_gen["parque"] == parque]
        if not df_r.empty:
            df_r = df_r[df_r["gen_real_mw"] >= 0].copy()
            fig.add_trace(go.Scatter(
                x=df_r["fecha_hora"], y=df_r["gen_real_mw"],
                name="Generacion real",
                line=dict(color=AES_AZUL, width=2.5),
                fill="tozeroy", fillcolor="rgba(59,76,232,0.05)",
                hovertemplate="%{y:.1f} MW<extra>Gen. real CEN gen-real/v3</extra>",
            ))

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=AES_BLANCO,
        plot_bgcolor=AES_GRIS,
        transition=dict(duration=0),
        autosize=True,
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None,
        yaxis_title="MW",
        xaxis=dict(range=[x_min, x_max]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE, rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True, key=f"solar_grafico_gen_{parque}")


def _grafico_ghi(df_meteo: pd.DataFrame, parque: str, corte: pd.Timestamp) -> None:
    if df_meteo.empty or "ghi_wm2" not in df_meteo.columns:
        return

    fig = go.Figure()
    hist = df_meteo[df_meteo["es_forecast"] != True]
    fore = df_meteo[df_meteo["es_forecast"] == True]
    x_min = df_meteo["fecha_hora"].min() if not df_meteo.empty else corte
    x_max = df_meteo["fecha_hora"].max() if not df_meteo.empty else None

    if not hist.empty:
        fig.add_trace(go.Scatter(
            x=hist["fecha_hora"], y=hist["ghi_wm2"],
            name="GHI historico",
            line=dict(color=AES_AMBAR, width=2),
            fill="tozeroy", fillcolor="rgba(245,158,11,0.08)",
            hovertemplate="%{y:.0f} W/m²<extra>GHI hist. — Global Horizontal Irradiance (shortwave_radiation Open-Meteo)</extra>",
        ))
    if not fore.empty:
        fig.add_trace(go.Scatter(
            x=fore["fecha_hora"], y=fore["ghi_wm2"],
            name="GHI forecast",
            line=dict(color=AES_AMBAR, width=1.5, dash="dot"),
            hovertemplate="%{y:.0f} W/m²<extra>GHI forecast Open-Meteo (7 d)</extra>",
        ))
    if "cloudcover_low_pct" in df_meteo.columns:
        fig.add_trace(go.Scatter(
            x=df_meteo["fecha_hora"], y=df_meteo["cloudcover_low_pct"],
            name="Nubosidad baja %",
            yaxis="y2",
            line=dict(color=AES_MUTED, width=1, dash="dot"),
            hovertemplate="%{y:.0f}%<extra>Nubosidad baja (camanchaca si >60% con cielo total <35%)</extra>",
        ))

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=AES_BLANCO,
        plot_bgcolor=AES_GRIS,
        transition=dict(duration=0),
        autosize=True,
        height=220,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None,
        yaxis_title="W/m²",
        xaxis=dict(range=[x_min, x_max]),
        yaxis2=dict(title="Nubosidad %", overlaying="y", side="right", range=[0, 100], showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key=f"solar_grafico_ghi_{parque}")


def _gen_prog_mismo_hora(df_gen, df_prog, parque):
    """Devuelve (gen, prog, hora) en la ÚLTIMA hora con gen real, con la PCP de
    esa MISMA hora. Comparar contra la última PCP (a veces futura) daba desvíos
    sin sentido (-100%) o nulos."""
    gen = prog = None
    hora = None
    if df_gen is not None and not df_gen.empty:
        d = df_gen[df_gen["parque"] == parque]
        d = d[d["gen_real_mw"] >= 0].sort_values("fecha_hora")
        if not d.empty:
            last = d.iloc[-1]
            gen = last["gen_real_mw"]
            hora = last["fecha_hora"]
            if df_prog is not None and not df_prog.empty:
                dp = df_prog[(df_prog["parque"] == parque) & (df_prog["fecha_hora"] == hora)]
                if not dp.empty:
                    prog = dp.iloc[-1]["gen_programada_mw"]
    return gen, prog, hora


def _panel_metricas(df_gen, df_prog, df_meteo, parque_sel):
    """Fila de métricas horizontales debajo del gráfico de generación."""
    gen, prog, _ = _gen_prog_mismo_hora(df_gen, df_prog, parque_sel)
    fp   = calcular_factor_planta(gen, PMAX_FP[parque_sel])
    dev  = calcular_desvio(gen, prog)

    ghi = tc = None
    if not df_meteo.empty:
        hist_m = df_meteo[df_meteo["es_forecast"] == False]
        if len(hist_m) > 0:
            u   = hist_m.iloc[-1]
            ghi = u.get("ghi_wm2")
            tc  = u.get("temp_celda_c")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("Generacion actual", f"{gen:.1f} MW" if gen is not None else "—")
    with c2:
        st.metric("Pmax neta CEN", f"{PMAX_FP[parque_sel]:.1f} MW",
                  help="Potencia máxima neta CEN usada para factor de planta. "
                       f"Capacidad config dashboard: {PMAX[parque_sel]:.1f} MW.")
    with c3:
        st.metric("Factor de planta", f"{fp:.1f}%" if fp is not None else "—")
    with c4:
        desvio_str = f"{dev['desvio_pct']:+.1f}%" if dev["desvio_pct"] is not None else "—"
        st.metric(
            "Desvio vs PCP",
            desvio_str,
            delta=f"{dev['desvio_mw']:+.1f} MW" if dev["desvio_mw"] is not None else None,
        )
    with c5:
        st.metric("GHI", f"{ghi:.0f} W/m²" if ghi is not None else "—")
    with c6:
        st.metric("Temp. celda", f"{tc:.1f} °C" if tc is not None else "—")

    st.caption(
        "Generacion: ultimo gen_real CEN · Cap. instalada: Pmax declarada · "
        "FP = Gen/Cap × 100 · Desvio = (Gen − PCP)/PCP × 100 a la misma hora "
        "(verde ≤15% · ambar ≤25% · rojo >25%) · GHI: irradiancia global horizontal "
        "Open-Meteo · Temp. celda: modelo NOCT (Tc = Tamb + (NOCT−20)/800 · GHI · f_viento)."
    )


def render_tab_solar(
    gen_por_parque: dict,
    prog_por_parque: dict,
    gen_rows: list[dict],
    prog_rows: list[dict],
    parque_activo: str | None = None,
) -> None:
    _ventanas = [24, 48, 72, 168]

    # Selección de parque: el sidebar fuerza el selectbox una sola vez (one-shot);
    # luego el desplegable es dueño de su estado y el usuario puede cambiarlo libremente.
    _sync = st.session_state.pop("_sync_parque", None)
    if _sync in PARQUES_SOLAR:
        st.session_state["solar_parque_sel"] = _sync
    if st.session_state.get("solar_parque_sel") not in PARQUES_SOLAR:
        st.session_state["solar_parque_sel"] = (
            parque_activo if parque_activo in PARQUES_SOLAR else PARQUES_SOLAR[0]
        )

    if st.session_state.get("solar_ventana_horas") not in _ventanas:
        st.session_state["solar_ventana_horas"] = 168

    # KPIs resaltan el parque actualmente seleccionado (coherente con el gráfico)
    _kpis_solar(gen_por_parque, prog_por_parque, st.session_state["solar_parque_sel"])
    st.divider()

    parque_sel = st.selectbox(
        "Parque solar",
        PARQUES_SOLAR,
        format_func=lambda p: NOMBRE_DISPLAY[p],
        key="solar_parque_sel",
    )
    horas_ventana = st.selectbox(
        "Ventana",
        _ventanas,
        format_func=lambda h: "Ultima semana" if h == 168 else f"Ultimas {h} h",
        key="solar_ventana_horas",
    )

    corte = pd.Timestamp.now() - pd.Timedelta(hours=horas_ventana)

    df_gen_raw = pd.DataFrame(gen_rows)
    if not df_gen_raw.empty:
        df_gen_raw["fecha_hora"] = pd.to_datetime(df_gen_raw["fecha_hora"]).dt.tz_localize(None)

    df_gen = df_gen_raw.copy()
    df_prog = pd.DataFrame(prog_rows) if prog_rows else pd.DataFrame()
    if not df_gen.empty:
        df_gen = df_gen[df_gen["parque"].isin(PARQUES_SOLAR)]
        df_gen = df_gen[df_gen["fecha_hora"] >= corte]
    if not df_prog.empty:
        df_prog["fecha_hora"] = pd.to_datetime(df_prog["fecha_hora"]).dt.tz_localize(None)
        df_prog = df_prog[df_prog["parque"].isin(PARQUES_SOLAR)]
        df_prog = df_prog[df_prog["fecha_hora"] >= corte]

    df_meteo = _df_meteo(parque_sel)
    if not df_meteo.empty:
        df_meteo = df_meteo[df_meteo["fecha_hora"] >= corte]


# ── Gráfico generación — ancho completo ──
    nombre_ventana = "ultima semana" if horas_ventana == 168 else f"ultimas {horas_ventana} h"
    grafico_container = st.container()
    with grafico_container:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:6px'>"
            f"Generacion — {NOMBRE_DISPLAY[parque_sel]} ({nombre_ventana})</div>",
            unsafe_allow_html=True,
        )
        _grafico_gen(df_gen, df_prog, df_meteo, parque_sel, corte)

    # ── Métricas entre los dos gráficos ──
    _panel_metricas(df_gen, df_prog, df_meteo, parque_sel)

    # ── Segunda serie de tiempo: GHI + nubosidad (antes que leyenda/fórmulas) ──
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:10px 0 6px'>"
        f"Irradiancia GHI + nubosidad baja — {NOMBRE_DISPLAY[parque_sel]}</div>",
        unsafe_allow_html=True,
    )
    _grafico_ghi(df_meteo, parque_sel, corte)

    # ── Glosario de series — al final, tras los gráficos ──
    st.markdown(
        f"""<div style='background:{AES_BLANCO};border:1px solid {AES_BORDE};border-radius:10px;
padding:14px 20px;margin:10px 0 14px;font-size:11.5px;color:{AES_TEXTO};line-height:1.7'>
<div style='font-size:11px;font-weight:700;color:{AES_MUTED};text-transform:uppercase;
letter-spacing:0.8px;margin-bottom:10px'>Leyenda de series</div>
<div style='display:grid;grid-template-columns:1fr 1fr;gap:6px 24px'>
  <div><span style='display:inline-block;width:28px;height:3px;background:{AES_AZUL};
  vertical-align:middle;margin-right:7px;border-radius:2px'></span>
  <b>Generacion real</b> — medicion CEN hora a hora (gen-real/v3). BESS y valores negativos excluidos.</div>
  <div><span style='display:inline-block;width:28px;height:2px;background:#D97706;
  vertical-align:middle;margin-right:7px;border-radius:2px;border-bottom:2px dashed #D97706'></span>
  <b>PCP programada</b> — potencia declarada D-1 ante el Coordinador (SIPUB pcp/v4).</div>
  <div><span style='display:inline-block;width:28px;height:1px;background:{AES_VIOLETA};
  vertical-align:middle;margin-right:7px;border-radius:2px;border-bottom:2px dotted {AES_VIOLETA}'></span>
  <b>Modelo FV</b> — potencia estimada por irradiancia y temperatura de celda
  (fórmulas en el panel inferior). Solo horas diurnas.</div>
  <div><span style='display:inline-block;width:28px;height:3px;background:{AES_AMBAR};
  vertical-align:middle;margin-right:7px;border-radius:2px'></span>
  <b>GHI historico</b> — irradiancia global horizontal [W/m²] (Open-Meteo).</div>
  <div><span style='display:inline-block;width:28px;height:1px;background:{AES_AMBAR};
  vertical-align:middle;margin-right:7px;border-bottom:2px dotted {AES_AMBAR}'></span>
  <b>GHI forecast</b> — pronostico Open-Meteo proximos 7 dias.</div>
  <div><span style='display:inline-block;width:28px;height:1px;background:{AES_MUTED};
  vertical-align:middle;margin-right:7px;border-bottom:2px dotted {AES_MUTED}'></span>
  <b>Nubosidad baja %</b> — fraccion cubierta por nubes bajas.
  Camanchaca si &gt;60% con total &lt;35%.</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    with st.expander("Fórmulas del modelo FV"):
        st.latex(r"T_c \;=\; T_{amb} \;+\; \frac{NOCT - 20}{800}\;\cdot\;GHI\;\cdot\;f_{viento}")
        st.latex(r"P_{FV} \;=\; P_{pico}\;\cdot\;\frac{GTI}{1000}\;\cdot\;\bigl[\,1 + \gamma\,(T_c - 25)\,\bigr]")
        st.markdown(
            f"<div style='font-size:11.5px;color:{AES_MUTED};line-height:1.7'>"
            r"$NOCT = 45\,^{\circ}\mathrm{C}$ (Normal Operating Cell Temperature) &nbsp;·&nbsp; "
            r"$\gamma = -0.4\,\%/^{\circ}\mathrm{C}$ (coef. de temperatura, silicio cristalino) &nbsp;·&nbsp; "
            r"$GTI$ = irradiancia sobre el plano inclinado $[\mathrm{W/m^2}]$ &nbsp;·&nbsp; "
            r"$f_{viento}$ corrige la convección. Potencia acotada a $P_{pico}$ y a horas diurnas."
            "</div>",
            unsafe_allow_html=True,
        )
