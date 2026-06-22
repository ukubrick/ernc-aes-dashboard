"""Mapa 2D pydeck para los 11 parques ERNC — Carto Light + ScatterplotLayer + TextLayer."""
import os
import pydeck as pdk
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


def maptiler_disponible() -> bool:
    return bool(_secret("MAPTILER_KEY"))


def _satelite_style_url(key: str) -> str:
    """URL del style satelital hospedado por MapTiler (imagen + etiquetas).

    IMPORTANTE: el componente DeckGlJsonChart de Streamlit exige que map_style sea
    un STRING (hace `.indexOf` sobre él). Un dict de style raster MapLibre revienta
    con 'e.mapStyle?.indexOf is not a function'. Por eso se usa la URL hospedada.
    La capa de nubes OpenWeather no puede inyectarse en una URL de style; requiere
    otro renderer (folium) y queda pendiente."""
    return f"https://api.maptiler.com/maps/hybrid/style.json?key={key}"

# Paleta AES por tecnologia (RGB)
_COLOR = {
    "Solar":  [59, 76, 232],    # AES_AZUL
    "Eólica": [77, 200, 220],   # AES_CYAN
}

MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

# Estilos de mapa base SIN token. Claro/Detallado usan estilos GL de Carto (string URL).
# Satélite se renderiza aparte como TileLayer raster de ESRI (ver render_mapa), porque
# pydeck exige token de Mapbox si el map_style se pasa como style-JSON dict.
MAP_STYLES = {
    "Claro":    "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    "Detallado": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
}

# Ciudades de referencia para dar contexto geográfico al mapa
_CIUDADES = [
    {"nombre": "Antofagasta", "lat": -23.65, "lon": -70.40},
    {"nombre": "Calama",      "lat": -22.46, "lon": -68.93},
    {"nombre": "La Serena",   "lat": -29.90, "lon": -71.25},
    {"nombre": "Santiago",    "lat": -33.45, "lon": -70.66},
    {"nombre": "Concepción",  "lat": -36.83, "lon": -73.05},
    {"nombre": "Los Ángeles", "lat": -37.47, "lon": -72.35},
]

# Bounds de Chile continental (lon_min, lat_min, lon_max, lat_max)
# Excluye Isla de Pascua y territorio antártico
_CHILE_BOUNDS = {
    "lat_min": -55.9,
    "lat_max": -17.5,
    "lon_min": -75.7,
    "lon_max": -66.0,
}

# Vista por defecto: Chile completo — zoom reducido para que los parques del norte
# no se aglomeren con los del sur (clúster solar Atacama vs eólicos Biobío)
_VIEW_DEFAULT = pdk.ViewState(
    latitude=-32.0,
    longitude=-70.5,
    zoom=3.9,
    pitch=0,
    bearing=0,
)

# Vista por parque: zoom centrado al seleccionar desde sidebar
_VIEW_PARQUE = {p: pdk.ViewState(
    latitude=COORDENADAS[p]["lat"],
    longitude=COORDENADAS[p]["lon"],
    zoom=8.5,
    pitch=0,
    bearing=0,
) for p in PARQUES_TODOS}


def _df(gen_por_parque: dict[str, float | None]) -> pd.DataFrame:
    filas = []
    for p in PARQUES_TODOS:
        coord = COORDENADAS[p]
        gen   = gen_por_parque.get(p) or 0.0
        pmax  = PMAX[p]
        fp    = round(gen / pmax * 100, 1) if pmax > 0 else 0.0
        tec   = TECNOLOGIA[p]
        col   = _COLOR[tec]
        radio = max(35000, pmax * 250)
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
            "radio": radio,
        })
    return pd.DataFrame(filas)


def render_mapa(
    gen_por_parque: dict[str, float | None],
    parque_activo: str | None = None,
    estilo: str = "Claro",
) -> None:
    df = _df(gen_por_parque)
    es_satelite = estilo == "Satelite"
    key_mt = _secret("MAPTILER_KEY")
    # Satelital: style raster MapLibre (MapTiler + nubes OpenWeather). Si no hay key,
    # se degrada a Detallado para no romper el render.
    if es_satelite and key_mt:
        map_style = _satelite_style_url(key_mt)
        map_provider = "mapbox"
    elif es_satelite and not key_mt:
        st.info("Vista satelital requiere MAPTILER_KEY en secrets. Mostrando mapa Detallado.")
        es_satelite = False
        map_style = MAP_STYLES["Detallado"]
        map_provider = "carto"
    else:
        map_style = MAP_STYLES.get(estilo, MAP_STYLES["Claro"])
        map_provider = "carto"
    # En satelital el texto va en blanco para contrastar con el fondo oscuro
    txt_color = [255, 255, 255, 235] if es_satelite else [26, 31, 54, 230]
    ciudad_color = [255, 255, 255, 150] if es_satelite else [107, 114, 128, 200]
    df_ciudades = pd.DataFrame(_CIUDADES)

    # Vista: zoom al parque activo si viene del sidebar, sino Chile completo
    if parque_activo and parque_activo in _VIEW_PARQUE:
        view = _VIEW_PARQUE[parque_activo]
    else:
        view = _VIEW_DEFAULT

    halo = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_radius="radio",
        get_fill_color=["r", "g", "b", 18],
        stroked=False,
        pickable=False,
    )

    circles = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_radius=22000,
        get_fill_color=["r", "g", "b", "alpha"],
        get_line_color=["r", "g", "b"],
        stroked=True,
        line_width_min_pixels=2,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 120],
    )

    labels = pdk.Layer(
        "TextLayer",
        data=df,
        get_position=["lon", "lat"],
        get_text="nombre",
        get_size=12,
        get_color=txt_color,
        get_alignment_baseline="'bottom'",
        get_pixel_offset=[0, -28],
        background=True,
        get_background_color=[0, 0, 0, 120] if es_satelite else [255, 255, 255, 160],
        pickable=False,
    )

    # Ciudades de referencia — contexto geográfico
    ciudades = pdk.Layer(
        "TextLayer",
        data=df_ciudades,
        get_position=["lon", "lat"],
        get_text="nombre",
        get_size=10,
        get_color=ciudad_color,
        get_alignment_baseline="'top'",
        get_pixel_offset=[0, 6],
        pickable=False,
    )
    ciudades_dot = pdk.Layer(
        "ScatterplotLayer",
        data=df_ciudades,
        get_position=["lon", "lat"],
        get_radius=2200,
        get_fill_color=ciudad_color,
        pickable=False,
    )

    tooltip = {
        "html": (
            "<div style='"
            "background:white;"
            "border:1px solid #E5E7EB;"
            "border-radius:8px;"
            "padding:12px 16px;"
            "font-family:Inter,sans-serif;"
            "box-shadow:0 4px 12px rgba(0,0,0,0.1);"
            "min-width:200px"
            "'>"
            "<div style='font-size:13px;font-weight:700;color:#1A1F36;margin-bottom:4px'>{nombre}</div>"
            "<div style='font-size:11px;color:#6B7280;margin-bottom:10px'>{tecnologia}</div>"
            "<div style='display:flex;justify-content:space-between;margin-bottom:4px'>"
            "  <span style='font-size:11px;color:#6B7280'>Generacion actual</span>"
            "  <span style='font-size:12px;font-weight:600;color:#1A1F36'>{gen_mw} MW</span>"
            "</div>"
            "<div style='display:flex;justify-content:space-between;margin-bottom:4px'>"
            "  <span style='font-size:11px;color:#6B7280'>Cap. instalada</span>"
            "  <span style='font-size:11px;color:#1A1F36'>{pmax_mw} MW</span>"
            "</div>"
            "<div style='display:flex;justify-content:space-between;"
            "border-top:1px solid #E5E7EB;padding-top:8px;margin-top:4px'>"
            "  <span style='font-size:11px;color:#6B7280'>Factor de planta</span>"
            "  <span style='font-size:13px;font-weight:700;color:#3B4CE8'>{factor_pct}%</span>"
            "</div>"
            "</div>"
        ),
        "style": {"padding": "0", "background": "transparent", "border": "none"},
    }

    deck = pdk.Deck(
        layers=[ciudades_dot, ciudades, halo, circles, labels],
        initial_view_state=view,
        tooltip=tooltip,
        map_style=map_style,
        map_provider=map_provider,
        views=[pdk.View(
            type="MapView",
            controller={"scrollZoom": True, "dragPan": True},
        )],
    )

    st.pydeck_chart(deck, use_container_width=True, key=f"mapa_ernc_{parque_activo or 'all'}_{estilo}")
