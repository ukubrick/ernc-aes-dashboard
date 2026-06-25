"""Tab ML Analysis — modelos predictivos y analítica sobre los datos ERNC.

Siete análisis:
  1. Forecast de generación  — RandomForest meteo→gen, comparado con el modelo físico.
  1b. Forecast probabilístico — LightGBM cuantílico (banda P10–P50–P90) meteo→gen.
  2. Detección de anomalías  — residuos del modelo + IsolationForest sobre el clima.
  3. Predicción de CMG        — RandomForest con rezagos (lags) por nodo.
  4. Análisis de eficiencia   — performance ratio real/teórico + clustering de condiciones.
  4b. Soiling FV              — soiling ratio (gen/modelo normalizado) + tendencia de suciedad.
  5. BESS — operación         — perfil horario, neta vs CMG y optimizador de arbitraje (LP/MILP).
  6. Validación recurso (NASA) — GHI Open-Meteo vs NASA POWER (fuente satelital independiente).

Sub-navegación con radio (no st.tabs) para que cada gráfico Plotly se monte siempre
en un contenedor visible y a ancho real.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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

SANTIAGO = ZoneInfo("America/Santiago")

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

try:
    from lightgbm import LGBMRegressor
    _LGBM = True
except Exception:
    _LGBM = False

try:
    import pulp
    _PULP = True
except Exception:
    _PULP = False

# Cuantiles de la banda probabilística: P10 (pesimista) — P50 (central) — P90 (optimista)
CUANTILES = (0.10, 0.50, 0.90)


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

def _fetch_paginado(query_fn, page: int = 1000) -> list[dict]:
    """Trae TODAS las filas de una query paginando con .range(): PostgREST tope a
    1000 filas por request, y una ventana de 120 días son ~2.880 filas/parque."""
    filas, i = [], 0
    while True:
        lote = query_fn().range(i, i + page - 1).execute().data or []
        filas.extend(lote)
        if len(lote) < page:
            break
        i += page
    return filas


@st.cache_data(ttl=900)
def _dataset_parque(parque: str, dias: int = 25) -> pd.DataFrame:
    """meteo histórico (es_forecast=False) ⋈ gen_real por hora para un parque."""
    from utils.db import get_client
    sb = get_client()
    desde = (datetime.now(SANTIAGO) - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        m_data = _fetch_paginado(lambda: (sb.table("meteo_ernc").select("*")
                                          .eq("parque", parque).eq("es_forecast", False)
                                          .gte("fecha_hora", desde).order("fecha_hora")))
        g_data = _fetch_paginado(lambda: (sb.table("generacion_real_ernc")
                                          .select("fecha_hora,gen_real_mw")
                                          .eq("parque", parque).gte("fecha_hora", desde)
                                          .order("fecha_hora")))
    except Exception:
        return pd.DataFrame()
    if not m_data or not g_data:
        return pd.DataFrame()
    dm = pd.DataFrame(m_data)
    dg = pd.DataFrame(g_data)
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
            "**Qué entrega:** un pronóstico **puntual** (un valor de MW por hora). Si necesitas el "
            "**rango de incertidumbre** (banda P10–P90, '80% de confianza'), usa la pestaña "
            "**Forecast probabilístico**.\n\n"
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
            "(error absoluto medio en MW).\n\n"
            "**Datos:** se entrena en vivo con el histórico de Supabase (meteo Open-Meteo + "
            "generación real CEN), ventana de los últimos ~115 días."
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


# ── 1b. Forecast probabilístico (LightGBM cuantílico) ──────────────────────────

def _add_ciclicas(df: pd.DataFrame) -> pd.DataFrame:
    """Codifica la hora del día como seno/coseno para que el modelo capte la
    periodicidad diaria sin tratar las 23h y las 0h como lejanas."""
    df = df.copy()
    df["hora_sin"] = np.sin(2 * np.pi * df["hora_dia"] / 24)
    df["hora_cos"] = np.cos(2 * np.pi * df["hora_dia"] / 24)
    return df


def _pinball(y_true, y_pred, alpha: float) -> float:
    """Pérdida pinball (quantile loss): mide la calidad de un cuantil predicho."""
    diff = y_true - y_pred
    return float(np.mean(np.maximum(alpha * diff, (alpha - 1.0) * diff)))


def _train_cuantiles(X, y, pmax: float):
    """Entrena un LGBMRegressor por cuantil. Devuelve dict {alpha: modelo}."""
    modelos = {}
    for a in CUANTILES:
        m = LGBMRegressor(objective="quantile", alpha=a, n_estimators=200,
                          num_leaves=31, learning_rate=0.07, min_child_samples=20,
                          subsample=0.9, colsample_bytree=0.9, random_state=42, n_jobs=-1,
                          verbose=-1)
        m.fit(X, y)
        modelos[a] = m
    return modelos


def _predict_banda(modelos, X, pmax: float):
    """Predice los 3 cuantiles, los acota a [0, pmax] y reordena para que P10≤P50≤P90
    (los cuantiles se entrenan por separado y pueden cruzarse en zonas con pocos datos)."""
    qs = np.column_stack([np.clip(modelos[a].predict(X), 0, pmax) for a in CUANTILES])
    qs = np.sort(qs, axis=1)
    return qs[:, 0], qs[:, 1], qs[:, 2]


def _train_cal(Xtr, ytr, Xcal, ycal, pmax: float, alpha: float = 0.20):
    """Entrena los cuantiles y calibra el ancho de banda por CQR (Conformalized
    Quantile Regression): sobre un set de calibración mide cuánto hay que ensanchar
    la banda P10–P90 para que la cobertura empírica alcance 1-alpha (80%). Devuelve
    (modelos, Q) donde Q es el ajuste de ancho. Corrige la subcobertura típica del
    viento sin tocar el modelo."""
    modelos = _train_cuantiles(Xtr, ytr, pmax)
    c10, _, c90 = _predict_banda(modelos, Xcal, pmax)
    E = np.maximum(c10 - ycal, ycal - c90)            # score de no-conformidad
    n = len(ycal)
    nivel = min(1.0, (1 - alpha) * (1 + 1.0 / n))     # corrección de muestra finita
    Q = float(np.quantile(E, nivel))
    return modelos, Q


def _banda_cal(modelos, X, Q: float, pmax: float):
    """Banda conformalizada: ensancha P10/P90 por Q y reacota a [0, pmax]."""
    p10, p50, p90 = _predict_banda(modelos, X, pmax)
    return np.clip(p10 - Q, 0, pmax), p50, np.clip(p90 + Q, 0, pmax)


@st.cache_data(ttl=3600, show_spinner=False)
def _entrenar_prob(parque: str) -> dict | None:
    """Entrena y calibra (CQR) la banda probabilística de un parque. Cacheado 1h:
    el entrenamiento LightGBM es lo caro (~10-15s), así que se hace una sola vez y
    las re-ejecuciones de la UI son instantáneas. Devuelve modelos+métricas+backtest
    listos para graficar, o None / {'insuf':True} si faltan datos."""
    from sklearn.model_selection import train_test_split
    tec = TECNOLOGIA[parque]
    pmax = PMAX[parque] if tec == "Solar" else PMAX_FP[parque]
    df = _dataset_parque(parque, dias=120)
    if df.empty:
        return None
    feats = _feats_disponibles(df, tec)
    df = _add_ciclicas(df)
    feats_q = feats + ["hora_sin", "hora_cos"]
    d = df.dropna(subset=feats_q + ["gen_real_mw"])
    if len(d) < 300:
        return {"insuf": True, "n": len(d)}

    col_fis = "p_fv_estimada_mw" if tec == "Solar" else "p_eolica_estimada_mw"
    cols = feats_q + ["gen_real_mw"] + ([col_fis] if col_fis in d.columns else [])
    tr_full, te = train_test_split(d[cols], test_size=0.2, random_state=42)
    tr, cal = train_test_split(tr_full, test_size=0.25, random_state=42)  # 60/20/20

    modelos, Q = _train_cal(tr[feats_q].values, tr["gen_real_mw"].values,
                            cal[feats_q].values, cal["gen_real_mw"].values, pmax)
    p10, p50, p90 = _banda_cal(modelos, te[feats_q].values, Q, pmax)
    y_te = te["gen_real_mw"].values
    cobertura = float(np.mean((y_te >= p10) & (y_te <= p90)) * 100)
    pinball = float(np.mean([_pinball(y_te, pq, a) for pq, a in zip((p10, p50, p90), CUANTILES)]))
    mae_p50 = float(mean_absolute_error(y_te, p50))
    mae_fis = None
    if col_fis in te.columns:
        fis = pd.to_numeric(te[col_fis], errors="coerce"); mk = fis.notna().values
        if mk.any():
            mae_fis = float(mean_absolute_error(y_te[mk], np.clip(fis.values[mk], 0, pmax)))

    # Se reutiliza el modelo ya entrenado (60% del set, calibrado en 20%) para el
    # backtest y el pronóstico futuro — evita un segundo entrenamiento (la mitad del
    # tiempo) sin sesgar las métricas, que se miden sobre el test held-out (20%).
    modelos_full, Q_full = modelos, Q

    # Backtest visual sobre el tramo reciente (arrays listos para graficar)
    n_vis = min(len(d), max(72, int(len(d) * 0.25)))
    dv = d.sort_values("fecha_hora").iloc[-n_vis:]
    b10, b50, b90 = _banda_cal(modelos_full, dv[feats_q].values, Q_full, pmax)

    return {
        "tec": tec, "pmax": pmax, "feats_q": feats_q,
        "modelos_full": modelos_full, "Q_full": Q_full,
        "cobertura": cobertura, "pinball": pinball, "mae_p50": mae_p50,
        "mae_fis": mae_fis, "n_tr": len(tr),
        "bt_fecha": dv["fecha_hora"].values, "bt10": b10, "bt50": b50, "bt90": b90,
        "bt_real": dv["gen_real_mw"].values,
    }


def _render_forecast_prob(parque: str) -> None:
    if not _LGBM:
        st.warning("LightGBM no está instalado en este entorno. Agrega `lightgbm>=4.0` a "
                   "requirements.txt y vuelve a desplegar.")
        return

    with st.expander("¿Qué es un forecast probabilístico? (metodología)"):
        st.markdown(
            "**Idea:** en vez de un solo número, el modelo entrega una **banda**: P10 (escenario "
            "pesimista), P50 (central) y P90 (optimista). Con 80% de confianza la generación real "
            "caerá entre P10 y P90. Esto es lo que sirve para declarar al CEN y gestionar desvíos.\n\n"
            "**Modelo:** tres `LightGBM` con `objective=quantile` (gradient boosting), uno por "
            "cuantil, con **calibración conformal (CQR)** que ajusta el ancho de banda para que la "
            "cobertura empírica alcance el 80%. Entradas: variables meteo del parque + hora del día "
            "codificada en seno/coseno.\n\n"
            "**Métricas:**\n"
            "- **Cobertura P10–P90:** % de horas reales dentro de la banda. Ideal ≈ 80%.\n"
            "- **Pinball loss:** calidad de los cuantiles (menor = mejor).\n"
            "- **MAE del P50** vs **MAE del modelo físico:** cuánto le gana el ML al modelo "
            "determinístico que ya usa el dashboard."
        )

    res = _entrenar_prob(parque)
    if res is None:
        st.info("Sin datos meteo+generación para este parque todavía.")
        return
    if res.get("insuf"):
        st.info(f"Datos insuficientes para una banda confiable ({res['n']} horas; se necesitan "
                "≥300). Corre el backfill o espera a que se acumule histórico.")
        return

    feats_q, pmax, tec = res["feats_q"], res["pmax"], res["tec"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cobertura P10–P90", f"{res['cobertura']:.0f}%", help="Ideal ≈ 80%")
    c2.metric("Pinball loss", f"{res['pinball']:.2f}")
    c3.metric("MAE P50", f"{res['mae_p50']:.2f} MW")
    if res["mae_fis"] is not None:
        mejora = (res["mae_fis"] - res["mae_p50"]) / res["mae_fis"] * 100 if res["mae_fis"] else 0
        c4.metric("MAE modelo físico", f"{res['mae_fis']:.2f} MW", delta=f"{mejora:+.0f}% ML")
    else:
        c4.metric("Registros entren.", f"{res['n_tr']}")

    _titulo(f"Banda P10–P90 vs generación real — {NOMBRE_DISPLAY[parque]}", "12px 0 6px")
    st.plotly_chart(_fan_chart(res["bt_fecha"], res["bt10"], res["bt50"], res["bt90"],
                               real=res["bt_real"]),
                    use_container_width=True, key=f"ml_prob_test_{parque}")
    st.caption("Validación: la línea punteada (generación real) debe caer dentro de la banda "
               "azul ~80% del tiempo. Si se sale a menudo, la banda está mal calibrada.")

    # Pronóstico futuro sobre el forecast meteo (barato; se aplica el modelo ya entrenado)
    dff = _forecast_meteo_parque(parque)
    if not dff.empty:
        dff = _add_ciclicas(dff)
        if set(feats_q).issubset(dff.columns):
            dfx = dff.dropna(subset=feats_q).copy()
            if not dfx.empty:
                f10, f50, f90 = _banda_cal(res["modelos_full"], dfx[feats_q].values,
                                           res["Q_full"], pmax)
                if tec == "Solar" and "is_day" in dfx.columns:
                    noche = ~dfx["is_day"].astype(bool).values
                    f10[noche] = f50[noche] = f90[noche] = 0.0
                _titulo("Pronóstico probabilístico — próximos días", "16px 0 6px")
                st.plotly_chart(_fan_chart(dfx["fecha_hora"], f10, f50, f90),
                                use_container_width=True, key=f"ml_prob_fut_{parque}")
                st.caption("Banda sombreada = rango P10–P90 (80% de confianza). Línea central = P50 "
                           "(escenario más probable). Aplicada al pronóstico meteo Open-Meteo.")


def _fan_chart(x, p10, p50, p90, real=None):
    """Fan chart: banda P10–P90 sombreada + línea P50 (+ real opcional)."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=p90, name="P90", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=p10, name="Banda P10–P90", line=dict(width=0),
                             fill="tonexty", fillcolor="rgba(59,76,232,0.16)",
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=p50, name="P50 (central)",
                             line=dict(color=AES_AZUL, width=2.4)))
    if real is not None:
        fig.add_trace(go.Scatter(x=x, y=real, name="Gen. real",
                                 line=dict(color=AES_TEXTO, width=1.6, dash="dot")))
    return _layout_base(fig, height=360)


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
            "calculado solo en horas con recurso relevante (>5% de Pmax). Un PR **más bajo** indica "
            "pérdidas (suciedad, sombras, indisponibilidad, limitaciones o curtailment). Se usa la "
            "**mediana** del PR para robustez ante valores extremos.\n\n"
            "*Nota:* el modelo físico puede tener un sesgo sistemático (sub o sobreestimar), por lo "
            "que importa **comparar el PR entre parques y entre horas**, más que su valor absoluto. "
            "Para seguimiento de suciedad en el tiempo, ver la pestaña **Soiling FV** (PR "
            "normalizado).\n\n"
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


# ── 4b. Soiling FV (ensuciamiento de paneles) ───────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def _soiling_diario(parque: str) -> pd.DataFrame:
    """Serie diaria del soiling ratio de un parque solar. Método: PR = gen_real /
    modelo físico (corrige temperatura, POA y trackers) por hora de sol fuerte,
    agregado a mediana diaria y normalizado contra el mejor estado reciente del propio
    parque (P90) para quitar el sesgo del modelo. SR≈1 = limpio; SR<1 = subrendimiento
    (soiling + curtailment + limitaciones)."""
    df = _dataset_parque(parque, dias=120)
    if df.empty:
        return pd.DataFrame()
    d = df.copy()
    d["pfv"] = pd.to_numeric(d.get("p_fv_estimada_mw"), errors="coerce")
    techo = d["pfv"].max()
    if not techo or techo <= 0:
        return pd.DataFrame()
    d = d[(d["is_day"] == True) & (d["ghi_wm2"] > 400) &
          (d["pfv"] > 0.10 * techo) & (d["gen_real_mw"] >= 0)]
    if d.empty:
        return pd.DataFrame()
    d["pr"] = d["gen_real_mw"] / d["pfv"]
    d["fecha"] = pd.to_datetime(d["fecha_hora"]).dt.date
    daily = (d.groupby("fecha").agg(pr=("pr", "median"), n=("pr", "size"),
                                    gen=("gen_real_mw", "sum")).reset_index())
    daily = daily[daily["n"] >= 3]
    if len(daily) < 10:
        return pd.DataFrame()
    ref = daily["pr"].quantile(0.90)
    daily["sr"] = (daily["pr"] / ref).clip(upper=1.05)
    daily["fecha"] = pd.to_datetime(daily["fecha"])
    return daily


def _render_soiling(parque: str) -> None:
    with st.expander("¿Cómo se estima el soiling? (metodología)"):
        st.markdown(
            "**Soiling** = pérdida de generación por suciedad acumulada en los paneles "
            "(polvo del desierto), que se recupera con lluvia o lavado.\n\n"
            "**Método:** se compara la generación real con el modelo físico (que ya corrige "
            "sol, temperatura y trackers) hora a hora con sol fuerte, se agrega a un valor "
            "diario y se **normaliza contra el mejor estado reciente del propio parque** "
            "(percentil 90 = referencia 'limpio'). El resultado es el **soiling ratio**: "
            "1.0 = limpio, <1.0 = subrendimiento.\n\n"
            "**Importante:** este índice capta el subrendimiento *total* vs los mejores días "
            "— incluye soiling pero también curtailment y limitaciones. La precisión mejora "
            "con datos de precipitación y una referencia de panel limpio medida."
        )

    daily = _soiling_diario(parque)
    if daily.empty:
        st.info("Datos insuficientes para estimar soiling (se necesitan ≥10 días con sol).")
        return

    sr = daily["sr"].values
    x = np.arange(len(sr))
    slope = float(np.polyfit(x, sr, 1)[0] * 100)        # %/día
    sr_actual = float(daily["sr"].tail(7).mean())        # estado actual suavizado 7d
    perdida_pct = (1 - sr_actual) * 100
    # Eventos de recuperación (limpieza/lluvia): salto diario > +8%
    rec = (daily["sr"].diff() > 0.08).sum()
    # Energía perdida estimada en la ventana: Σ (1-sr)·gen_diaria sobre referencia limpia
    perdida_mwh = float(((1 - daily["sr"]).clip(lower=0) * daily["gen"] / daily["sr"].clip(lower=0.3)).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Soiling ratio actual", f"{sr_actual:.2f}", help="1.0 = panel limpio")
    estado = "acumulando" if slope < -0.05 else ("limpiando" if slope > 0.05 else "estable")
    c2.metric("Tendencia", f"{slope:+.2f}%/día", delta=estado, delta_color="off")
    c3.metric("Pérdida estimada", f"{perdida_pct:.1f}%")
    c4.metric("Recuperaciones (lluvia/lavado)", f"{int(rec)}")

    if perdida_pct > 8 and slope < -0.05:
        st.warning(f"Posible soiling significativo en {NOMBRE_DISPLAY[parque]}: "
                   f"rendimiento {perdida_pct:.0f}% bajo el estado limpio y en descenso. "
                   "Evaluar lavado si no hay lluvia próxima.")

    _titulo(f"Soiling ratio diario — {NOMBRE_DISPLAY[parque]}", "12px 0 6px")
    tend = np.polyval(np.polyfit(x, sr, 1), x)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily["fecha"], y=daily["sr"], mode="lines+markers",
                             name="Soiling ratio", line=dict(color=AES_AZUL, width=2),
                             marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=daily["fecha"], y=tend, name="Tendencia",
                             line=dict(color=AES_AMBAR, width=1.6, dash="dash")))
    fig.add_hline(y=1.0, line=dict(color=AES_VERDE, width=1, dash="dot"))
    recs = daily[daily["sr"].diff() > 0.08]
    if not recs.empty:
        fig.add_trace(go.Scatter(x=recs["fecha"], y=recs["sr"], mode="markers",
                                 name="Recuperación", marker=dict(color=AES_CYAN, size=11,
                                 symbol="triangle-up")))
    fig.update_yaxes(range=[max(0, sr.min() - 0.1), 1.1])
    st.plotly_chart(_layout_base(fig), use_container_width=True, key=f"ml_soil_{parque}")
    st.caption("Línea verde = estado limpio (1.0). Caídas sostenidas = ensuciamiento; "
               "saltos hacia arriba (cyan) = lluvia o lavado. La tendencia ámbar resume la "
               "acumulación de soiling en el período.")


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
            "Estudia **cómo opera el BESS hoy** y **cómo debería operar** para maximizar ingresos:\n\n"
            "1. **Perfil horario:** potencia neta media por hora del día (negativa = carga, "
            "positiva = descarga). Un BESS solar bien operado carga al mediodía (CMG bajo) y "
            "descarga en la punta de la tarde (CMG alto).\n"
            "2. **Relación con el CMG:** dispersión de potencia neta vs CMG del nodo. Si el BESS "
            "arbitra bien, debería cargar con CMG bajo y descargar con CMG alto.\n"
            "3. **Modelo descriptivo:** Random Forest que predice la potencia neta a partir de hora "
            "del día y CMG; la importancia de variables indica qué guía la operación actual.\n"
            "4. **Optimizador de arbitraje (al final):** programación lineal que calcula el "
            "cronograma **óptimo** de carga/descarga sobre el CMG **programado futuro**, maximizando "
            "el ingreso. Respeta el estado de carga (SoC), la eficiencia *round-trip* (85%) y un "
            "límite de 1.5 ciclos. Es la diferencia entre *observar* el BESS y *decirle qué hacer* "
            "con un valor en USD asociado. El ingreso es estimado sobre el CMG programado, no "
            "garantizado."
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

    _titulo("¿El BESS arbitra con el precio? (potencia neta vs CMG)", "14px 0 6px")
    st.caption(
        "Cada punto es una hora. Eje X = precio del nodo (CMG); eje Y = qué hizo el BESS "
        "(arriba de 0 = descargó, abajo = cargó). El color indica la hora del día. "
        "Lo ideal: puntos **abajo a la izquierda** (carga cuando está barato) y "
        "**arriba a la derecha** (descarga cuando está caro)."
    )
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
    st.caption(
        "La **correlación** resume el gráfico de arriba en un número de −1 a +1: cercano a "
        "**+1** = arbitra bien (sube precio → descarga); cercano a **0** = opera por horario, "
        "no por precio; **negativo** = opera al revés (revisar)."
    )

    # Modelo: importancia de hora vs CMG
    feats_b = ["hora_dia", "cmg_usd_mwh"]
    if len(dd) >= 48:
        m = RandomForestRegressor(n_estimators=150, max_depth=8, random_state=42, n_jobs=-1)
        m.fit(dd[feats_b].values, dd["potencia_neta_mw"].values)
        imp = pd.DataFrame({"var": ["Hora del día", "CMG nodo"],
                            "imp": m.feature_importances_}).sort_values("imp")
        _titulo("¿Qué decide cuándo carga o descarga el BESS?", "14px 0 6px")
        st.caption(
            "Un modelo aprende a predecir la operación del BESS a partir de dos pistas: la "
            "**hora del día** y el **precio (CMG)**. La barra más larga es la que más pesa: si "
            "manda 'Hora del día' opera con horario fijo; si manda 'CMG nodo' reacciona al precio."
        )
        figi = go.Figure(go.Bar(x=imp["imp"], y=imp["var"], orientation="h", marker_color=AES_VIOLETA))
        figi.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                           height=200, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Importancia relativa (qué pesa más)")
        st.plotly_chart(figi, use_container_width=True, key=f"ml_bess_imp_{cod}")

    # 4. Recomendación de arbitraje a futuro (CMG programado próximas horas)
    _render_arbitraje_milp(cod)


def _optimizar_bess(precios, pmax: float, energia_mwh: float,
                    eta_rt: float = 0.85, max_ciclos: float = 1.5, soc0: float = 0.0):
    """Optimiza el cronograma de carga/descarga del BESS para maximizar el ingreso
    por arbitraje sobre el CMG programado futuro. Programación LINEAL (no requiere
    binarios: con precios positivos nunca conviene cargar y descargar a la vez, así
    que el óptimo lo evita solo → rápido).

    Variables por hora t: carga c_t, descarga d_t ∈ [0, pmax]; estado s_t ∈ [0, E].
    Dinámica: s_t = s_{t-1} + η·c_t − d_t.   Objetivo: max Σ precio_t·(d_t − c_t).
    Restricción de ciclos: Σ d_t ≤ max_ciclos · E.

    Devuelve (carga[], descarga[], soc[], ingreso_usd) o None si no hay solver.
    """
    if not _PULP:
        return None
    T = len(precios)
    prob = pulp.LpProblem("arbitraje_bess", pulp.LpMaximize)
    c = [pulp.LpVariable(f"c{t}", 0, pmax) for t in range(T)]
    d = [pulp.LpVariable(f"d{t}", 0, pmax) for t in range(T)]
    s = [pulp.LpVariable(f"s{t}", 0, energia_mwh) for t in range(T)]

    prob += pulp.lpSum(precios[t] * (d[t] - c[t]) for t in range(T))
    for t in range(T):
        prev = soc0 if t == 0 else s[t - 1]
        prob += s[t] == prev + eta_rt * c[t] - d[t]
    prob += pulp.lpSum(d) <= max_ciclos * energia_mwh
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    if pulp.LpStatus[prob.status] != "Optimal":
        return None
    carga = np.array([c[t].value() or 0.0 for t in range(T)])
    desc = np.array([d[t].value() or 0.0 for t in range(T)])
    soc = np.array([s[t].value() or 0.0 for t in range(T)])
    ingreso = float(sum(precios[t] * (desc[t] - carga[t]) for t in range(T)))
    return carga, desc, soc, ingreso


def _render_arbitraje_milp(cod: str) -> None:
    """Optimizador de arbitraje: programa el BESS sobre el CMG programado futuro y
    estima el ingreso esperado. Reemplaza la heurística de 'horas baratas/caras' por
    un óptimo que respeta el estado de carga, la eficiencia y el límite de ciclos."""
    if not _PULP:
        _recomendacion_arbitraje(cod)   # fallback heurístico si no hay solver
        return
    nodo = CMG_NODO.get(BESS[cod]["parque"])
    if not nodo:
        return
    dp = _cmg_programado_hist(nodo, dias_atras=0)
    ahora = datetime.now(SANTIAGO).replace(tzinfo=None)
    if not dp.empty:
        dp = dp[dp["fecha_hora"] >= ahora].sort_values("fecha_hora")
    if dp.empty or len(dp) < 6:
        st.info("Sin CMG programado futuro suficiente para optimizar el arbitraje "
                "(se puebla con la adquisición / cron).")
        return

    fut = dp.head(48).copy()
    precios = fut["cmg_usd_mwh"].values
    pmax = BESS[cod]["pmax_mw"]
    horas = BESS_HORAS.get(cod) or 4.0
    energia_mwh = pmax * horas

    res = _optimizar_bess(precios, pmax, energia_mwh)
    if res is None:
        st.warning("El optimizador no encontró solución. Usando recomendación heurística.")
        _recomendacion_arbitraje(cod)
        return
    carga, desc, soc, ingreso = res
    horas_dur = "declaradas" if BESS_HORAS.get(cod) else "asumidas (4 h)"

    _titulo("Optimizador de arbitraje BESS (programación lineal sobre CMG futuro)", "16px 0 6px")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ingreso esperado", f"{ingreso:,.0f} USD", help=f"Horizonte {len(fut)} h")
    c2.metric("Energía descargada", f"{desc.sum():.0f} MWh")
    c3.metric("Ciclos equivalentes", f"{desc.sum() / energia_mwh:.2f}")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=fut["fecha_hora"], y=desc, name="Descargar (vender)",
                         marker_color=AES_VERDE))
    fig.add_trace(go.Bar(x=fut["fecha_hora"], y=-carga, name="Cargar (comprar)",
                         marker_color=AES_AZUL))
    fig.add_trace(go.Scatter(x=fut["fecha_hora"], y=precios, name="CMG programado",
                             yaxis="y2", line=dict(color=AES_VIOLETA, width=2)))
    fig.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                      height=340, margin=dict(l=0, r=0, t=10, b=0), barmode="relative",
                      yaxis_title="Potencia (MW)",
                      yaxis2=dict(title="USD/MWh", overlaying="y", side="right", showgrid=False),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)))
    fig.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    fig.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(fig, use_container_width=True, key=f"ml_bess_milp_{cod}")

    figs = go.Figure()
    figs.add_trace(go.Scatter(x=fut["fecha_hora"], y=soc, name="Estado de carga",
                              fill="tozeroy", line=dict(color=AES_CYAN, width=2),
                              fillcolor="rgba(77,200,220,0.15)"))
    figs.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                       height=200, margin=dict(l=0, r=0, t=10, b=0),
                       yaxis_title="MWh", yaxis=dict(range=[0, energia_mwh * 1.05]))
    figs.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    figs.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(figs, use_container_width=True, key=f"ml_bess_soc_{cod}")
    st.caption(f"Capacidad {energia_mwh:.0f} MWh ({horas:.1f} h {horas_dur}), eficiencia "
               f"round-trip 85%, máx. 1.5 ciclos. Óptimo: comprar barato (azul) y vender caro "
               "(verde) respetando el estado de carga. El ingreso es estimado sobre el CMG "
               "programado, no garantizado.")


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


# ── 6. Validación de recurso solar — NASA POWER vs Open-Meteo ───────────────────

@st.cache_data(ttl=1800)
def _meteo_por_fuente(parque: str, fuente: str, dias: int = 120) -> pd.DataFrame:
    """GHI horario de meteo_ernc para un parque y una fuente (open-meteo / nasa-power)."""
    from utils.db import get_client
    sb = get_client()
    desde = (datetime.now(SANTIAGO) - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        r = (sb.table("meteo_ernc").select("fecha_hora,ghi_wm2")
             .eq("parque", parque).eq("fuente", fuente).eq("es_forecast", False)
             .gte("fecha_hora", desde).order("fecha_hora").execute())
    except Exception:
        return pd.DataFrame()
    if not r.data:
        return pd.DataFrame()
    df = pd.DataFrame(r.data)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df.dropna(subset=["ghi_wm2"]).drop_duplicates("fecha_hora")


def _render_validacion_nasa(parque: str) -> None:
    with st.expander("¿Qué valida esta sección? (metodología)"):
        st.markdown(
            "Compara el **GHI de Open-Meteo** (el que alimenta el modelo y el forecast) "
            "contra el **GHI de NASA POWER** (satelital/reanálisis, fuente independiente) "
            "en las horas que ambas cubren.\n\n"
            "- **Sesgo (bias):** promedio Open-Meteo − NASA. Positivo = Open-Meteo sobreestima.\n"
            "- **RMSE / correlación:** cuánto coinciden hora a hora.\n\n"
            "NASA POWER publica con un rezago real de ~2-3 meses (~85 días), por eso es "
            "validación histórica, no tiempo real. Se puebla con `Adquisicion_nasa_ernc.py` "
            "(corrida diaria, ventana ~100 d)."
        )
    om = _meteo_por_fuente(parque, "open-meteo")
    na = _meteo_por_fuente(parque, "nasa-power")
    if na.empty:
        st.info("Aún no hay datos de NASA POWER. Corre `Adquisicion_nasa_ernc.py` "
                "(o espera el job diario). NASA publica con rezago de ~2-3 meses.")
        return
    if om.empty:
        st.info("Sin GHI de Open-Meteo histórico para cruzar.")
        return

    m = om.merge(na, on="fecha_hora", suffixes=("_om", "_nasa"))
    m = m[(m["ghi_wm2_om"] > 0) | (m["ghi_wm2_nasa"] > 0)]   # ignora la noche (ambos 0)
    if len(m) < 12:
        st.info(f"Solo {len(m)} horas solapadas entre fuentes — insuficiente para validar. "
                "Aumenta la ventana de NASA o espera más histórico.")
        return

    bias = (m["ghi_wm2_om"] - m["ghi_wm2_nasa"]).mean()
    rmse = float(np.sqrt(((m["ghi_wm2_om"] - m["ghi_wm2_nasa"]) ** 2).mean()))
    corr = m["ghi_wm2_om"].corr(m["ghi_wm2_nasa"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Sesgo Open-Meteo − NASA", f"{bias:+.0f} W/m²")
    c2.metric("RMSE", f"{rmse:.0f} W/m²")
    c3.metric("Correlación", f"{corr:.2f}")

    _titulo(f"GHI Open-Meteo vs NASA POWER — {NOMBRE_DISPLAY[parque]}", "12px 0 6px")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m["fecha_hora"], y=m["ghi_wm2_om"], name="Open-Meteo",
                             line=dict(color=AES_AZUL, width=1.8)))
    fig.add_trace(go.Scatter(x=m["fecha_hora"], y=m["ghi_wm2_nasa"], name="NASA POWER",
                             line=dict(color=AES_AMBAR, width=1.8, dash="dot")))
    st.plotly_chart(_layout_base(fig), use_container_width=True, key=f"ml_nasa_serie_{parque}")

    _titulo("Dispersión hora a hora (línea = acuerdo perfecto)", "12px 0 6px")
    mx = max(m["ghi_wm2_om"].max(), m["ghi_wm2_nasa"].max())
    figs = go.Figure()
    figs.add_trace(go.Scatter(x=m["ghi_wm2_nasa"], y=m["ghi_wm2_om"], mode="markers",
                              marker=dict(color=AES_AZUL, size=6, opacity=0.5),
                              hovertemplate="NASA %{x:.0f} · OM %{y:.0f}<extra></extra>", name="horas"))
    figs.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines",
                              line=dict(color=AES_MUTED, dash="dash"), name="y=x"))
    figs.update_layout(template="plotly_white", paper_bgcolor=AES_BLANCO, plot_bgcolor=AES_GRIS,
                       height=340, margin=dict(l=0, r=0, t=10, b=0),
                       xaxis_title="NASA POWER GHI (W/m²)", yaxis_title="Open-Meteo GHI (W/m²)")
    figs.update_xaxes(showgrid=True, gridcolor=AES_BORDE)
    figs.update_yaxes(showgrid=True, gridcolor=AES_BORDE)
    st.plotly_chart(figs, use_container_width=True, key=f"ml_nasa_scatter_{parque}")
    st.caption(
        f"{len(m)} horas comparadas. Un sesgo alto o correlación baja indica que Open-Meteo "
        "se desvía del recurso satelital → afecta el forecast y el modelo físico de ese parque."
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
        ["Forecast de generación", "Forecast probabilístico", "Detección de anomalías",
         "Predicción de CMG", "Análisis de eficiencia", "Soiling FV", "BESS — operación",
         "Validación recurso (NASA)"],
        horizontal=True, key="ml_analisis",
    )

    if analisis == "Forecast de generación":
        parque = st.selectbox("Parque", PARQUES_TODOS, format_func=lambda p: NOMBRE_DISPLAY[p],
                              key="ml_fc_parque")
        with st.spinner("Entrenando modelo..."):
            _render_forecast_gen(parque)

    elif analisis == "Forecast probabilístico":
        parque = st.selectbox("Parque", PARQUES_TODOS, format_func=lambda p: NOMBRE_DISPLAY[p],
                              key="ml_prob_parque")
        with st.spinner("Entrenando banda probabilística..."):
            _render_forecast_prob(parque)

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

    elif analisis == "Soiling FV":
        parque = st.selectbox("Parque solar", PARQUES_SOLAR,
                              format_func=lambda p: NOMBRE_DISPLAY[p], key="ml_soil_parque")
        with st.spinner("Estimando soiling..."):
            _render_soiling(parque)

    elif analisis == "BESS — operación":
        cod = st.selectbox("BESS", list(BESS.keys()),
                           format_func=lambda c: BESS[c]["nombre"], key="ml_bess_cod")
        with st.spinner("Analizando operación del BESS..."):
            _render_bess_ml(cod)

    elif analisis == "Validación recurso (NASA)":
        parque = st.selectbox("Parque solar", PARQUES_SOLAR, format_func=lambda p: NOMBRE_DISPLAY[p],
                              key="ml_nasa_parque")
        with st.spinner("Comparando fuentes de irradiancia..."):
            _render_validacion_nasa(parque)
