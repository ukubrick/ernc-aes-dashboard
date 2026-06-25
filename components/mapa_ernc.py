"""Mapa satelital de los 11 parques ERNC.

folium + Esri World Imagery (sin token) con nubosidad OpenWeather en vivo, sombra
día/noche en tiempo real y flechas de viento actual por parque.
"""
import os
import streamlit as st
import pandas as pd

from config import NOMBRE_DISPLAY, COORDENADAS, TECNOLOGIA, PMAX, PARQUES_TODOS


def _secret(nombre: str) -> str | None:
    """Lee una credencial de st.secrets primero, luego de variables de entorno."""
    try:
        if nombre in st.secrets:
            return st.secrets[nombre]
    except Exception:
        pass
    return os.environ.get(nombre)


# Paleta AES por tecnologia (RGB)
_COLOR = {
    "Solar":  [59, 76, 232],    # AES_AZUL
    "Eólica": [77, 200, 220],   # AES_CYAN
}


# ── Nubosidad: tile OWM clouds_new (textura real) + filtros de color ────────────
# El tile gratuito clouds_new entrega nubes blancas/grises sobre fondo transparente,
# donde la densidad se codifica como opacidad. El color se logra con filtros CSS
# (sepia+saturate+hue-rotate) aplicados por className → permite paletas, incl. ROJA.
_CLOUD_FILTROS = {
    "f-natural": "filter:contrast(1.5) brightness(1.05) saturate(1.0);",
    "f-azul":    "filter:sepia(1) saturate(6) hue-rotate(175deg) brightness(1.0) contrast(1.5);",
    "f-roja":    "filter:sepia(1) saturate(10) hue-rotate(-55deg) brightness(1.1) contrast(1.6);",
    "f-violeta": "filter:sepia(1) saturate(7) hue-rotate(240deg) brightness(1.05) contrast(1.5);",
}
# clase = filtro de color · refuerzo = nº de capas apiladas (densifica) · opacity.
_CLOUD_PRESETS = {
    "Natural (blanco)": {"opacity": 1.0, "refuerzo": 2, "clase": "f-natural"},
    "Azul":             {"opacity": 1.0, "refuerzo": 2, "clase": "f-azul"},
    "Roja":             {"opacity": 1.0, "refuerzo": 2, "clase": "f-roja"},
    "Violeta":          {"opacity": 1.0, "refuerzo": 2, "clase": "f-violeta"},
}


def _build_cloud_layers(folium, key: str, cfg: dict) -> list:
    """TileLayers de nubosidad OWM clouds_new para el preset (color) elegido."""
    url = f"https://tile.openweathermap.org/map/clouds_new/{{z}}/{{x}}/{{y}}.png?appid={key}"
    clase = cfg.get("clase")
    n = max(1, int(cfg.get("refuerzo", 1)))
    layers = []
    for i in range(n):
        layers.append(folium.TileLayer(
            tiles=url, attr="© OpenWeather",
            name="Nubosidad" if i == 0 else f"Nubosidad (refuerzo {i})",
            overlay=True, control=(i == 0), opacity=cfg["opacity"], show=True,
            className=clase or "",
        ))
    return layers


def _css_filtros_nubes() -> str:
    """<style> con los filtros de color (se inyecta en el <head> del mapa folium)."""
    reglas = "".join(f".{c} img{{{f}}}" for c, f in _CLOUD_FILTROS.items())
    reglas += "".join(f".leaflet-layer.{c}{{{f}}}" for c, f in _CLOUD_FILTROS.items())
    return f"<style>{reglas}</style>"


@st.cache_data(ttl=300)
def _viento_actual_parques() -> dict:
    """Viento ACTUAL (velocidad 10m + dirección) de los 11 parques desde Open-Meteo,
    en una sola llamada. Funciona para solares y eólicos por igual (no depende de lo
    que se guarde en meteo_ernc). Retorna {parque: {"dir": grados, "vel": m/s}}."""
    import requests
    orden = list(PARQUES_TODOS)
    lats = ",".join(f"{COORDENADAS[p]['lat']:.4f}" for p in orden)
    lons = ",".join(f"{COORDENADAS[p]['lon']:.4f}" for p in orden)
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lats, "longitude": lons,
                    "current": "wind_speed_10m,wind_direction_10m",
                    "wind_speed_unit": "ms", "timezone": "America/Santiago"},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {}
    objs = data if isinstance(data, list) else [data]
    out = {}
    for p, o in zip(orden, objs):
        cur = o.get("current", {})
        d = cur.get("wind_direction_10m")
        v = cur.get("wind_speed_10m")
        if d is not None:
            out[p] = {"dir": float(d), "vel": float(v) if v is not None else None}
    return out

# Ciudades de referencia para dar contexto geográfico al mapa
_CIUDADES = [
    {"nombre": "Antofagasta", "lat": -23.65, "lon": -70.40},
    {"nombre": "Calama",      "lat": -22.46, "lon": -68.93},
    {"nombre": "La Serena",   "lat": -29.90, "lon": -71.25},
    {"nombre": "Santiago",    "lat": -33.45, "lon": -70.66},
    {"nombre": "Concepción",  "lat": -36.83, "lon": -73.05},
    {"nombre": "Los Ángeles", "lat": -37.47, "lon": -72.35},
]

# Los 5 parques del complejo Andes Solar están a < 2 km entre sí: sus etiquetas se
# apilan. Se les da un offset vertical escalonado para que se lean separadas.
_LABEL_OFFSET = {
    "AS1":  [12, -34], "AS2A": [12, -20], "AS2B": [12, -6],
    "AS3":  [12, 8],   "AS4":  [12, 22],
}


def _df(gen_por_parque: dict[str, float | None]) -> pd.DataFrame:
    filas = []
    for p in PARQUES_TODOS:
        coord = COORDENADAS[p]
        gen   = gen_por_parque.get(p) or 0.0
        pmax  = PMAX[p]
        fp    = round(gen / pmax * 100, 1) if pmax > 0 else 0.0
        tec   = TECNOLOGIA[p]
        col   = _COLOR[tec]
        # Radio en PÍXELES (no metros): tamaño constante en pantalla a cualquier zoom.
        # Proporcional a la capacidad pero acotado para no tapar el terreno al hacer zoom.
        radio_px = max(6.0, min(13.0, 5.0 + (pmax ** 0.5) * 0.55))
        filas.append({
            "parque":     p,
            "nombre":     NOMBRE_DISPLAY[p],
            "lat":        coord["lat"],
            "lon":        coord["lon"],
            "gen_mw":     round(gen, 1),
            "pmax_mw":    pmax,
            "factor_pct": fp,
            "tecnologia": tec,
            "r": col[0], "g": col[1], "b": col[2],
            "alpha": max(80, min(230, int(80 + fp * 1.5))) if fp > 0 else 60,
            "radio_px":   round(radio_px, 1),
            "halo_px":    round(radio_px * 1.9, 1),
            "off_x":      _LABEL_OFFSET.get(p, [10, -6])[0],
            "off_y":      _LABEL_OFFSET.get(p, [10, -6])[1],
        })
    return pd.DataFrame(filas)


def _render_satelite_folium(df: pd.DataFrame, parque_activo: str | None) -> None:
    """Mapa satelital con folium: imagen ESRI + nubes OpenWeather en vivo +
    sombra día/noche (Terminator). folium/Leaflet sí renderiza overlays raster,
    a diferencia de pydeck."""
    import folium
    from folium.plugins import Terminator
    from streamlit_folium import st_folium

    if parque_activo and parque_activo in COORDENADAS:
        center = [COORDENADAS[parque_activo]["lat"], COORDENADAS[parque_activo]["lon"]]
        zoom = 11
    else:
        # Vista por defecto centrada en la región de Antofagasta (complejo solar norte),
        # para observar la nubosidad sobre ese sector.
        center, zoom = [-23.8, -69.1], 7

    m = folium.Map(location=center, zoom_start=zoom, tiles=None, control_scale=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri — World Imagery", name="Satélite", overlay=False, control=False,
    ).add_to(m)
    # Etiquetas de referencia (lugares/carreteras) semitransparentes encima
    folium.TileLayer(
        tiles="https://basemaps.cartocdn.com/rastertiles/dark_only_labels/{z}/{x}/{y}{r}.png",
        attr="© CARTO", name="Etiquetas", overlay=True, control=True, opacity=0.9,
    ).add_to(m)

    # Controles de capas meteorológicas
    cc1, cc2, cc3 = st.columns([1, 1, 1.2])
    ver_nubes = cc1.checkbox("Nubosidad", value=True,
                             key=f"chk_nubes_{parque_activo or 'all'}")
    ver_viento = cc2.checkbox("Dirección del viento", value=True,
                              key=f"chk_viento_{parque_activo or 'all'}")
    color_nubes = cc3.selectbox("Color de nubes", list(_CLOUD_PRESETS),
                                index=0, key=f"cloud_color_{parque_activo or 'all'}")

    # ── Nubosidad: tile OWM clouds_new (textura real) con filtro de color ──
    owm = _secret("OPENWEATHER_KEY")
    if ver_nubes and owm:
        m.get_root().header.add_child(folium.Element(_css_filtros_nubes()))
        for layer in _build_cloud_layers(folium, owm, _CLOUD_PRESETS[color_nubes]):
            layer.add_to(m)

    # Sombra día/noche en tiempo real
    Terminator().add_to(m)

    # ── Viento ACTUAL (todos los parques): flecha grande + velocidad encima ──
    if ver_viento:
        viento = _viento_actual_parques()
        fgv = folium.FeatureGroup(name="Viento", show=True)
        for _, r in df.iterrows():
            w = viento.get(r["parque"])
            if not w or w.get("dir") is None:
                continue
            vel = w.get("vel")
            # dir meteorológico = de dónde viene → la flecha apunta hacia donde va (+180).
            # El glifo ➜ apunta al este (0° CSS), y el rumbo es 0=N/90=E → rotar (rumbo-90).
            rumbo = (w["dir"] + 180) % 360
            rot = (rumbo - 90) % 360
            col = "#EF4444" if (vel or 0) >= 12 else ("#F59E0B" if (vel or 0) >= 7 else "#22D3EE")
            vtxt = f"{vel:.1f}" if vel is not None else "s/d"
            # Flecha grande rotada + etiqueta de velocidad fija (no rota) debajo
            html = (
                "<div style='position:relative;width:54px;height:54px'>"
                f"<div style='position:absolute;top:0;left:15px;transform:rotate({rot}deg);"
                f"font-size:30px;line-height:30px;color:{col};"
                f"text-shadow:0 0 4px #000,0 0 4px #000'>&#10148;</div>"
                f"<div style='position:absolute;bottom:0;left:0;width:54px;text-align:center;"
                f"font-size:11px;font-weight:700;color:#fff;text-shadow:0 0 3px #000,0 0 3px #000'>"
                f"{vtxt} m/s</div></div>"
            )
            folium.Marker(
                location=[r["lat"], r["lon"]],
                icon=folium.DivIcon(html=html, icon_size=(54, 54), icon_anchor=(27, 27)),
                tooltip=f"{r['nombre']} — viento {vtxt} m/s desde {w['dir']:.0f}°",
            ).add_to(fgv)
        fgv.add_to(m)

    # Ciudades de referencia
    for c in _CIUDADES:
        folium.CircleMarker(
            location=[c["lat"], c["lon"]], radius=2, color="#FFFFFF",
            fill=True, fill_color="#FFFFFF", fill_opacity=0.7, weight=0,
            tooltip=c["nombre"],
        ).add_to(m)

    # Parques: círculo de color por tecnología con popup
    for _, r in df.iterrows():
        color = f"rgb({int(r['r'])},{int(r['g'])},{int(r['b'])})"
        popup = folium.Popup(
            f"<b>{r['nombre']}</b><br>{r['tecnologia']}<br>"
            f"Gen: {r['gen_mw']} MW<br>Cap: {r['pmax_mw']} MW<br>"
            f"FP: {r['factor_pct']}%",
            max_width=220,
        )
        folium.CircleMarker(
            location=[r["lat"], r["lon"]],
            radius=float(r["radio_px"]) * 0.7,
            color="#FFFFFF", weight=1.2,
            fill=True, fill_color=color, fill_opacity=min(0.9, r["alpha"] / 255 + 0.2),
            popup=popup, tooltip=r["nombre"],
        ).add_to(m)

    folium.LayerControl(collapsed=True, position="topright").add_to(m)
    st_folium(m, use_container_width=True, height=560,
              returned_objects=[], key=f"mapa_folium_{parque_activo or 'all'}")

    from datetime import datetime
    from zoneinfo import ZoneInfo
    # America/Santiago maneja el cambio horario (UTC-4 invierno / UTC-3 verano),
    # a diferencia del offset fijo -3 que adelantaba 1 h en invierno.
    ahora = datetime.now(ZoneInfo("America/Santiago")).strftime("%d/%m %H:%M")
    st.caption(
        f"Hora actual (Santiago): {ahora} hrs · Sombra día/noche en tiempo real · "
        "Nubosidad: cobertura en vivo (OpenWeather, ~cada 10 min) — color configurable · "
        "Flechas = dirección a la que sopla el viento (color por velocidad) · "
        "Imagen satelital: composición estática Esri World Imagery (sin fecha por tile)."
    )


def render_mapa(
    gen_por_parque: dict[str, float | None],
    parque_activo: str | None = None,
) -> None:
    """Mapa satelital (folium + Esri World Imagery) con nubosidad OWM, día/noche y viento."""
    df = _df(gen_por_parque)

    # Auto-refresco del mapa cada 5 min: refresca nubosidad/viento/día-noche sin que
    # el usuario tenga que recargar la página ni cambiar de sección. Combinado con el
    # TTL de 5 min de _viento_actual_parques + tile OWM en vivo, trae datos nuevos.
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=300_000, key="mapa_autorefresh")
    except Exception:
        pass

    try:
        _render_satelite_folium(df, parque_activo)
    except Exception as e:
        st.error(f"No se pudo cargar el mapa satelital: {e}")
