"""
Tab Meteo & Sistema — alertas meteorológicas anticipadas (forecast Open-Meteo) +
contexto de mercado (CMG nacional). Reutiliza meteo_ernc (es_forecast=True) y cmg_ernc.
No requiere tablas nuevas.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from config import (
    NOMBRE_DISPLAY, PARQUES_SOLAR, PARQUES_EOLICA, PARQUES_TODOS,
    CMG_NODOS_TODOS, TRACKER_STOW_WIND_MS,
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


def _ahora_santiago() -> datetime:
    return datetime.now(ZoneInfo("America/Santiago")).replace(tzinfo=None)


@st.cache_data(ttl=900)
def _cargar_forecast_meteo(horas: int = 48) -> pd.DataFrame:
    """Forecast meteo próximo (es_forecast=True) de todos los parques."""
    try:
        from utils.db import get_client
        sb = get_client()
        ahora = _ahora_santiago()
        desde = (ahora - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        hasta = (ahora + timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S")
        res = (
            sb.table("meteo_ernc")
            .select(
                "parque,fecha_hora,ghi_wm2,cloud_cover_pct,cloudcover_low_pct,"
                "wind_speed_10m,wind_speed_100m,wind_gusts_10m,"
                "p_fv_estimada_mw,p_eolica_estimada_mw,es_forecast"
            )
            .eq("es_forecast", True)
            .gte("fecha_hora", desde)
            .lte("fecha_hora", hasta)
            .order("fecha_hora")
            .execute()
        )
        if res.data:
            df = pd.DataFrame(res.data)
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
            return df
    except Exception:
        pass
    return pd.DataFrame()


_ALERTAS_CSS = """
<style>
@keyframes alertaIn{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}
@keyframes pulseAlta{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0.0)}
  50%{box-shadow:0 0 0 4px rgba(239,68,68,0.12)}}
.alerta-card{border-radius:0 10px 10px 0;padding:10px 16px;margin-bottom:8px;
  animation:alertaIn .35s ease both}
.alerta-alta{animation:alertaIn .35s ease both, pulseAlta 2.2s ease-in-out infinite}
.alerta-dot{display:inline-block;width:8px;height:8px;border-radius:50%}
</style>
"""


def _seccion_alertas(df: pd.DataFrame) -> None:
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:4px 0 10px'>"
        f"Alertas meteorologicas anticipadas — proximas 48 horas</div>",
        unsafe_allow_html=True,
    )
    if df.empty:
        st.info("Sin forecast meteo disponible. Ejecuta Adquisicion_meteo_ernc.py o espera el cron.")
        return

    alertas = []  # (prioridad, parque, titulo, detalle)
    # Eólica: ráfagas (cut-out) y déficit de recurso
    for p in PARQUES_EOLICA:
        sub = df[df["parque"] == p]
        if sub.empty:
            continue
        criticas = sub[sub["wind_gusts_10m"] > 20]
        altas    = sub[(sub["wind_gusts_10m"] > 16) & (sub["wind_gusts_10m"] <= 20)]
        if not criticas.empty:
            r = criticas.iloc[0]
            alertas.append(("alta", NOMBRE_DISPLAY[p], "Rafagas sobre cut-out",
                            f"{r['wind_gusts_10m']:.1f} m/s a las {str(r['fecha_hora'])[5:16]} — riesgo de parada de turbinas"))
        elif not altas.empty:
            r = altas.iloc[0]
            alertas.append(("media", NOMBRE_DISPLAY[p], "Rafagas altas",
                            f"{r['wind_gusts_10m']:.1f} m/s a las {str(r['fecha_hora'])[5:16]} — acercandose al cut-out"))
        else:
            # Recurso eólico pobre sostenido (>6 h con viento hub < 3 m/s = bajo cut-in)
            flojo = sub[sub["wind_speed_100m"] < 3]
            if len(flojo) >= 6:
                alertas.append(("baja", NOMBRE_DISPLAY[p], "Recurso eolico bajo",
                                f"{len(flojo)} h con viento hub < 3 m/s (cut-in) — generacion limitada"))
    # Solar: viento fuerte que gatilla stow de trackers (pierde ganancia de tracking)
    for p in PARQUES_SOLAR:
        sub = df[df["parque"] == p].copy()
        if sub.empty:
            continue
        sub["peor_viento"] = sub[["wind_speed_10m", "wind_gusts_10m"]].max(axis=1)
        stow = sub[sub["peor_viento"] >= TRACKER_STOW_WIND_MS]
        if not stow.empty:
            r = stow.iloc[0]
            n_h = len(stow)
            alertas.append(("alta", NOMBRE_DISPLAY[p], "Stow de trackers por viento fuerte",
                            f"Viento/rafaga {r['peor_viento']:.1f} m/s a las {str(r['fecha_hora'])[5:16]} "
                            f"(≥{TRACKER_STOW_WIND_MS:.0f} m/s) — {n_h} h con seguidores en stow, merma de generacion"))

    # Solar: nubosidad que reduce recurso en horas diurnas
    for p in PARQUES_SOLAR:
        sub = df[(df["parque"] == p) & (df["ghi_wm2"] > 150)]
        if sub.empty:
            continue
        nublado_alto = sub[sub["cloud_cover_pct"] > 70]
        nublado_med  = sub[(sub["cloud_cover_pct"] > 50) & (sub["cloud_cover_pct"] <= 70)]
        if not nublado_alto.empty:
            r = nublado_alto.iloc[0]
            alertas.append(("media", NOMBRE_DISPLAY[p], "Nubosidad alta en horas de sol",
                            f"Cobertura {r['cloud_cover_pct']:.0f}% a las {str(r['fecha_hora'])[5:16]} — caida de GHI esperada"))
        elif not nublado_med.empty:
            r = nublado_med.iloc[0]
            alertas.append(("baja", NOMBRE_DISPLAY[p], "Nubosidad moderada",
                            f"Cobertura {r['cloud_cover_pct']:.0f}% a las {str(r['fecha_hora'])[5:16]} — leve merma de recurso"))

    if not alertas:
        st.markdown(
            f"<div style='background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;"
            f"padding:12px 16px;color:#166534;font-size:13px'>"
            f"Sin alertas meteorologicas en las proximas 48 horas. Recurso estable.</div>",
            unsafe_allow_html=True,
        )
        return

    orden = {"alta": 0, "media": 1, "baja": 2}
    alertas.sort(key=lambda a: orden.get(a[0], 3))

    # Resumen por prioridad
    n_alta  = sum(1 for a in alertas if a[0] == "alta")
    n_media = sum(1 for a in alertas if a[0] == "media")
    n_baja  = sum(1 for a in alertas if a[0] == "baja")
    st.markdown(
        _ALERTAS_CSS +
        f"<div style='display:flex;gap:10px;margin-bottom:12px;font-size:11px;font-weight:600'>"
        f"<span><span class='alerta-dot' style='background:{AES_ROJO}'></span> {n_alta} alta</span>"
        f"<span><span class='alerta-dot' style='background:{AES_AMBAR}'></span> {n_media} media</span>"
        f"<span><span class='alerta-dot' style='background:{AES_AZUL}'></span> {n_baja} baja</span></div>",
        unsafe_allow_html=True,
    )

    _bg  = {"alta": "#FEF2F2", "media": "#FFFBEB", "baja": "#EFF6FF"}
    _bd  = {"alta": AES_ROJO, "media": AES_AMBAR, "baja": AES_AZUL}
    _lb  = {"alta": "PRIORIDAD ALTA", "media": "PRIORIDAD MEDIA", "baja": "PRIORIDAD BAJA"}
    _cls = {"alta": "alerta-card alerta-alta", "media": "alerta-card", "baja": "alerta-card"}
    for sev, parque, titulo, detalle in alertas:
        st.markdown(
            f"<div class='{_cls[sev]}' style='background:{_bg[sev]};border-left:4px solid {_bd[sev]}'>"
            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:3px'>"
            f"<span style='font-size:9px;font-weight:700;color:{_bd[sev]};letter-spacing:1px;"
            f"background:{_bd[sev]}22;padding:2px 8px;border-radius:20px'>{_lb[sev]}</span>"
            f"<span style='font-size:11px;color:{AES_MUTED};margin-left:auto'>{parque}</span></div>"
            f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO}'>{titulo}</div>"
            f"<div style='font-size:12px;color:{AES_MUTED}'>{detalle}</div></div>",
            unsafe_allow_html=True,
        )


def _heatmap(df: pd.DataFrame, parques: list, col: str, titulo: str, escala, key: str, fmt: str,
             zmin: float | None = None, zmax: float | None = None) -> None:
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:14px 0 6px'>{titulo}</div>",
        unsafe_allow_html=True,
    )
    sub = df[df["parque"].isin(parques)].copy()
    if sub.empty or col not in sub.columns:
        st.info("Sin datos de forecast para esta vista.")
        return
    sub["etq"] = sub["fecha_hora"].dt.strftime("%d/%m %Hh")
    pivot = sub.pivot_table(index="parque", columns="etq", values=col, aggfunc="mean")
    orden = [p for p in parques if p in pivot.index]
    # Ordenar columnas cronológicamente
    cols_ord = sorted(pivot.columns, key=lambda e: sub[sub["etq"] == e]["fecha_hora"].iloc[0])
    pivot = pivot.reindex(index=orden, columns=cols_ord)
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=[NOMBRE_DISPLAY[p] for p in pivot.index],
        colorscale=escala,
        zmin=zmin, zmax=zmax,
        hovertemplate="%{y} · %{x}: %{z:" + fmt + "}<extra></extra>",
        colorbar=dict(thickness=12),
    ))
    fig.update_layout(
        template="plotly_white", paper_bgcolor=AES_BLANCO,
        height=60 + 34 * len(orden), margin=dict(l=0, r=0, t=6, b=0),
        xaxis=dict(tickfont=dict(size=9)),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def _seccion_cmg_sistema(cmg_rows: list) -> None:
    st.markdown(
        f"<div style='font-size:13px;font-weight:600;color:{AES_TEXTO};margin:16px 0 8px'>"
        f"Contexto de mercado — costo marginal nacional (CMG online CEN)</div>",
        unsafe_allow_html=True,
    )
    if not cmg_rows:
        st.info("Sin datos de CMG disponibles.")
        return
    idx = {r["nodo"]: r.get("cmg_usd_mwh") for r in cmg_rows}
    norte = idx.get("CRUCERO_______220")
    sur   = idx.get("CHARRUA_______220")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("CMG Norte (CRUCERO)", f"{norte:.1f} USD/MWh" if norte is not None else "—",)
    with c2:
        st.metric("CMG Sur (CHARRUA)", f"{sur:.1f} USD/MWh" if sur is not None else "—",)
    with c3:
        spread = (norte - sur) if (norte is not None and sur is not None) else None
        st.metric("Spread Norte-Sur", f"{spread:+.1f} USD/MWh" if spread is not None else "—",)

    st.caption(
        "El ranking de CMG por nodo (barras) y la demanda programada del SEN viven en la "
        "subsección **CMG** de esta vista. Aquí solo se muestra el resumen Norte/Sur."
    )


def render_tab_meteo_sistema(cmg_rows: list | None = None) -> None:
    df = _cargar_forecast_meteo(48)

    # 1) Heatmaps primero (nubosidad → viento)
    if not df.empty:
        _heatmap(
            df, PARQUES_SOLAR, "cloud_cover_pct",
            "Nubosidad total pronosticada (%) — anticipa caidas de recurso solar",
            [[0, "#FEF9C3"], [0.5, AES_CYAN], [1, "#1E3A8A"]],
            "meteo_hm_nubes", ".0f", zmin=0, zmax=100,
        )
        # Un heatmap plano de nubosidad es ambiguo: puede parecer un fallo de datos
        # cuando en realidad el pronostico es de cielos despejados (habitual en Atacama).
        # Si toda la ventana esta ~0%, se muestra un aviso explicito.
        nub_solar = pd.to_numeric(
            df[df["parque"].isin(PARQUES_SOLAR)]["cloud_cover_pct"], errors="coerce"
        )
        if not nub_solar.empty and nub_solar.max() <= 5:
            st.caption(
                "Cielos despejados pronosticados (≤5% de nubosidad en las próximas 48 h) "
                "— recurso solar óptimo, sin caídas de GHI por nubes. El heatmap plano es "
                "correcto, no un fallo de datos."
            )
        # Viento 10m / ráfagas en los SOLARES — anticipa el stow de trackers.
        # Escala con quiebre en el umbral de stow (verde < umbral, ámbar→rojo sobre él).
        _stow_frac = min(max(TRACKER_STOW_WIND_MS / 25.0, 0.05), 0.95)
        _esc_stow = [[0, "#F0FDF4"], [max(_stow_frac - 0.001, 0.01), "#FDE68A"],
                     [_stow_frac, AES_AMBAR], [1, AES_ROJO]]
        _heatmap(
            df, PARQUES_SOLAR, "wind_gusts_10m",
            f"Rafagas 10m pronosticadas (m/s) — anticipan stow de trackers (≥{TRACKER_STOW_WIND_MS:.0f} m/s)",
            _esc_stow, "meteo_hm_rafagas_solar", ".1f", zmin=0, zmax=25,
        )
        _heatmap(
            df, PARQUES_EOLICA, "wind_speed_100m",
            "Viento hub 100m pronosticado (m/s) — recurso eolico proximas 48h",
            [[0, "#F5F7FA"], [0.5, AES_CYAN], [1, AES_AZUL]],
            "meteo_hm_viento", ".1f", zmin=0, zmax=15,
        )
        st.divider()

    # 2) Alertas priorizadas (alta/media/baja)
    _seccion_alertas(df)

    # 3) Contexto de mercado CMG (solo resumen Norte/Sur; el ranking de barras y la
    #    demanda programada del SEN viven en la subsección CMG, no aquí).
    st.divider()
    _seccion_cmg_sistema(cmg_rows or [])
