"""Tab ML Analysis — modelos predictivos y analítica sobre los datos ERNC.

Cuatro análisis:
  1. Forecast de generación  — RandomForest meteo→gen, comparado con el modelo físico.
  2. Detección de anomalías  — residuos del modelo + IsolationForest sobre el clima.
  3. Predicción de CMG        — RandomForest con rezagos (lags) por nodo.
  4. Análisis de eficiencia   — performance ratio real/teórico + clustering de condiciones.

Sub-navegación con radio (no st.tabs) para que cada gráfico Plotly se monte siempre
en un contenedor visible y a ancho real.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone

from config import (
    NOMBRE_DISPLAY, PMAX, PMAX_FP, PARQUES_SOLAR, PARQUES_EOLICA, PARQUES_TODOS,
    TECNOLOGIA, CMG_NODOS_TODOS, BESS, BESS_HORAS, CMG_NODO,
)

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

SANTIAGO = timezone(timedelta(hours=-3))

FEATURES_SOLAR = [
    "ghi_wm2", "gti_wm2", "temp_2m", "temp_celda_c",
    "cloud_cover_pct", "cloudcover_low_pct", "hora_dia",
]
FEATURES_EOLICA = [
    "wind_speed_100m", "wind_speed_10m", "wind_gusts_10m",
    "densidad_aire", "wind_shear_alpha", "hora_dia",
]

try:
    from sklearn.ensemble import RandomForestRegressor, IsolationForest
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import r2_score, mean_absolute_error
    _SKLEARN = True
except Exception:
    _SKLEARN = False


# ── Layout helpers ───────────────────────────────────────────────────────────

def _titulo(txt: str, margin: str = "4px 0 8px") -> None:
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:{margin}'>{txt}</div>",
        unsafe_allow_html=True,
    )


def _layout_base(fig, height=340):
    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
        height=height, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    return fig


# ── Carga de datos ───────────────────────────────────────────────────────────

@st.cache_data(ttl=900)
def _dataset_parque(parque: str, dias: int = 25) -> pd.DataFrame:
    """meteo histórico (es_forecast=False) ⋈ gen_real por hora para un parque."""
    from utils.db import get_client
    sb = get_client()
    desde = (datetime.now(SANTIAGO) - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        m = (sb.table("meteo_ernc").select("*")
             .eq("parque", parque).eq("es_forecast", False)
             .gte("fecha_hora", desde).order("fecha_hora").execute())
        g = (sb.table("generacion_real_ernc").select("fecha_hora,gen_real_mw")
             .eq("parque", parque).gte("fecha_hora", desde)
             .order("fecha_hora").execute())
    except Exception:
        return pd.DataFrame()
    if not m.data or not g.data:
        return pd.DataFrame()
    dm = pd.DataFrame(m.data)
    dg = pd.DataFrame(g.data)
    df = dm.merge(dg, on="fecha_hora", how="inner")
    if df.empty:
        return df
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    df["hora_dia"] = df["fecha_hora"].dt.hour
    df = df[df["gen_real_mw"].notna() & (df["gen_real_mw"] >= 0)]
    return df


@st.cache_data(ttl=900)
def _forecast_meteo_parque(parque: str) -> pd.DataFrame:
    from utils.db import get_client
    sb = get_client()
    ahora = datetime.now(SANTIAGO).strftime("%Y-%m-%d %H:%M:%S")
    hasta = (datetime.now(SANTIAGO) + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        r = (sb.table("meteo_ernc").select("*")
             .eq("parque", parque).eq("es_forecast", True)
             .gte("fecha_hora", ahora).lte("fecha_hora", hasta)
             .order("fecha_hora").execute())
    except Exception:
        return pd.DataFrame()
    if not r.data:
        return pd.DataFrame()
    df = pd.DataFrame(r.data)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    df["hora_dia"] = df["fecha_hora"].dt.hour
    return df


@st.cache_data(ttl=900)
def _cmg_historico(nodo: str, dias: int = 20) -> pd.DataFrame:
    from utils.db import get_client
    sb = get_client()
    desde = (datetime.now(SANTIAGO) - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        r = (sb.table("cmg_ernc").select("fecha_hora,cmg_usd_mwh")
             .eq("nodo", nodo).gte("fecha_hora", desde)
             .order("fecha_hora").execute())
    except Exception:
        return pd.DataFrame()
    if not r.data:
        return pd.DataFrame()
    df = pd.DataFrame(r.data)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    df = df.drop_duplicates("fecha_hora").sort_values("fecha_hora")
    return df


@st.cache_data(ttl=900)
def _cmg_programado_hist(nodo: str, dias_atras: int = 20) -> pd.DataFrame:
    """CMG programado PCP del nodo: cobertura horaria densa (pasado reciente + futuro).
    Sirve de fuente de CMG para el arbitraje BESS (el online S3 es muy escaso)."""
    from utils.db import get_client
    sb = get_client()
    desde = (datetime.now(SANTIAGO) - timedelta(days=dias_atras)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        r = (sb.table("cmg_programado_ernc").select("fecha_hora,cmg_usd_mwh")
             .eq("nodo", nodo).gte("fecha_hora", desde)
             .order("fecha_hora").execute())
    except Exception:
        return pd.DataFrame()
    if not r.data:
        return pd.DataFrame()
    df = pd.DataFrame(r.data)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df.drop_duplicates("fecha_hora").sort_values("fecha_hora")


def _feats_disponibles(df: pd.DataFrame, tec: str) -> list[str]:
    base = FEATURES_SOLAR if tec == "Solar" else FEATURES_EOLICA
    return [f for f in base if f in df.columns and df[f].notna().any()]


# ── 1. Forecast de generación ─────────────────────────────────────────────────

def _render_forecast_gen(parque: str) -> None:
    tec = TECNOLOGIA[parque]
    df = _dataset_parque(parque)
    if df.empty or len(df) < 48:
        st.info("Datos insuficientes para entrenar (se necesitan ≥48 horas con meteo+gen). "
                "Corre la adquisición para poblar el histórico.")
        return

    feats = _feats_disponibles(df, tec)
    d = df.dropna(subset=feats + ["gen_real_mw"])
    if len(d) < 48:
        st.info("Datos insuficientes tras limpiar valores faltantes.")
        return

    with st.expander("¿Cómo se calcula esta predicción? (metodología)"):
        st.markdown(
            "**Modelo:** Random Forest Regressor (160 árboles) — un *ensemble* que promedia "
            "muchos árboles de decisión sobre submuestras, robusto a relaciones no lineales "
            "entre clima y generación.\n\n"
            "**Entradas:** GHI, GTI, temperatura, temperatura de celda, nubosidad y hora del día "
            "(solar); viento 100m/10m, ráfagas, densidad del aire, cizalle y hora (eólico).\n\n"
            "**Objetivo:** generación real horaria (MW) del CEN.\n\n"
            "**Validación:** partición aleatoria 80/20. La generación de cada hora depende del "
            "clima *de esa misma hora*, no de su pasado, por lo que la partición aleatoria es la "
            "métrica correcta. Una partición cronológica daba R² negativos engañosos cuando el "
            "tramo final caía en un régimen meteorológico distinto al del entrenamiento.\n\n"
            "**Métricas:** R² (varianza explicada, 1.0 = perfecto, <0 = peor que la media) y MAE "
            "(error absoluto medio en MW)."
        )

    from sklearn.model_selection import train_test_split
    X = d[feats].values
    y = d["gen_real_mw"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=160, max_depth=12, min_samples_leaf=2,
                                  random_state=42, n_jobs=-1)
    model.fit(Xtr, ytr)
    pred_te = np.clip(model.predict(Xte), 0, PMAX[parque])
    r2 = r2_score(yte, pred_te)
    mae = mean_absolute_error(yte, pred_te)

    c1, c2, c3 = st.columns(3)
    c1.metric("R² (test)", f"{r2:.3f}")
    c2.metric("MAE", f"{mae:.2f} MW")
    c3.metric("Registros entrenamiento", f"{len(Xtr)}")
    if r2 < 0.4:
        st.warning("R² bajo: poco histórico todavía o recurso muy variable en este parque. "
                   "Mejora a medida que se acumulan horas de datos meteo+generación.")

    # Modelo entrenado sobre todo el set para predecir el forecast meteo
    model_full = RandomForestRegressor(n_estimators=160, max_depth=12, min_samples_leaf=2,
                                       random_state=42, n_jobs=-1)
    model_full.fit(X, y)

    _titulo(f"Predicción ML vs real (backtest cronológico) — {NOMBRE_DISPLAY[parque]}", "12px 0 6px")
    n_vis = min(len(d), max(48, int(len(d) * 0.25)))
    d_vis = d.iloc[-n_vis:]
    pred_vis = np.clip(model_full.predict(d_vis[feats].values), 0, PMAX[parque])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d_vis["fecha_hora"], y=d_vis["gen_real_mw"], name="Gen. real",
                             line=dict(color=AES_AZUL, width=2.5)))
    fig.add_trace(go.Scatter(x=d_vis["fecha_hora"], y=pred_vis, name="Predicción ML",
                             line=dict(color=AES_VERDE, width=2, dash="dot")))
    col_fis = "p_fv_estimada_mw" if tec == "Solar" else "p_eolica_estimada_mw"
    if col_fis in d_vis.columns:
        fig.add_trace(go.Scatter(x=d_vis["fecha_hora"], y=d_vis[col_fis], name="Modelo físico",
                                 line=dict(color=AES_VIOLETA, width=1.2, dash="dash")))
    st.plotly_chart(_layout_base(fig), use_container_width=True, key=f"ml_fc_test_{parque}")

    # Aplicar al forecast meteo futuro
    dff = _forecast_meteo_parque(parque)
    if not dff.empty:
        feats_f = [f for f in feats if f in dff.columns]
        if set(feats_f) == set(feats) and dff[feats].notna().all(axis=1).any():
            dfx = dff.dropna(subset=feats).copy()
            dfx["pred_ml"] = np.clip(model_full.predict(dfx[feats].values), 0, PMAX[parque])
            _titulo(f"Pronóstico ML de generación — próximos días", "16px 0 6px")
            figf = go.Figure()
            figf.add_trace(go.Scatter(x=dfx["fecha_hora"], y=dfx["pred_ml"], name="Pronóstico ML",
                                      line=dict(color=AES_VERDE, width=2), fill="tozeroy",
                                      fillcolor="rgba(90,184,72,0.10)"))
            if col_fis in dfx.columns:
                figf.add_trace(go.Scatter(x=dfx["fecha_hora"], y=dfx[col_fis], name="Modelo físico",
                                          line=dict(color=AES_VIOLETA, width=1.2, dash="dash")))
            st.plotly_chart(_layout_base(figf), use_container_width=True, key=f"ml_fc_fut_{parque}")

    # Importancia de variables
    _titulo("Importancia de variables", "16px 0 6px")
    imp = pd.DataFrame({"var": feats, "imp": model_full.feature_importances_}).sort_values("imp")
    figi = go.Figure(go.Bar(x=imp["imp"], y=imp["var"], orientation="h",
                            marker_color=AES_AZUL))
    figi.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                       height=240, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Importancia relativa")
    figi.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(figi, use_container_width=True, key=f"ml_fc_imp_{parque}")


# ── 2. Detección de anomalías ──────────────────────────────────────────────────

def _render_anomalias(parque: str) -> None:
    tec = TECNOLOGIA[parque]
    df = _dataset_parque(parque)
    if df.empty or len(df) < 48:
        st.info("Datos insuficientes para detectar anomalías (≥48 horas meteo+gen).")
        return

    feats = _feats_disponibles(df, tec)
    d = df.dropna(subset=feats + ["gen_real_mw"]).copy()
    if len(d) < 48:
        st.info("Datos insuficientes tras limpiar faltantes.")
        return

    with st.expander("¿Cómo se detectan las anomalías? (metodología)"):
        st.markdown(
            "Se combinan **dos enfoques complementarios**:\n\n"
            "1. **Residuo del modelo:** se entrena un Random Forest clima→generación y se calcula "
            "el residuo (real − esperado). Se estandariza a *z-score*; |z| > 3 marca horas donde la "
            "generación se aleja >3σ de lo que el clima predecía (posible falla, limitación o "
            "curtailment).\n"
            "2. **Isolation Forest:** algoritmo no supervisado que aísla combinaciones raras de "
            "clima+generación (contaminación 5%). Detecta patrones atípicos aunque el residuo sea "
            "moderado.\n\n"
            "Una hora es anómala si **cualquiera** de los dos criterios la marca."
        )

    # Residuos del modelo: gen real vs esperado dado el clima (validación cruzada simple)
    model = RandomForestRegressor(n_estimators=160, max_depth=12, min_samples_leaf=2,
                                  random_state=42, n_jobs=-1)
    model.fit(d[feats].values, d["gen_real_mw"].values)
    d["esperado"] = model.predict(d[feats].values)
    d["residuo"] = d["gen_real_mw"] - d["esperado"]
    sigma = d["residuo"].std() or 1.0
    d["z"] = d["residuo"] / sigma

    # IsolationForest sobre features + gen para marcar combinaciones raras
    iso = IsolationForest(contamination=0.05, random_state=42)
    Xa = StandardScaler().fit_transform(d[feats + ["gen_real_mw"]].values)
    d["iso"] = iso.fit_predict(Xa)  # -1 = anómalo

    d["anomalo"] = (d["z"].abs() > 3) | (d["iso"] == -1)
    n_anom = int(d["anomalo"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Horas analizadas", f"{len(d)}")
    c2.metric("Anomalías detectadas", f"{n_anom}")
    c3.metric("σ residuo", f"{sigma:.2f} MW")

    _titulo(f"Generación real con anomalías marcadas — {NOMBRE_DISPLAY[parque]}", "12px 0 6px")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["fecha_hora"], y=d["esperado"], name="Esperado (modelo)",
                             line=dict(color=AES_VIOLETA, width=1.2, dash="dot")))
    fig.add_trace(go.Scatter(x=d["fecha_hora"], y=d["gen_real_mw"], name="Gen. real",
                             line=dict(color=AES_CYAN, width=2)))
    da = d[d["anomalo"]]
    if not da.empty:
        fig.add_trace(go.Scatter(x=da["fecha_hora"], y=da["gen_real_mw"], name="Anomalía",
                                 mode="markers", marker=dict(color=AES_ROJO, size=9, symbol="x")))
    st.plotly_chart(_layout_base(fig), use_container_width=True, key=f"ml_anom_{parque}")

    if n_anom:
        _titulo("Detalle de anomalías", "12px 0 6px")
        cols = ["fecha_hora", "gen_real_mw", "esperado", "residuo", "z"]
        tabla = da[cols].copy().sort_values("z", key=lambda s: s.abs(), ascending=False).head(30)
        tabla["fecha_hora"] = tabla["fecha_hora"].dt.strftime("%d/%m %H:%M")
        for c in ["gen_real_mw", "esperado", "residuo", "z"]:
            tabla[c] = tabla[c].round(2)
        tabla.columns = ["Hora", "Real MW", "Esperado MW", "Residuo MW", "z-score"]
        st.dataframe(tabla, hide_index=True, use_container_width=True)


# ── 3. Predicción de CMG ────────────────────────────────────────────────────────

def _render_cmg(nodo: str) -> None:
    df = _cmg_historico(nodo)
    if df.empty or len(df) < 48:
        st.info("Histórico de CMG insuficiente para este nodo (≥48 registros). "
                "Algunos nodos publican con menor frecuencia.")
        return

    with st.expander("¿Cómo se predice el CMG? (metodología)"):
        st.markdown(
            "El costo marginal es una **serie temporal** con fuerte autocorrelación y patrón "
            "diario. Por eso, a diferencia de la generación, **sí** se modela con su propio pasado:\n\n"
            "**Features:** rezagos (*lags*) del CMG a 1, 2, 3, 6, 12 y 24 horas + la hora del día.\n\n"
            "**Modelo:** Random Forest (200 árboles) que aprende cómo el precio futuro depende de "
            "esos rezagos.\n\n"
            "**Validación:** partición **cronológica** 80/20 (aquí sí corresponde, porque el orden "
            "temporal importa).\n\n"
            "**Pronóstico recursivo:** para proyectar 12 h se predice la hora siguiente y se "
            "realimenta como nuevo rezago. El error se acumula con el horizonte → referencia de "
            "corto plazo, no garantía."
        )

    # Regularizar a frecuencia horaria e imputar
    s = df.set_index("fecha_hora")["cmg_usd_mwh"].resample("1h").mean().interpolate().dropna()
    d = pd.DataFrame({"cmg": s})
    for lag in [1, 2, 3, 6, 12, 24]:
        d[f"lag{lag}"] = d["cmg"].shift(lag)
    d["hora_dia"] = d.index.hour
    d = d.dropna()
    if len(d) < 36:
        st.info("Serie de CMG demasiado corta tras crear rezagos.")
        return

    feats = [c for c in d.columns if c != "cmg"]
    X, y = d[feats].values, d["cmg"].values
    n_test = max(12, int(len(d) * 0.2))
    model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X[:-n_test], y[:-n_test])
    pred = model.predict(X[-n_test:])
    r2 = r2_score(y[-n_test:], pred)
    mae = mean_absolute_error(y[-n_test:], pred)

    c1, c2, c3 = st.columns(3)
    c1.metric("R² (test)", f"{r2:.3f}")
    c2.metric("MAE", f"{mae:.1f} USD/MWh")
    c3.metric("Último CMG", f"{y[-1]:.1f} USD/MWh")

    _titulo(f"CMG real vs predicción (backtest) — {nodo.replace('_', ' ').strip()}", "12px 0 6px")
    idx_te = d.index[-n_test:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=idx_te, y=y[-n_test:], name="CMG real",
                             line=dict(color=AES_VIOLETA, width=2.5)))
    fig.add_trace(go.Scatter(x=idx_te, y=pred, name="Predicción ML",
                             line=dict(color=AES_AMBAR, width=2, dash="dot")))
    fig.update_yaxes(title="USD/MWh")
    st.plotly_chart(_layout_base(fig), use_container_width=True, key=f"ml_cmg_{nodo}")

    # Pronóstico recursivo de las próximas 12 horas
    _titulo("Pronóstico recursivo — próximas 12 horas", "16px 0 6px")
    model_full = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1)
    model_full.fit(X, y)
    hist = list(d["cmg"].values)
    last_time = d.index[-1]
    futuros, horas_f = [], []
    for h in range(1, 13):
        lags = {1: hist[-1], 2: hist[-2], 3: hist[-3], 6: hist[-6], 12: hist[-12], 24: hist[-24]}
        hora_dia = (last_time + timedelta(hours=h)).hour
        feat_vec = [lags[1], lags[2], lags[3], lags[6], lags[12], lags[24], hora_dia]
        yhat = float(model_full.predict([feat_vec])[0])
        hist.append(yhat)
        futuros.append(yhat)
        horas_f.append(last_time + timedelta(hours=h))
    figf = go.Figure()
    figf.add_trace(go.Scatter(x=d.index[-48:], y=d["cmg"].values[-48:], name="Histórico",
                              line=dict(color=AES_VIOLETA, width=2)))
    figf.add_trace(go.Scatter(x=horas_f, y=futuros, name="Pronóstico 12h",
                              line=dict(color=AES_AMBAR, width=2, dash="dot")))
    figf.update_yaxes(title="USD/MWh")
    st.plotly_chart(_layout_base(figf), use_container_width=True, key=f"ml_cmg_fut_{nodo}")
    st.caption("Pronóstico recursivo con RandomForest sobre rezagos. El error crece con el horizonte "
               "— úsese como referencia de corto plazo, no como valor garantizado.")


# ── 4. Análisis de eficiencia ──────────────────────────────────────────────────

def _render_eficiencia() -> None:
    with st.expander("¿Qué mide el análisis de eficiencia? (metodología)"):
        st.markdown(
            "**Performance Ratio (PR)** = generación real / generación teórica del modelo físico, "
            "calculado solo en horas con recurso relevante (>5% de Pmax). PR≈1 significa que el "
            "parque rinde lo esperado; PR bajo indica pérdidas (suciedad, sombras, "
            "indisponibilidad, limitaciones o curtailment). Se usa la **mediana** del PR para "
            "robustez ante valores extremos.\n\n"
            "**Clustering (K-Means):** agrupa las horas según recurso (GHI o viento) y PR, "
            "revelando regímenes de operación. Los grupos se etiquetan por nivel de eficiencia "
            "(alta/media/baja). Puntos con buen recurso pero PR bajo son los que conviene investigar."
        )

    filas = []
    detalle = {}
    for p in PARQUES_TODOS:
        tec = TECNOLOGIA[p]
        df = _dataset_parque(p)
        if df.empty:
            continue
        col_fis = "p_fv_estimada_mw" if tec == "Solar" else "p_eolica_estimada_mw"
        if col_fis not in df.columns:
            continue
        d = df[(df[col_fis] > PMAX[p] * 0.05)].copy()  # solo horas con recurso relevante
        if d.empty:
            continue
        d["pr"] = (d["gen_real_mw"] / d[col_fis]).clip(0, 1.5)
        pr_medio = d["pr"].median()
        fp = (df["gen_real_mw"].mean() / PMAX_FP[p] * 100) if PMAX_FP[p] else None
        filas.append({"Parque": NOMBRE_DISPLAY[p], "Tipo": tec,
                      "Performance ratio": round(pr_medio, 3),
                      "FP medio %": round(fp, 1) if fp is not None else None,
                      "Horas": len(d)})
        detalle[p] = d

    if not filas:
        st.info("Datos insuficientes para el análisis de eficiencia.")
        return

    dfr = pd.DataFrame(filas).sort_values("Performance ratio", ascending=False)
    _titulo("Performance ratio (real / teórico) por parque", "4px 0 6px")
    fig = go.Figure(go.Bar(
        x=dfr["Parque"], y=dfr["Performance ratio"],
        marker_color=[AES_AZUL if t == "Solar" else AES_CYAN for t in dfr["Tipo"]],
        text=dfr["Performance ratio"], textposition="outside",
    ))
    fig.add_hline(y=1.0, line_dash="dot", line_color=AES_VERDE,
                  annotation_text="PR ideal = 1.0", annotation_font_size=9)
    fig.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                      height=320, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="PR (mediana)")
    fig.update_xaxes(tickangle=-30)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key="ml_efi_rank")

    st.dataframe(dfr, hide_index=True, use_container_width=True)

    # Clustering de condiciones para un parque seleccionado
    st.divider()
    parque_sel = st.selectbox("Clustering de condiciones operativas — parque",
                              list(detalle.keys()), format_func=lambda p: NOMBRE_DISPLAY[p],
                              key="ml_efi_parque")
    d = detalle[parque_sel]
    tec = TECNOLOGIA[parque_sel]
    var_rec = "ghi_wm2" if tec == "Solar" else "wind_speed_100m"
    lbl_rec = "GHI (W/m²)" if tec == "Solar" else "Viento 100m (m/s)"
    if var_rec not in d.columns or len(d) < 20:
        st.info("Datos insuficientes para clustering en este parque.")
        return
    dc = d.dropna(subset=[var_rec, "pr"]).copy()
    if len(dc) < 20:
        st.info("Datos insuficientes para clustering tras limpiar faltantes.")
        return
    Xc = StandardScaler().fit_transform(dc[[var_rec, "pr"]].values)
    k = min(3, max(2, len(dc) // 30))
    dc["cluster"] = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(Xc)

    # Centroides en unidades reales (no escaladas) y etiqueta por nivel de eficiencia
    cent = dc.groupby("cluster").agg(
        x=(var_rec, "mean"), y=("pr", "mean"), n=("pr", "size")
    ).reset_index().sort_values("y", ascending=False)
    niveles = ["Alta eficiencia", "Media eficiencia", "Baja eficiencia"]
    colores = [AES_VERDE, AES_AMBAR, AES_ROJO]
    etq_cluster, color_cluster = {}, {}
    for rank, (_, row) in enumerate(cent.iterrows()):
        etq_cluster[row["cluster"]] = niveles[rank] if rank < len(niveles) else f"Grupo {rank+1}"
        color_cluster[row["cluster"]] = colores[rank] if rank < len(colores) else AES_VIOLETA

    _titulo(f"Eficiencia vs recurso — {NOMBRE_DISPLAY[parque_sel]}", "12px 0 6px")
    figc = go.Figure()
    for c in cent["cluster"]:
        sub = dc[dc["cluster"] == c]
        figc.add_trace(go.Scatter(
            x=sub[var_rec], y=sub["pr"], mode="markers",
            name=f"{etq_cluster[c]} (n={len(sub)})",
            marker=dict(color=color_cluster[c], size=6, opacity=0.55),
            hovertemplate=f"{lbl_rec}: %{{x:.1f}}<br>PR: %{{y:.2f}}<extra>{etq_cluster[c]}</extra>",
        ))
    # Centroides: una X grande por grupo
    for _, row in cent.iterrows():
        figc.add_trace(go.Scatter(
            x=[row["x"]], y=[row["y"]], mode="markers+text",
            marker=dict(color=color_cluster[row["cluster"]], size=18, symbol="x",
                        line=dict(color="white", width=1.5)),
            text=["centroide"], textposition="top center", textfont=dict(size=9),
            showlegend=False,
            hovertemplate=f"Centroide {etq_cluster[row['cluster']]}<br>"
                          f"{lbl_rec}: %{{x:.1f}}<br>PR medio: %{{y:.2f}}<extra></extra>",
        ))
    figc.add_hline(y=1.0, line_dash="dot", line_color=AES_MUTED, line_width=1,
                   annotation_text="PR = 1.0 (real = teórico)", annotation_font_size=9)
    figc.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                       height=360, margin=dict(l=0, r=0, t=10, b=0),
                       xaxis_title=lbl_rec, yaxis_title="Performance ratio (real / teórico)",
                       legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    figc.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    figc.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(figc, use_container_width=True, key=f"ml_efi_cluster_{parque_sel}")
    st.caption(
        "Cómo leerlo: cada punto es una hora de operación. Eje X = recurso disponible "
        f"({lbl_rec}); eje Y = performance ratio (cuánto generó vs lo que el modelo "
        "físico esperaba). La X marca el centroide (condición típica) de cada grupo. "
        "Verde = horas de alta eficiencia (PR cerca de 1); rojo = baja eficiencia "
        "(posible suciedad, sombras, limitaciones o fallas). Puntos rojos con buen "
        "recurso a la derecha y PR bajo son los que conviene investigar."
    )


# ── 5. BESS — patrón de operación y arbitraje (ML) ──────────────────────────────

@st.cache_data(ttl=900)
def _dataset_bess(cod: str, dias: int = 20) -> pd.DataFrame:
    """Serie del BESS ⋈ CMG del nodo del parque asociado, por hora."""
    from utils.db import get_client
    sb = get_client()
    desde = (datetime.now(SANTIAGO) - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        b = (sb.table("generacion_bess_ernc").select("*")
             .eq("bess", cod).gte("fecha_hora", desde).order("fecha_hora").execute())
    except Exception:
        return pd.DataFrame()
    if not b.data:
        return pd.DataFrame()
    db = pd.DataFrame(b.data)
    db["fecha_hora"] = pd.to_datetime(db["fecha_hora"])
    db["hora_dia"] = db["fecha_hora"].dt.hour
    nodo = CMG_NODO.get(BESS[cod]["parque"])
    if nodo:
        # CMG del nodo: el online S3 (cmg_ernc) es muy escaso → se combina con el
        # CMG programado PCP (denso, horario). Se prefiere el online real cuando existe
        # y se completa con el programado, de modo que el merge siempre tenga cobertura.
        dc = _cmg_historico(nodo, dias).rename(columns={"cmg_usd_mwh": "cmg_online"})
        dp = _cmg_programado_hist(nodo, dias).rename(columns={"cmg_usd_mwh": "cmg_prog"})
        if not dc.empty:
            db = db.merge(dc, on="fecha_hora", how="left")
        if not dp.empty:
            db = db.merge(dp, on="fecha_hora", how="left")
        col_on = db["cmg_online"] if "cmg_online" in db.columns else pd.Series(index=db.index, dtype=float)
        col_pr = db["cmg_prog"] if "cmg_prog" in db.columns else pd.Series(index=db.index, dtype=float)
        db["cmg_usd_mwh"] = col_on.combine_first(col_pr)
    return db


def _render_bess_ml(cod: str) -> None:
    with st.expander("¿Qué analiza esta sección? (metodología)"):
        st.markdown(
            "Estudia **cómo opera el BESS** y si su arbitraje es racional:\n\n"
            "1. **Perfil horario:** potencia neta media por hora del día (negativa = carga, "
            "positiva = descarga). Un BESS solar bien operado carga al mediodía (CMG bajo) y "
            "descarga en la punta de la tarde (CMG alto).\n"
            "2. **Relación con el CMG:** dispersión de potencia neta vs CMG del nodo. Si el BESS "
            "arbitra bien, debería cargar con CMG bajo y descargar con CMG alto.\n"
            "3. **Modelo:** Random Forest que predice la potencia neta a partir de hora del día y "
            "CMG; la importancia de variables indica qué guía la operación."
        )

    db = _dataset_bess(cod)
    if db.empty or len(db) < 24:
        st.info("Sin histórico suficiente de este BESS (se necesitan ≥24 horas). "
                "Corre la adquisición o espera el cron.")
        return

    # 1. Perfil horario de potencia neta
    perf = db.groupby("hora_dia")["potencia_neta_mw"].mean().reset_index()
    _titulo(f"Perfil horario de operación — {BESS[cod]['nombre']}", "8px 0 6px")
    figp = go.Figure(go.Bar(
        x=perf["hora_dia"], y=perf["potencia_neta_mw"],
        marker_color=[AES_VERDE if v >= 0 else AES_AZUL for v in perf["potencia_neta_mw"]],
        hovertemplate="%{x}h: %{y:.1f} MW<extra></extra>",
    ))
    figp.add_hline(y=0, line_color=AES_MUTED, line_width=1)
    figp.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                       height=300, margin=dict(l=0, r=0, t=10, b=0),
                       xaxis_title="Hora del día", yaxis_title="Potencia neta media (MW)")
    figp.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    figp.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(figp, use_container_width=True, key=f"ml_bess_perfil_{cod}")
    st.caption("Verde = descarga (entrega al sistema), azul = carga. El patrón ideal carga al "
               "mediodía solar y descarga en la punta de la tarde.")

    # 2 + 3. Relación con CMG y modelo
    if "cmg_usd_mwh" not in db.columns or db["cmg_usd_mwh"].notna().sum() < 24:
        st.info("Sin CMG suficiente del nodo asociado para el análisis de arbitraje.")
        return
    dd = db.dropna(subset=["cmg_usd_mwh", "potencia_neta_mw"]).copy()
    corr = dd["cmg_usd_mwh"].corr(dd["potencia_neta_mw"])

    _titulo("Potencia neta vs CMG del nodo", "14px 0 6px")
    figs = go.Figure(go.Scatter(
        x=dd["cmg_usd_mwh"], y=dd["potencia_neta_mw"], mode="markers",
        marker=dict(color=dd["hora_dia"], colorscale="Viridis", size=6, opacity=0.6,
                    colorbar=dict(title="Hora")),
        hovertemplate="CMG %{x:.0f} USD/MWh<br>Neta %{y:.1f} MW<extra></extra>",
    ))
    figs.add_hline(y=0, line_color=AES_MUTED, line_width=1)
    figs.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                       height=320, margin=dict(l=0, r=0, t=10, b=0),
                       xaxis_title="CMG (USD/MWh)", yaxis_title="Potencia neta (MW)")
    figs.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    figs.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(figs, use_container_width=True, key=f"ml_bess_cmg_{cod}")

    c1, c2 = st.columns(2)
    c1.metric("Correlación neta–CMG", f"{corr:+.2f}")
    arb = "racional (descarga con CMG alto)" if corr > 0.15 else (
          "inverso (revisar operación)" if corr < -0.15 else "sin patrón claro")
    c2.metric("Lectura del arbitraje", arb)

    # Modelo: importancia de hora vs CMG
    feats_b = ["hora_dia", "cmg_usd_mwh"]
    if len(dd) >= 48:
        m = RandomForestRegressor(n_estimators=150, max_depth=8, random_state=42, n_jobs=-1)
        m.fit(dd[feats_b].values, dd["potencia_neta_mw"].values)
        imp = pd.DataFrame({"var": ["Hora del día", "CMG nodo"],
                            "imp": m.feature_importances_}).sort_values("imp")
        _titulo("¿Qué guía la operación del BESS?", "14px 0 6px")
        figi = go.Figure(go.Bar(x=imp["imp"], y=imp["var"], orientation="h", marker_color=AES_VIOLETA))
        figi.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                           height=200, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Importancia relativa")
        st.plotly_chart(figi, use_container_width=True, key=f"ml_bess_imp_{cod}")
        st.caption("Si domina 'Hora del día', el BESS opera por horario fijo; si domina 'CMG nodo', "
                   "responde al precio (arbitraje activo).")

    # 4. Recomendación de arbitraje a futuro (CMG programado próximas horas)
    _recomendacion_arbitraje(cod)


def _recomendacion_arbitraje(cod: str) -> None:
    """Usa el CMG programado del nodo para recomendar ventanas de carga/descarga
    en las próximas horas y estimar el margen de arbitraje del BESS."""
    nodo = CMG_NODO.get(BESS[cod]["parque"])
    if not nodo:
        return
    dp = _cmg_programado_hist(nodo, dias_atras=0)  # solo desde ahora hacia adelante
    ahora = datetime.now(SANTIAGO).replace(tzinfo=None)
    if not dp.empty:
        dp = dp[dp["fecha_hora"] >= ahora].sort_values("fecha_hora")
    if dp.empty or len(dp) < 6:
        st.info("Sin CMG programado futuro suficiente para recomendar arbitraje "
                "(se puebla al correr la adquisición / cron).")
        return

    fut = dp.head(36).copy()   # próximas ~36 h
    pmax = BESS[cod]["pmax_mw"]
    horas = BESS_HORAS.get(cod) or 4.0
    energia_mwh = pmax * horas

    # Ventanas: n horas más baratas (carga) y más caras (descarga), n ≈ duración del BESS
    n = max(1, int(round(horas)))
    baratas = fut.nsmallest(n, "cmg_usd_mwh")
    caras = fut.nlargest(n, "cmg_usd_mwh")
    p_carga = baratas["cmg_usd_mwh"].mean()
    p_desc = caras["cmg_usd_mwh"].mean()
    spread = p_desc - p_carga
    # Margen de un ciclo: descarga (energía·precio alto) − costo de carga (energía·precio bajo)
    margen = energia_mwh * spread

    _titulo("Recomendación de arbitraje — próximas horas (CMG programado)", "16px 0 6px")
    figr = go.Figure()
    figr.add_trace(go.Scatter(
        x=fut["fecha_hora"], y=fut["cmg_usd_mwh"], mode="lines",
        line=dict(color=AES_VIOLETA, width=2), name="CMG programado",
        hovertemplate="%{y:.1f} USD/MWh<extra></extra>",
    ))
    figr.add_trace(go.Scatter(
        x=baratas["fecha_hora"], y=baratas["cmg_usd_mwh"], mode="markers",
        marker=dict(color=AES_AZUL, size=11, symbol="triangle-down"),
        name="Cargar (barato)", hovertemplate="Cargar @ %{y:.1f}<extra></extra>",
    ))
    figr.add_trace(go.Scatter(
        x=caras["fecha_hora"], y=caras["cmg_usd_mwh"], mode="markers",
        marker=dict(color=AES_VERDE, size=11, symbol="triangle-up"),
        name="Descargar (caro)", hovertemplate="Descargar @ %{y:.1f}<extra></extra>",
    ))
    figr.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                       height=300, margin=dict(l=0, r=0, t=10, b=0),
                       xaxis_title=None, yaxis_title="USD/MWh",
                       legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)))
    figr.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    figr.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(figr, use_container_width=True, key=f"ml_bess_arb_{cod}")

    h_carga = ", ".join(sorted(baratas["fecha_hora"].dt.strftime("%H:%M")))
    h_desc = ", ".join(sorted(caras["fecha_hora"].dt.strftime("%H:%M")))
    c1, c2, c3 = st.columns(3)
    c1.metric("Cargar a", f"{p_carga:.0f} USD/MWh", h_carga)
    c2.metric("Descargar a", f"{p_desc:.0f} USD/MWh", h_desc)
    c3.metric("Margen ciclo est.", f"{margen:,.0f} USD", f"spread {spread:.0f} USD/MWh")
    st.caption(
        f"Ventanas óptimas para {energia_mwh:.0f} MWh ({pmax:.0f} MW × {horas:.1f} h) según el "
        "CMG programado PCP del nodo. Margen = energía × (precio descarga − precio carga); es una "
        "cota teórica (no descuenta pérdidas de round-trip ni límites de red)."
    )


# ── Entrada principal ──────────────────────────────────────────────────────────

def render_tab_ml() -> None:
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin-bottom:4px'>"
        f"ML Analysis — modelos predictivos sobre los datos del portfolio</div>"
        f"<div style='font-size:11.5px;color:{AES_MUTED};margin-bottom:12px'>"
        f"Modelos entrenados en vivo con el histórico de Supabase (meteo, generación y CMG)."
        f"</div>",
        unsafe_allow_html=True,
    )

    if not _SKLEARN:
        st.warning("scikit-learn no está instalado en este entorno. Agrega `scikit-learn>=1.4.0` "
                   "a requirements.txt y vuelve a desplegar.")
        return

    analisis = st.radio(
        "Análisis",
        ["Forecast de generación", "Detección de anomalías", "Predicción de CMG",
         "Análisis de eficiencia", "BESS — operación"],
        horizontal=True, key="ml_analisis",
    )

    if analisis == "Forecast de generación":
        parque = st.selectbox("Parque", PARQUES_TODOS, format_func=lambda p: NOMBRE_DISPLAY[p],
                              key="ml_fc_parque")
        with st.spinner("Entrenando modelo..."):
            _render_forecast_gen(parque)

    elif analisis == "Detección de anomalías":
        parque = st.selectbox("Parque", PARQUES_TODOS, format_func=lambda p: NOMBRE_DISPLAY[p],
                              key="ml_anom_parque")
        with st.spinner("Analizando..."):
            _render_anomalias(parque)

    elif analisis == "Predicción de CMG":
        nodo = st.selectbox("Nodo CMG", CMG_NODOS_TODOS,
                            format_func=lambda n: n.replace("_", " ").strip(), key="ml_cmg_nodo")
        with st.spinner("Entrenando modelo..."):
            _render_cmg(nodo)

    elif analisis == "Análisis de eficiencia":
        with st.spinner("Calculando..."):
            _render_eficiencia()

    elif analisis == "BESS — operación":
        cod = st.selectbox("BESS", list(BESS.keys()),
                           format_func=lambda c: BESS[c]["nombre"], key="ml_bess_cod")
        with st.spinner("Analizando operación del BESS..."):
            _render_bess_ml(cod)
