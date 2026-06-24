"""Tab Forecast — tema claro, paleta AES, sin emojis, mensaje claro si no hay datos."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone

from config import NOMBRE_DISPLAY, PMAX, TECNOLOGIA, PARQUES_SOLAR, PARQUES_EOLICA, PARQUES_TODOS

AES_AZUL    = "#3B4CE8"
AES_CYAN    = "#4DC8DC"
AES_VIOLETA = "#9B6FD4"
AES_VERDE   = "#5AB848"
AES_AMBAR   = "#F59E0B"
AES_GRIS    = "#F5F7FA"
AES_BORDE   = "#E5E7EB"
AES_BLANCO  = "#FFFFFF"
AES_TEXTO   = "#1A1F36"
AES_MUTED   = "#6B7280"


@st.cache_data(ttl=1800)
def _cargar_forecast() -> pd.DataFrame:
    try:
        from utils.db import get_client
        sb = get_client()
        santiago = timezone(timedelta(hours=-3))
        ahora = datetime.now(santiago).strftime("%Y-%m-%d %H:%M:%S")
        hasta = (datetime.now(santiago) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        res = (
            sb.table("meteo_ernc")
            .select(
                "parque,fecha_hora,p_fv_estimada_mw,p_eolica_estimada_mw,"
                "ghi_wm2,wind_speed_100m,cloud_cover_pct,wind_gusts_10m,es_forecast"
            )
            .eq("es_forecast", True)
            .gte("fecha_hora", ahora)
            .lte("fecha_hora", hasta)
            .order("fecha_hora")
            .execute()
        )
        if res.data:
            df = pd.DataFrame(res.data)
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
            df["tecnologia"] = df["parque"].map(TECNOLOGIA)
            return df
    except Exception as e:
        st.warning(f"Error cargando forecast: {e}")
    return pd.DataFrame()


def _tabla_diaria(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["fecha"] = df["fecha_hora"].dt.date
    df["p_solar"]  = df.apply(lambda r: r["p_fv_estimada_mw"]     if r["tecnologia"] == "Solar"  else 0, axis=1)
    df["p_eolica"] = df.apply(lambda r: r["p_eolica_estimada_mw"] if r["tecnologia"] == "Eólica" else 0, axis=1)
    agg = df.groupby("fecha").agg(solar_mwh=("p_solar", "sum"), eolica_mwh=("p_eolica", "sum")).reset_index()
    agg["total_mwh"] = agg["solar_mwh"] + agg["eolica_mwh"]
    agg["fecha"] = pd.to_datetime(agg["fecha"]).dt.strftime("%a %d/%m")
    agg.rename(columns={"fecha": "Dia", "solar_mwh": "Solar FV (MWh)", "eolica_mwh": "Eolica (MWh)", "total_mwh": "Total (MWh)"}, inplace=True)
    for col in ["Solar FV (MWh)", "Eolica (MWh)", "Total (MWh)"]:
        agg[col] = agg[col].round(0).astype(int)
    return agg


def _grafico_portfolio(df: pd.DataFrame, ml_total: pd.DataFrame | None = None) -> None:
    df_solar  = df[df["tecnologia"] == "Solar"].groupby("fecha_hora")["p_fv_estimada_mw"].sum().reset_index()
    df_eolica = df[df["tecnologia"] == "Eólica"].groupby("fecha_hora")["p_eolica_estimada_mw"].sum().reset_index()
    df_solar.columns  = ["fecha_hora", "mw"]
    df_eolica.columns = ["fecha_hora", "mw"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_eolica["fecha_hora"], y=df_eolica["mw"],
        name="Eolica estimada", fill="tozeroy",
        line=dict(color=AES_CYAN, width=1.5),
        fillcolor="rgba(77,200,220,0.20)",
        hovertemplate="%{y:.0f} MW<extra>Eolica estimada</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df_solar["fecha_hora"], y=df_solar["mw"],
        name="Solar FV estimada", fill="tozeroy",
        line=dict(color=AES_AZUL, width=1.5),
        fillcolor="rgba(59,76,232,0.18)",
        hovertemplate="%{y:.0f} MW<extra>Solar FV estimada</extra>",
    ))
    if ml_total is not None and not ml_total.empty:
        fig.add_trace(go.Scatter(
            x=ml_total["fecha_hora"], y=ml_total["ml_mw"],
            name="Total ML (data-driven)",
            line=dict(color=AES_VIOLETA, width=2, dash="dash"),
            hovertemplate="%{y:.0f} MW<extra>Total ML</extra>",
        ))
    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS, transition=dict(duration=500, easing="cubic-in-out"),
        height=380, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None, yaxis_title="MW",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE, rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True, key="forecast_grafico_portfolio")


@st.cache_data(ttl=1800)
def _ml_forecast_parque(parque: str) -> tuple[pd.DataFrame, dict]:
    """Pronóstico ML (RandomForest) para un parque: entrena meteo→gen_real histórico
    y predice sobre el forecast Open-Meteo. Devuelve ([fecha_hora, ml_mw], métricas).
    Las métricas (R², MAE, n) salen de un holdout aleatorio 80/20 para indicar la
    confiabilidad del modelo. Usa solo features disponibles en el forecast."""
    import numpy as np
    vacio = (pd.DataFrame(), {})
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import r2_score, mean_absolute_error
        from utils.db import get_client
    except Exception:
        return vacio
    tec = TECNOLOGIA[parque]
    feats = ["ghi_wm2", "cloud_cover_pct"] if tec == "Solar" else ["wind_speed_100m", "wind_gusts_10m"]
    sb = get_client()
    santiago = timezone(timedelta(hours=-3))
    desde = (datetime.now(santiago) - timedelta(days=45)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        sel = "fecha_hora," + ",".join(feats)
        mh = (sb.table("meteo_ernc").select(sel)
              .eq("parque", parque).eq("es_forecast", False)
              .gte("fecha_hora", desde).order("fecha_hora").execute())
        gh = (sb.table("generacion_real_ernc").select("fecha_hora,gen_real_mw")
              .eq("parque", parque).gte("fecha_hora", desde).order("fecha_hora").execute())
    except Exception:
        return vacio
    if not mh.data or not gh.data:
        return vacio
    dm = pd.DataFrame(mh.data); dg = pd.DataFrame(gh.data)
    dm["fecha_hora"] = pd.to_datetime(dm["fecha_hora"])
    dg["fecha_hora"] = pd.to_datetime(dg["fecha_hora"])
    d = dm.merge(dg, on="fecha_hora", how="inner").dropna(subset=feats + ["gen_real_mw"])
    d = d[d["gen_real_mw"] >= 0]
    if len(d) < 48:
        return vacio
    d["hora_dia"] = d["fecha_hora"].dt.hour
    cols = feats + ["hora_dia"]
    X, y = d[cols].values, d["gen_real_mw"].values

    # Métricas de confiabilidad con holdout aleatorio
    metrics = {}
    try:
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
        mt = RandomForestRegressor(n_estimators=160, max_depth=12, random_state=42, n_jobs=-1)
        mt.fit(Xtr, ytr)
        pte = np.clip(mt.predict(Xte), 0, PMAX[parque])
        metrics = {"r2": float(r2_score(yte, pte)), "mae": float(mean_absolute_error(yte, pte)),
                   "n": int(len(d))}
    except Exception:
        metrics = {"n": int(len(d))}

    # Modelo final con todo el histórico para predecir el forecast
    m = RandomForestRegressor(n_estimators=160, max_depth=12, random_state=42, n_jobs=-1)
    m.fit(X, y)

    fc = _cargar_forecast()
    fc = fc[fc["parque"] == parque].copy()
    if fc.empty or any(c not in fc.columns for c in feats):
        return (pd.DataFrame(), metrics)
    fc = fc.dropna(subset=feats)
    if fc.empty:
        return (pd.DataFrame(), metrics)
    fc["hora_dia"] = fc["fecha_hora"].dt.hour
    pred = np.clip(m.predict(fc[cols].values), 0, PMAX[parque])
    return (pd.DataFrame({"fecha_hora": fc["fecha_hora"].values, "ml_mw": pred}), metrics)


@st.cache_data(ttl=1800)
def _ml_portfolio_total() -> pd.DataFrame:
    """Suma el pronóstico ML de todos los parques por hora → banda data-driven del
    portfolio para comparar contra el modelo físico en el horizonte de 7 días."""
    acc = None
    for p in PARQUES_TODOS:
        ml, _ = _ml_forecast_parque(p)
        if ml.empty:
            continue
        ml = ml.rename(columns={"ml_mw": p}).set_index("fecha_hora")
        acc = ml if acc is None else acc.join(ml, how="outer")
    if acc is None or acc.empty:
        return pd.DataFrame()
    total = acc.sum(axis=1, min_count=1).reset_index()
    total.columns = ["fecha_hora", "ml_mw"]
    return total.dropna()


def _grafico_parque(df: pd.DataFrame, parque: str, con_ml: bool = False) -> None:
    tec  = TECNOLOGIA[parque]
    df_p = df[df["parque"] == parque].sort_values("fecha_hora")
    if df_p.empty:
        st.info("Sin datos forecast para este parque.")
        return

    y_col   = "p_fv_estimada_mw"     if tec == "Solar"  else "p_eolica_estimada_mw"
    y2_col  = "ghi_wm2"              if tec == "Solar"  else "wind_speed_100m"
    y2_lbl  = "GHI (W/m²)"          if tec == "Solar"  else "Viento 100m (m/s)"
    color   = AES_AZUL               if tec == "Solar"  else AES_CYAN
    fill_c  = "rgba(59,76,232,0.10)" if tec == "Solar"  else "rgba(77,200,220,0.12)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_p["fecha_hora"], y=df_p[y_col],
        name="Modelo físico",
        fill="tozeroy", fillcolor=fill_c,
        line=dict(color=color, width=2),
        hovertemplate="%{y:.1f} MW<extra>Modelo físico</extra>",
    ))
    metrics = {}
    if con_ml:
        ml, metrics = _ml_forecast_parque(parque)
        if not ml.empty:
            fig.add_trace(go.Scatter(
                x=ml["fecha_hora"], y=ml["ml_mw"],
                name="Modelo ML",
                line=dict(color=AES_VIOLETA, width=2, dash="dash"),
                hovertemplate="%{y:.1f} MW<extra>Modelo ML</extra>",
            ))
    if y2_col in df_p.columns:
        fig.add_trace(go.Scatter(
            x=df_p["fecha_hora"], y=df_p[y2_col],
            name=y2_lbl, yaxis="y2",
            line=dict(color=AES_MUTED, width=1, dash="dot"),
            hovertemplate=f"%{{y:.1f}}<extra>{y2_lbl}</extra>",
        ))
    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS, transition=dict(duration=500, easing="cubic-in-out"),
        height=320, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None, yaxis_title="MW",
        yaxis2=dict(overlaying="y", side="right", showgrid=False, title=y2_lbl),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE, rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True, key=f"forecast_grafico_parque_{parque}")
    return metrics


def render_tab_forecast() -> None:
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:12px'>"
        f"Forecast de produccion — proximos 7 dias</div>",
        unsafe_allow_html=True,
    )

    df = _cargar_forecast()

    if df.empty:
        st.markdown(
            f"<div style='background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;"
            f"padding:16px 20px;color:#92400E'>"
            f"<div style='font-weight:600;font-size:13px;margin-bottom:6px'>"
            f"Sin datos de forecast disponibles</div>"
            f"<div style='font-size:12px;line-height:1.6'>"
            f"La tabla <code>meteo_ernc</code> no contiene registros futuros (es_forecast=True).<br>"
            f"Para poblarla, ejecuta localmente:<br>"
            f"<code style='background:#FEF3C7;padding:2px 6px;border-radius:3px'>"
            f"python Adquisicion_meteo_ernc.py</code><br>"
            f"o espera al proximo cron de GitHub Actions (cada hora, minuto :20)."
            f"</div></div>",
            unsafe_allow_html=True,
        )
        return

    # KPIs 7 dias
    solar_tot  = df[df["tecnologia"] == "Solar"]["p_fv_estimada_mw"].sum()
    eolica_tot = df[df["tecnologia"] == "Eólica"]["p_eolica_estimada_mw"].sum()
    total_mwh  = solar_tot + eolica_tot

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "Solar FV — 7 dias",
            f"{solar_tot:,.0f} MWh",
        )
    with c2:
        st.metric(
            "Eolica — 7 dias",
            f"{eolica_tot:,.0f} MWh",
        )
    with c3:
        st.metric(
            "Total portfolio",
            f"{total_mwh:,.0f} MWh",
        )

    st.divider()
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
        f"Potencia estimada portfolio — hora a hora</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Pronostico = modelo fisico propio aplicado al forecast meteorologico Open-Meteo "
        "(7 dias). Reemplaza a la PCP del Coordinador, que solo se publica hasta el dia "
        "siguiente y no cubre el horizonte de 7 dias."
    )
    con_ml_portf = st.checkbox(
        "Superponer pronóstico ML del portfolio (RandomForest entrenado con la generación real reciente)",
        value=False, key="fcst_portfolio_ml",
    )
    ml_total = None
    if con_ml_portf:
        with st.spinner("Entrenando modelos ML por parque..."):
            ml_total = _ml_portfolio_total()
        if ml_total is not None and not ml_total.empty:
            ml_mwh = float(ml_total["ml_mw"].sum())
            delta = ml_mwh - total_mwh
            st.metric(
                "Total ML — 7 dias",
                f"{ml_mwh:,.0f} MWh",
                delta=f"{delta:+,.0f} MWh vs modelo físico",
            )
            st.caption(
                "Si el ML proyecta menos que el modelo físico, este último puede estar "
                "sobreestimando (p. ej. limitaciones o disponibilidad real no capturadas)."
            )
        else:
            st.info("Sin suficiente histórico para el modelo ML del portfolio (se necesitan ≥48 h por parque).")
    _grafico_portfolio(df, ml_total=ml_total)

    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:16px 0 8px'>"
        f"Produccion estimada por dia</div>",
        unsafe_allow_html=True,
    )
    df_dia = _tabla_diaria(df)
    if not df_dia.empty:
        st.dataframe(df_dia, hide_index=True, use_container_width=True)

    st.divider()
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:8px'>"
        f"Detalle por parque</div>",
        unsafe_allow_html=True,
    )

    col_tipo, col_parque = st.columns([1, 3])
    with col_tipo:
        tipo_sel = st.radio("Tecnologia", ["Solar FV", "Eolica"], horizontal=False, key="fcst_tipo")
    parques_disp = PARQUES_SOLAR if tipo_sel == "Solar FV" else PARQUES_EOLICA
    with col_parque:
        parque_sel = st.selectbox(
            "Parque",
            parques_disp,
            format_func=lambda p: NOMBRE_DISPLAY[p],
            key="fcst_parque",
        )
    con_ml = st.checkbox("Comparar con modelo ML (entrena con histórico real del parque)",
                         value=False, key="fcst_con_ml")
    metrics = _grafico_parque(df, parque_sel, con_ml=con_ml)
    if con_ml:
        if metrics and "r2" in metrics:
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                st.metric("R² del modelo ML", f"{metrics['r2']:.2f}")
            with mc2:
                st.metric("MAE (error medio)", f"{metrics['mae']:.1f} MW")
            with mc3:
                st.metric("Horas de entrenamiento", f"{metrics['n']:,}")
            calidad = ("alta" if metrics["r2"] >= 0.85 else
                       "media" if metrics["r2"] >= 0.6 else "baja")
            st.caption(
                f"Confiabilidad **{calidad}** (R²={metrics['r2']:.2f}, holdout 80/20). "
                "Modelo físico = estimación por irradiancia/viento. Modelo ML = RandomForest "
                "entrenado con la generación real reciente del parque vs su meteo. Si difieren "
                "mucho, el modelo físico puede estar sesgado para este parque."
            )
        else:
            st.caption(
                "Sin histórico suficiente para entrenar el modelo ML de este parque "
                "(se necesitan ≥48 h de generación real con meteo)."
            )
