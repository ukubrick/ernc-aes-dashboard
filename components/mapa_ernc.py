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


# Paleta AES por tecnologia (RGB)
_COLOR = {
    "Solar":  [59, 76, 232],    # AES_AZUL
    "Eólica": [77, 200, 220],   # AES_CYAN
}


# ── Nubosidad como área de colores (Open-Meteo, sin key) ───────────────────────

@st.cache_data(ttl=300)
def _cloud_grid(lat0: float, lon0: float, delta: float, n: int = 9) -> list[tuple]:
    """Grilla n×n de nubosidad actual (%) alrededor de (lat0,lon0) ±delta.
    Una sola llamada a Open-Meteo (coords separadas por coma, sin API key).
    Retorna [(lat, lon, cloud_pct), ...]."""
    import requests
    lats = [lat0 - delta + 2 * delta * i / (n - 1) for i in range(n)]
    lons = [lon0 - delta + 2 * delta * j / (n - 1) for j in range(n)]
    pares = [(la, lo) for la in lats for lo in lons]
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": ",".join(f"{la:.3f}" for la, _ in pares),
                "longitude": ",".join(f"{lo:.3f}" for _, lo in pares),
                "current": "cloud_cover",
                "timezone": "America/Santiago",
            },
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    # Con múltiples coords Open-Meteo devuelve una lista de objetos
    objs = data if isinstance(data, list) else [data]
    out = []
    for o in objs:
        cur = o.get("current", {})
        cc = cur.get("cloud_cover")
        if cc is not None:
            out.append((o.get("latitude"), o.get("longitude"), float(cc)))
    return out


def _cloud_color(pct: float) -> str:
    """Color HEX para un % de nubosidad: azul translúcido (despejado) → blanco/gris (cubierto)."""
    p = max(0.0, min(100.0, pct)) / 100.0
    # interpola de azul claro (#7FB2FF) a gris-blanco (#E8ECF2)
    r = int(127 + (232 - 127) * p)
    g = int(178 + (236 - 178) * p)
    b = int(255 + (242 - 255) * p)
    return f"#{r:02x}{g:02x}{b:02x}"


@st.cache_data(ttl=300)
def _meteo_viento_por_parque() -> dict:
    """Última dirección/velocidad de viento (hub) por parque desde meteo_ernc.
    Retorna {parque: {"dir": grados_meteo, "vel": m/s}}."""
    from utils.db import query_meteo_parque
    out = {}
    for p in PARQUES_TODOS:
        try:
            filas = query_meteo_parque(p, horas=6)
        except Exception:
            filas = []
        if not filas:
            continue
        # más reciente con dirección válida
        for f in reversed(filas):
            d = f.get("wind_dir_80m")
            v = f.get("wind_speed_100m") or f.get("wind_speed_10m")
            if d is not None:
                out[p] = {"dir": float(d), "vel": float(v) if v is not None else None}
                break
    return out

MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

# Estilos de mapa base SIN token. Claro/Detallado usan estilos GL de Carto (string URL).
# Satélite se renderiza aparte como TileLayer raster de ESRI (ver render_mapa), porque
# pydeck exige token de Mapbox si el map_style se pasa como style-JSON dict.
MAP_STYLES = {
    "Claro":    "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    "Detallado": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
}

# Ciudades de referencia para dar contexto geográfico al mapa
# Nota: la nubosidad dejó de usar el tile OWM clouds_new (baja resolución, color fijo).
# Ahora se dibuja como área de colores interpolada de Open-Meteo (ver _cloud_grid).


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
    cc1, cc2 = st.columns(2)
    ver_nubes = cc1.checkbox("Nubosidad (área)", value=True,
                             key=f"chk_nubes_{parque_activo or 'all'}")
    ver_viento = cc2.checkbox("Dirección del viento", value=True,
                              key=f"chk_viento_{parque_activo or 'all'}")

    # ── Nubosidad como ÁREA de colores (Open-Meteo, grilla interpolada) ──
    if ver_nubes:
        delta = 0.35 if (parque_activo and parque_activo in COORDENADAS) else 1.8
        n = 9
        grid = _cloud_grid(center[0], center[1], delta, n)
        if grid:
            fg = folium.FeatureGroup(name="Nubosidad", show=True)
            paso = (2 * delta) / (n - 1)
            for la, lo, cc in grid:
                # opacidad sube con la nubosidad (cielo despejado casi transparente)
                op = 0.10 + 0.55 * (max(0.0, min(100.0, cc)) / 100.0)
                folium.Rectangle(
                    bounds=[[la - paso / 2, lo - paso / 2], [la + paso / 2, lo + paso / 2]],
                    color=None, weight=0, fill=True,
                    fill_color=_cloud_color(cc), fill_opacity=op,
                    tooltip=f"Nubosidad {cc:.0f}%",
                ).add_to(fg)
            fg.add_to(m)

    # Sombra día/noche en tiempo real
    Terminator().add_to(m)

    # ── Dirección del viento: flecha por parque (apunta a donde sopla) ──
    if ver_viento:
        viento = _meteo_viento_por_parque()
        fgv = folium.FeatureGroup(name="Viento", show=True)
        for _, r in df.iterrows():
            w = viento.get(r["parque"])
            if not w or w.get("dir") is None:
                continue
            vel = w.get("vel")
            # dir meteorológico = de dónde viene → la flecha apunta hacia donde va (+180)
            rot = (w["dir"] + 180) % 360
            col = "#EF4444" if (vel or 0) >= 12 else ("#F59E0B" if (vel or 0) >= 7 else "#4DC8DC")
            vtxt = f"{vel:.1f} m/s" if vel is not None else "s/d"
            html = (f"<div style='transform:rotate({rot}deg);font-size:22px;line-height:22px;"
                    f"color:{col};text-shadow:0 0 3px #000'>&#8593;</div>")
            folium.Marker(
                location=[r["lat"], r["lon"]],
                icon=folium.DivIcon(html=html, icon_size=(24, 24), icon_anchor=(12, 12)),
                tooltip=f"{r['nombre']} — viento {vtxt} desde {w['dir']:.0f}°",
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
        "Nubosidad: área interpolada de % de cobertura (Open-Meteo, actual) — azul=despejado, "
        "gris=cubierto · Flechas = dirección a la que sopla el viento (color por velocidad) · "
        "Imagen satelital: composición estática Esri World Imagery (sin fecha por tile)."
    )


def render_mapa(
    gen_por_parque: dict[str, float | None],
    parque_activo: str | None = None,
    estilo: str = "Claro",
) -> None:
    df = _df(gen_por_parque)
    es_satelite = estilo == "Satelite"

    # Auto-refresco del mapa cada 5 min: refresca nubosidad/viento/día-noche sin que
    # el usuario tenga que recargar la página ni cambiar de sección. Combinado con el
    # TTL de 5 min de _cloud_grid/_meteo_viento_por_parque, trae datos nuevos.
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=300_000, key="mapa_autorefresh")
    except Exception:
        pass

    # Satélite → folium (ESRI token-free + nubes OWM en vivo + día/noche; pydeck no puede).
    if es_satelite:
        try:
            _render_satelite_folium(df, parque_activo)
            return
        except Exception as e:
            st.info(f"No se pudo cargar el mapa satelital ({e}). Mostrando mapa Detallado.")
            estilo = "Detallado"
            es_satelite = False
    # Llegados aquí el estilo es Claro/Detallado (el satélite se fue por folium arriba).
    map_style = MAP_STYLES.get(estilo, MAP_STYLES["Claro"])
    map_provider = "carto"
    txt_color = [26, 31, 54, 230]
    ciudad_color = [107, 114, 128, 200]
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
        get_radius="halo_px",
        radius_units="pixels",
        get_fill_color=["r", "g", "b", 40],
        stroked=False,
        pickable=False,
    )

    circles = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_radius="radio_px",
        radius_units="pixels",
        radius_min_pixels=5,
        radius_max_pixels=14,
        get_fill_color=["r", "g", "b", "alpha"],
        get_line_color=[255, 255, 255] if es_satelite else ["r", "g", "b"],
        stroked=True,
        line_width_min_pixels=1.5,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 120],
    )

    labels = pdk.Layer(
        "TextLayer",
        data=df,
        get_position=["lon", "lat"],
        get_text="nombre",
        get_size=10,
        size_units="pixels",
        get_color=txt_color,
        get_alignment_baseline="'bottom'",
        get_text_anchor="'start'",
        get_pixel_offset=["off_x", "off_y"],
        background=True,
        get_background_color=[0, 0, 0, 140] if es_satelite else [255, 255, 255, 180],
        background_padding=[3, 1, 3, 1],
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
