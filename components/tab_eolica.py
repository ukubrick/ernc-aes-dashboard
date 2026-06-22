"""Tab Eolica — tema claro, paleta AES, tooltips explicativos."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone

from config import NOMBRE_DISPLAY, PMAX, PMAX_FP, PARQUES_EOLICA
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
            .select(
                "fecha_hora,wind_speed_10m,wind_speed_80m,wind_speed_100m,"
                "wind_gusts_10m,wind_dir_80m,wind_shear_alpha,"
                "densidad_aire,p_eolica_estimada_mw,boundary_layer_height,"
                "temp_2m,es_forecast"
            )
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


def _kpis_eolica(gen_por_parque: dict, prog_por_parque: dict, parque_activo: str | None) -> None:
    """Tarjetas-botón: clic selecciona el parque (actualiza el selectbox y el gráfico)."""
    cols = st.columns(len(PARQUES_EOLICA))
    for i, p in enumerate(PARQUES_EOLICA):
        gen    = gen_por_parque.get(p)
        fp     = calcular_factor_planta(gen, PMAX_FP[p])
        nombre = NOMBRE_DISPLAY[p]
        gen_str = "—" if gen is None else f"{gen:.1f}"
        fp_str  = "—" if fp  is None else f"{fp:.0f}%"
        is_sel  = (p == parque_activo)
        with cols[i]:
            if st.button(
                f"{nombre}\n\n{gen_str} MW · FP {fp_str}",
                key=f"kpi_eolica_{p}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                st.session_state["eolica_parque_sel"] = p
                st.rerun()


def _grafico_gen(gen_rows: list, prog_rows: list, df_meteo: pd.DataFrame, parque: str, horas_ventana: int) -> None:
    fig = go.Figure()

    corte = pd.Timestamp.now() - pd.Timedelta(hours=horas_ventana)

    # Rango X desde datos reales — evita espacio vacío si la ventana supera los datos disponibles
    _xmins, _xmaxs = [], []
    if gen_rows:
        _dr = pd.DataFrame(gen_rows)
        _dr["fecha_hora"] = pd.to_datetime(_dr["fecha_hora"]).dt.tz_localize(None)
        _dr = _dr[(_dr["parque"] == parque) & (_dr["fecha_hora"] >= corte)]
        if not _dr.empty:
            _xmins.append(_dr["fecha_hora"].min()); _xmaxs.append(_dr["fecha_hora"].max())
    if prog_rows:
        _dp = pd.DataFrame(prog_rows)
        _dp["fecha_hora"] = pd.to_datetime(_dp["fecha_hora"]).dt.tz_localize(None)
        _dp = _dp[(_dp["parque"] == parque) & (_dp["fecha_hora"] >= corte)]
        if not _dp.empty:
            _xmins.append(_dp["fecha_hora"].min()); _xmaxs.append(_dp["fecha_hora"].max())
    x_min_gen = min(_xmins) if _xmins else corte
    x_max_gen = max(_xmaxs) if _xmaxs else None

    # Modelo eólico primero (fondo) — solo histórico para no estirar el eje X al futuro
    if not df_meteo.empty and "p_eolica_estimada_mw" in df_meteo.columns:
        df_mod = df_meteo[
            (df_meteo["es_forecast"] != True) & df_meteo["p_eolica_estimada_mw"].notna()
        ].copy() if "es_forecast" in df_meteo.columns else df_meteo[df_meteo["p_eolica_estimada_mw"].notna()].copy()
        if not df_mod.empty:
            fig.add_trace(go.Scatter(
                x=df_mod["fecha_hora"], y=df_mod["p_eolica_estimada_mw"],
                name="Modelo eolico",
                line=dict(color=AES_VIOLETA, width=1.2, dash="dot"),
                fill="tozeroy", fillcolor="rgba(155,111,212,0.04)",
                hovertemplate="%{y:.1f} MW<extra>Modelo eolico</extra>",
            ))

    if prog_rows:
        df_p = pd.DataFrame(prog_rows)
        df_p["fecha_hora"] = pd.to_datetime(df_p["fecha_hora"]).dt.tz_localize(None)
        df_p = df_p[(df_p["parque"] == parque) & (df_p["fecha_hora"] >= corte)].sort_values("fecha_hora")
        if not df_p.empty:
            fig.add_trace(go.Scatter(
                x=df_p["fecha_hora"], y=df_p["gen_programada_mw"],
                name="PCP programada",
                line=dict(color="#D97706", width=2.2, dash="dash"),
                hovertemplate="%{y:.1f} MW<extra>PCP programada — declarada D-1 ante CEN</extra>",
            ))

    if gen_rows:
        df_r = pd.DataFrame(gen_rows)
        df_r["fecha_hora"] = pd.to_datetime(df_r["fecha_hora"]).dt.tz_localize(None)
        df_r = df_r[(df_r["parque"] == parque) & (df_r["fecha_hora"] >= corte)].sort_values("fecha_hora")
        df_r = df_r[df_r["gen_real_mw"] >= 0]
        if not df_r.empty:
            fig.add_trace(go.Scatter(
                x=df_r["fecha_hora"], y=df_r["gen_real_mw"],
                name="Generacion real",
                line=dict(color=AES_CYAN, width=2.5),
                fill="tozeroy", fillcolor="rgba(77,200,220,0.05)",
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
        xaxis=dict(range=[x_min_gen, x_max_gen]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE, rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True, key=f"eolica_grafico_gen_{parque}")


def _grafico_viento(df_meteo: pd.DataFrame, parque: str, corte: pd.Timestamp) -> None:
    """Gráfico de viento separado en dos subplots: velocidad arriba, shear abajo."""
    if df_meteo.empty:
        return

    x_min = df_meteo["fecha_hora"].min() if not df_meteo.empty else corte
    x_max = df_meteo["fecha_hora"].max() if not df_meteo.empty else None

    # Subplot superior: velocidades (10m, 100m, rafagas)
    fig_v = go.Figure()
    for col, label, color, width, dash in [
        ("wind_speed_10m",  "Viento 10m",       AES_MUTED, 1.2, "dot"),
        ("wind_speed_100m", "Viento 100m (hub)", AES_CYAN,  2.2, "solid"),
        ("wind_gusts_10m",  "Rafagas 10m",       AES_ROJO,  1.2, "dash"),
    ]:
        if col not in df_meteo.columns:
            continue
        hist = df_meteo[df_meteo["es_forecast"] == False]
        fore = df_meteo[df_meteo["es_forecast"] == True]
        if not hist.empty:
            fig_v.add_trace(go.Scatter(
                x=hist["fecha_hora"], y=hist[col],
                name=label,
                line=dict(color=color, width=width, dash=dash),
                hovertemplate=f"%{{y:.1f}} m/s<extra>{label} (historico)</extra>",
            ))
        if not fore.empty:
            fig_v.add_trace(go.Scatter(
                x=fore["fecha_hora"], y=fore[col],
                name=f"{label} fcst",
                line=dict(color=color, width=1, dash="dot"),
                showlegend=False,
                hovertemplate=f"%{{y:.1f}} m/s<extra>{label} (forecast)</extra>",
            ))

    # Línea de referencia cut-out — solo visible si los datos alcanzan ~18 m/s para evitar escala forzada
    if not df_meteo.empty:
        fig_v.add_hline(
            y=20, line_dash="dot", line_color="rgba(239,68,68,0.45)", line_width=1,
            annotation_text="Cut-out ~20 m/s", annotation_position="right",
            annotation_font_size=9, annotation_font_color="rgba(239,68,68,0.7)",
        )

    fig_v.update_layout(
        template="plotly_white",
        paper_bgcolor=AES_BLANCO,
        plot_bgcolor=AES_GRIS,
        transition=dict(duration=0),
        autosize=True,
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None,
        yaxis_title="m/s",
        xaxis=dict(range=[x_min, x_max]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig_v.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig_v.update_yaxes(showgrid=True, gridcolor=AES_BORDE, rangemode="tozero")
    st.plotly_chart(fig_v, use_container_width=True, key=f"eolica_grafico_viento_{parque}")

    # Shear α en gráfico propio — eje Y automático
    if "wind_shear_alpha" in df_meteo.columns:
        df_sh = df_meteo[df_meteo["wind_shear_alpha"].notna()].copy()
        if not df_sh.empty:
            # El cizalle es físicamente acotado a [-0.10, 0.60]. Datos antiguos en DB
            # (pre-Sesión 14) traen valores absurdos (-2..+5); se recortan para el
            # gráfico hasta que la re-adquisición meteo los repueble.
            df_sh["wind_shear_alpha"] = df_sh["wind_shear_alpha"].clip(-0.10, 0.60)
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(
                x=df_sh["fecha_hora"], y=df_sh["wind_shear_alpha"],
                name="Wind shear alpha",
                line=dict(color=AES_VIOLETA, width=1.5),
                hovertemplate="%{y:.3f}<extra>Wind shear α</extra>",
            ))
            fig_s.add_hline(y=0, line_width=1, line_color=AES_BORDE)
            fig_s.add_hline(
                y=0.30, line_dash="dot", line_color=AES_AMBAR, line_width=1,
                annotation_text="α = 0.30 (umbral atm. estable)", annotation_position="right",
                annotation_font_size=9, annotation_font_color=AES_AMBAR,
            )
            fig_s.update_layout(
                template="plotly_white",
                paper_bgcolor=AES_BLANCO,
                plot_bgcolor=AES_GRIS,
                autosize=True,
                height=200,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title=None,
                yaxis_title="α (shear)",
                xaxis=dict(range=[x_min, x_max]),
                yaxis=dict(range=[-0.15, 0.65]),
                hovermode="x unified",
                showlegend=False,
            )
            fig_s.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
            fig_s.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
            st.plotly_chart(fig_s, use_container_width=True, key=f"eolica_grafico_shear_{parque}")


def _gen_prog_mismo_hora(gen_rows, prog_rows, parque):
    """(gen, prog) en la última hora con gen real, con la PCP de esa misma hora."""
    gen = prog = None
    if gen_rows:
        d = pd.DataFrame(gen_rows)
        d["fecha_hora"] = pd.to_datetime(d["fecha_hora"]).dt.tz_localize(None)
        d = d[(d["parque"] == parque) & (d["gen_real_mw"] >= 0)].sort_values("fecha_hora")
        if not d.empty:
            last = d.iloc[-1]
            gen = last["gen_real_mw"]
            hora = last["fecha_hora"]
            if prog_rows:
                dp = pd.DataFrame(prog_rows)
                dp["fecha_hora"] = pd.to_datetime(dp["fecha_hora"]).dt.tz_localize(None)
                dp = dp[(dp["parque"] == parque) & (dp["fecha_hora"] == hora)]
                if not dp.empty:
                    prog = dp.iloc[-1]["gen_programada_mw"]
    return gen, prog


def _panel_metricas(gen_rows, prog_rows, df_meteo, parque_sel):
    """Fila de métricas horizontales debajo del gráfico de generación."""
    gen, prog = _gen_prog_mismo_hora(gen_rows, prog_rows, parque_sel)
    fp   = calcular_factor_planta(gen, PMAX_FP[parque_sel])
    dev  = calcular_desvio(gen, prog)

    v100 = alpha = gusts = None
    if not df_meteo.empty:
        hist_m = df_meteo[df_meteo["es_forecast"] == False]
        if len(hist_m) > 0:
            u     = hist_m.iloc[-1]
            v100  = u.get("wind_speed_100m")
            alpha = u.get("wind_shear_alpha")
            gusts = u.get("wind_gusts_10m")

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
        st.metric("Viento 100m", f"{v100:.1f} m/s" if v100 is not None else "—")
    with c6:
        st.metric(
            "Rafagas / Shear α",
            f"{gusts:.1f} m/s" if gusts is not None else "—",
            delta=f"α = {alpha:.3f}" if alpha is not None else None,
        )

    st.caption(
        "Generacion: ultimo gen_real CEN · Cap. instalada: Pmax declarada · "
        "FP = Gen/Cap × 100 · Desvio = (Gen − PCP)/PCP × 100 a la misma hora · "
        "Viento 100m: interpolado v80/v120 con ley de potencia v(h)=v_ref·(h/h_ref)^α · "
        "Rafagas: maximas a 10m (cut-out ~20 m/s) · Shear α>0.30 → atmosfera estable."
    )


def render_tab_eolica(
    gen_por_parque: dict,
    prog_por_parque: dict,
    gen_rows: list,
    prog_rows: list,
    parque_activo: str | None = None,
) -> None:
    _ventanas = [24, 48, 72, 168]

    # Selección de parque: el sidebar fuerza el selectbox una sola vez (one-shot);
    # luego el desplegable es dueño de su estado y el usuario puede cambiarlo libremente.
    _sync = st.session_state.pop("_sync_parque", None)
    if _sync in PARQUES_EOLICA:
        st.session_state["eolica_parque_sel"] = _sync
    if st.session_state.get("eolica_parque_sel") not in PARQUES_EOLICA:
        st.session_state["eolica_parque_sel"] = (
            parque_activo if parque_activo in PARQUES_EOLICA else PARQUES_EOLICA[0]
        )
    if st.session_state.get("eolica_ventana_horas") not in _ventanas:
        st.session_state["eolica_ventana_horas"] = 168

    # KPIs resaltan el parque actualmente seleccionado (coherente con el gráfico)
    _kpis_eolica(gen_por_parque, prog_por_parque, st.session_state["eolica_parque_sel"])
    st.divider()

    parque_sel = st.selectbox(
        "Parque eolico",
        PARQUES_EOLICA,
        format_func=lambda p: NOMBRE_DISPLAY[p],
        key="eolica_parque_sel",
    )
    horas_ventana = st.selectbox(
        "Ventana",
        _ventanas,
        format_func=lambda h: "Ultima semana" if h == 168 else f"Ultimas {h} h",
        key="eolica_ventana_horas",
    )

    corte_meteo = pd.Timestamp.now() - pd.Timedelta(hours=horas_ventana)

    df_meteo = _df_meteo(parque_sel)
    if not df_meteo.empty:
        df_meteo = df_meteo[df_meteo["fecha_hora"] >= corte_meteo]

    nombre_ventana = "ultima semana" if horas_ventana == 168 else f"ultimas {horas_ventana} h"
    grafico_container = st.container()
    with grafico_container:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:6px'>"
            f"Generacion — {NOMBRE_DISPLAY[parque_sel]} ({nombre_ventana})</div>",
            unsafe_allow_html=True,
        )
        _grafico_gen(gen_rows, prog_rows, df_meteo, parque_sel, horas_ventana)

    # ── Métricas entre los dos gráficos ──
    _panel_metricas(gen_rows, prog_rows, df_meteo, parque_sel)

    # ── Segunda serie de tiempo: viento + shear (antes que leyenda/fórmulas) ──
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:10px 0 6px'>"
        f"Velocidad de viento — {NOMBRE_DISPLAY[parque_sel]}</div>",
        unsafe_allow_html=True,
    )
    _grafico_viento(df_meteo, parque_sel, corte_meteo)

    # ── Glosario de series — al final, tras los gráficos ──
    st.markdown(
        f"""<div style='background:{AES_BLANCO};border:1px solid {AES_BORDE};border-radius:10px;
padding:14px 20px;margin:10px 0 14px;font-size:11.5px;color:{AES_TEXTO};line-height:1.7'>
<div style='font-size:11px;font-weight:700;color:{AES_MUTED};text-transform:uppercase;
letter-spacing:0.8px;margin-bottom:10px'>Leyenda de series</div>
<div style='display:grid;grid-template-columns:1fr 1fr;gap:6px 24px'>
  <div><span style='display:inline-block;width:28px;height:3px;background:{AES_CYAN};
  vertical-align:middle;margin-right:7px;border-radius:2px'></span>
  <b>Generacion real</b> — medicion CEN hora a hora (gen-real/v3). Negativos filtrados.</div>
  <div><span style='display:inline-block;width:28px;height:2px;background:#D97706;
  vertical-align:middle;margin-right:7px;border-bottom:2px dashed #D97706'></span>
  <b>PCP programada</b> — potencia declarada D-1 ante el Coordinador (SIPUB pcp/v4).</div>
  <div><span style='display:inline-block;width:28px;height:1px;background:{AES_VIOLETA};
  vertical-align:middle;margin-right:7px;border-bottom:2px dotted {AES_VIOLETA}'></span>
  <b>Modelo eolico</b> — curva de potencia con cut-in/rated/cut-out
  (fórmulas en el panel inferior). v = viento a 100m (hub).</div>
  <div><span style='display:inline-block;width:28px;height:3px;background:{AES_MUTED};
  vertical-align:middle;margin-right:7px;border-radius:2px'></span>
  <b>Viento 10m</b> — velocidad a 10m (Open-Meteo windspeed_10m) [m/s].</div>
  <div><span style='display:inline-block;width:28px;height:3px;background:{AES_CYAN};
  vertical-align:middle;margin-right:7px;border-radius:2px'></span>
  <b>Viento 100m (hub)</b> — interpolado de v80m+v120m con ley de potencia:
  v(h)=v_ref×(h/h_ref)^α [m/s].</div>
  <div><span style='display:inline-block;width:28px;height:2px;background:{AES_ROJO};
  vertical-align:middle;margin-right:7px;border-bottom:2px dashed {AES_ROJO}'></span>
  <b>Rafagas 10m</b> — maximas en [m/s]. Cut-out tipico ~20 m/s.</div>
  <div><span style='display:inline-block;width:28px;height:2px;background:{AES_VIOLETA};
  vertical-align:middle;margin-right:7px;border-bottom:2px dotted {AES_VIOLETA}'></span>
  <b>Wind shear α</b> — exponente ley de potencia perfil vertical.
  α&gt;0.30 → atm. estable, estelas mas persistentes.</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    with st.expander("Fórmulas del modelo eólico"):
        st.markdown("**Interpolación de viento al hub (100 m) y cizalle vertical**")
        st.latex(r"\alpha \;=\; \frac{\ln\!\left(v_{120}/v_{80}\right)}{\ln\!\left(120/80\right)}"
                 r"\qquad v_{100} \;=\; v_{80}\left(\frac{100}{80}\right)^{\!\alpha}")
        st.markdown("**Densidad del aire**")
        st.latex(r"\rho \;=\; \frac{P}{R\,T}\quad\left[\mathrm{kg/m^3}\right],\quad R = 287.05\ \mathrm{J/(kg\cdot K)}")
        st.markdown("**Curva de potencia de la turbina**")
        st.latex(r"P(v) = \begin{cases} 0 & v < v_{in}\ \text{o}\ v > v_{out} \\[4pt]"
                 r"P_{max}\,\dfrac{v^3 - v_{in}^3}{v_{rated}^3 - v_{in}^3}\,\dfrac{\rho}{\rho_{ref}} & v_{in} \le v < v_{rated} \\[8pt]"
                 r"P_{max}\,\dfrac{\rho}{\rho_{ref}} & v_{rated} \le v \le v_{out} \end{cases}")
        st.markdown(
            f"<div style='font-size:11.5px;color:{AES_MUTED};line-height:1.7'>"
            r"$v_{in}=3$, $v_{rated}=12$, $v_{out}=25\ \mathrm{m/s}$ &nbsp;·&nbsp; "
            r"$\rho_{ref}=1.225\ \mathrm{kg/m^3}$ &nbsp;·&nbsp; "
            r"$\alpha$ acotado a $[-0.10,\ 0.60]$; sobre $v_{out}$ la turbina se detiene por seguridad."
            "</div>",
            unsafe_allow_html=True,
        )
