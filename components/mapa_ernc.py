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
    # Open-Meteo devuelve los objetos EN EL MISMO ORDEN que las coords de entrada
    # (pares = lats×lons, row-major). Se conserva el índice → no depende de que las
    # coordenadas devueltas (redondeadas por Open-Meteo) coincidan exactamente.
    objs = data if isinstance(data, list) else [data]
    out = []
    for idx, (la, lo) in enumerate(pares):
        cc = None
        if idx < len(objs):
            cc = objs[idx].get("current", {}).get("cloud_cover")
        out.append((la, lo, float(cc) if cc is not None else None))
    return out


def _cloud_image(grid: list[tuple], lat0: float, lon0: float, delta: float, n: int):
    """Convierte la grilla n×n de nubosidad en una imagen RGBA suavizada (PNG base64)
    para overlay continuo (sin cuadrados). Retorna (data_uri, bounds) o (None, None)."""
    if not grid or len(grid) < n * n:
        return None, None
    import numpy as np, io, base64
    from PIL import Image
    # grid viene row-major sobre lats×lons (lat ascendente i, lon ascendente j)
    vals = np.array([cc if cc is not None else np.nan for _, _, cc in grid], dtype=float)
    z = vals.reshape((n, n))
    media = np.nanmean(z) if np.isfinite(z).any() else 0.0
    z = np.nan_to_num(z, nan=media)
    p = np.clip(z, 0, 100) / 100.0
    # color despejado (azul claro) → cubierto (gris-blanco)
    r = (127 + (232 - 127) * p).astype(np.uint8)
    g = (178 + (236 - 178) * p).astype(np.uint8)
    b = (255 + (242 - 255) * p).astype(np.uint8)
    a = (np.clip(0.12 + 0.62 * p, 0, 1) * 255).astype(np.uint8)
    rgba = np.dstack([r, g, b, a])
    rgba = np.flipud(rgba)  # fila 0 = norte (lat máx) para ImageOverlay
    img = Image.fromarray(rgba, "RGBA").resize((360, 360), Image.BILINEAR)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    bounds = [[lat0 - delta, lon0 - delta], [lat0 + delta, lon0 + delta]]
    return uri, bounds


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

    # ── Nubosidad como ÁREA suave (imagen interpolada, sin cuadrados) ──
    if ver_nubes:
        delta = 0.35 if (parque_activo and parque_activo in COORDENADAS) else 1.8
        n = 12
        grid = _cloud_grid(center[0], center[1], delta, n)
        uri, bounds = _cloud_image(grid, center[0], center[1], delta, n)
        if uri:
            folium.raster_layers.ImageOverlay(
                image=uri, bounds=bounds, opacity=0.85, name="Nubosidad", interactive=False,
            ).add_to(m)

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
    # TTL de 5 min de _cloud_grid/_viento_actual_parques, trae datos nuevos.
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
