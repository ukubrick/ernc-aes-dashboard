from zoneinfo import ZoneInfo

# ── Timezone ───────────────────────────────────────────────────────────────────
TZ_CHILE = ZoneInfo("America/Santiago")

# ── APIs CEN ──────────────────────────────────────────────────────────────────
API_BASE_SIP = "https://sipub.api.coordinador.cl"
API_BASE_OPS = "https://operacion.api.coordinador.cl"
CMG_S3_URL   = "https://cen-template-graph-pweb-prod.s3.us-east-1.amazonaws.com/CMG-online/costo-marginal-online.json"

# ── Ventanas de adquisición ────────────────────────────────────────────────────
DIAS_VENTANA     = 5    # gen. real, programada, meteo, SSCC
DIAS_VENTANA_LIM = 30   # limitaciones de transmisión

# ── IDs CEN por parque ─────────────────────────────────────────────────────────
ID_CENTRAL = {
    "AS1":  374,
    "AS2A": 643,
    "AS2B": 1850,
    "AS3":  2322,
    "AS4":  2076,
    "BOL":  456,
    "CL":   1845,
    "OLM":  1757,
    "CUR":  318,
    "STM":  2091,
    "MSM":  1758,
}

# ── Nombres display ────────────────────────────────────────────────────────────
NOMBRE_DISPLAY = {
    "AS1":  "Andes Solar I",
    "AS2A": "Andes Solar 2A",
    "AS2B": "Andes Solar 2B",
    "AS3":  "Andes Solar III",
    "AS4":  "Andes Solar IV",
    "BOL":  "PFV Bolero",
    "CL":   "PE Campo Lindo",
    "OLM":  "PE Los Olmos",
    "CUR":  "PE Los Cururos",
    "STM":  "PE San Matías",
    "MSM":  "PE Mesamavida",
}

# ── Llaves generación real CEN ────────────────────────────────────────────────
LLAVES_OPREAL = {
    "AS1":  "PFV ANDES SOLAR",
    "AS2A": "PFV ANDES SOLAR IIA",
    "AS2B": "PFV ANDES SOLAR IIB",
    "AS3":  "PFV Andes Solar III",
    "AS4":  "PFV ANDES SOLAR IV",
    "BOL":  "PFV BOLERO",
    "CL":   "PE CAMPO LINDO",
    "OLM":  "PE LOS OLMOS",
    "CUR":  "PE LOS CURUROS",
    "STM":  "PE SAN MATIAS",
    "MSM":  "PE MESAMÁVIDA",
}

# ── Llaves generación programada PCP ──────────────────────────────────────────
LLAVES_GEN_PROG = {
    "AS1":  ["ANDES_FV"],
    "AS2A": ["ANDES_2A_FV"],
    "AS2B": ["ANDES_2B_FV"],
    "AS3":  ["ANDES_3_FV"],
    "AS4":  ["ANDES_4_FV"],
    "BOL":  ["BOLERO_1_FV"],
    "CL":   ["CAMPO_LINDO_EO"],
    "OLM":  ["LOS_OLMOS_EO"],
    "CUR":  ["LOS_CURUROS_EO"],
    "STM":  ["SAN_MATIAS_EO"],
    "MSM":  ["MESAMAVIDA_EO"],
}

# ── Tecnología por parque ──────────────────────────────────────────────────────
TECNOLOGIA = {
    "AS1":  "Solar", "AS2A": "Solar", "AS2B": "Solar",
    "AS3":  "Solar", "AS4":  "Solar", "BOL":  "Solar",
    "CL":   "Eólica", "OLM": "Eólica", "CUR": "Eólica",
    "STM":  "Eólica", "MSM": "Eólica",
}

PARQUES_SOLAR  = [k for k, v in TECNOLOGIA.items() if v == "Solar"]
PARQUES_EOLICA = [k for k, v in TECNOLOGIA.items() if v == "Eólica"]
PARQUES_TODOS  = list(ID_CENTRAL.keys())

# ── Potencias máximas (MW) ────────────────────────────────────────────────────
PMAX = {
    "AS1":  23.97,
    "AS2A": 91.09,
    "AS2B": 220.0,
    "AS3":  175.0,
    "AS4":  220.0,
    "BOL":  161.3,
    "CL":   76.8,
    "OLM":  115.92,
    "CUR":  115.08,
    "STM":  87.5,
    "MSM":  70.56,
}

PMAX_TOTAL_SOLAR  = sum(PMAX[k] for k in PARQUES_SOLAR)
PMAX_TOTAL_EOLICA = sum(PMAX[k] for k in PARQUES_EOLICA)
PMAX_TOTAL        = sum(PMAX.values())

# ── Coordenadas geográficas (aproximadas) ──────────────────────────────────────
COORDENADAS = {
    "AS1":  {"lat": -24.010753, "lon": -68.584921},  # OSM way 745505231
    "AS2A": {"lat": -24.009143, "lon": -68.574685},  # OSM way 1296706746
    "AS2B": {"lat": -24.000723, "lon": -68.575145},  # OSM way 974171190
    "AS3":  {"lat": -24.001486, "lon": -68.565828},  # OSM way 1296706747
    "AS4":  {"lat": -24.021944, "lon": -68.573460},  # OSM way 1144233017
    "BOL":  {"lat": -23.475195, "lon": -69.408486},  # Sierra Gorda, Antofagasta
    "CL":   {"lat": -37.404179, "lon": -72.494720},  # Los Angeles, Bio Bio
    "OLM":  {"lat": -37.649278, "lon": -72.473876},  # Mulchen, Bio Bio
    "CUR":  {"lat": -31.012533, "lon": -71.637465},  # Los Cururos Sur, Coquimbo
    "STM":  {"lat": -37.434120, "lon": -72.552807},  # Los Angeles, Bio Bio
    "MSM":  {"lat": -37.489984, "lon": -72.459097},  # Los Angeles, Bio Bio
}

# ── Colores por tecnología ─────────────────────────────────────────────────────
COLORES = {
    "Solar":  [245, 158, 11],   # Amber RGB — pydeck
    "Eólica": [59, 130, 246],   # Blue RGB  — pydeck
}

COLORES_HEX = {
    "Solar":  "#F59E0B",
    "Eólica": "#3B82F6",
}

# ── CMG: nodo por parque ───────────────────────────────────────────────────────
CMG_NODO = {
    "AS1":  "CRUCERO_______220",
    "AS2A": "CRUCERO_______220",
    "AS2B": "CRUCERO_______220",
    "AS3":  "CRUCERO_______220",
    "AS4":  "CRUCERO_______220",
    "BOL":  "CRUCERO_______220",
    # Eólicos del sur — CHARRUA probable, pendiente confirmar con AES Andes
    "CL":   "CHARRUA_______220",
    "OLM":  "CHARRUA_______220",
    "CUR":  "CHARRUA_______220",
    "STM":  "CHARRUA_______220",
    "MSM":  "CHARRUA_______220",
}

# Todos los nodos CMG que se guardan en DB — nombres EXACTOS del feed S3 del CEN
# (confirmados 2026-06-21: el feed publica estos 8 nodos y no otros).
# OJO: el número de guiones bajos importa, debe calzar carácter a carácter con el JSON.
CMG_NODOS_TODOS = [
    "CRUCERO_______220",   # norte (Antofagasta) — parques solares
    "ATACAMA_______220",   # norte (Atacama) — referencia solar alternativa
    "TARAPACA______220",   # norte extremo
    "CARDONES______220",   # norte-centro (Atacama/Coquimbo)
    "P.AZUCAR______220",   # Pan de Azúcar (Coquimbo) — cercano a Los Cururos
    "QUILLOTA______220",   # centro
    "CHARRUA_______220",   # sur (Biobío) — parques eólicos
    "P.MONTT_______220",   # sur extremo
]

# ── SSCC: centralUnidad API → código interno ───────────────────────────────────
LLAVES_SSCC = {
    "PE-SANMATIAS": "STM",
}

# ── BESS (sistemas de almacenamiento) de AES Andes ─────────────────────────────
# Aparecen en gen-real/v3 como centrales separadas (id_central=None, tipo='BESS')
# con llaves de (Inyección)=descarga y (Retiro)=carga, ambas en magnitud positiva.
# Convención dashboard: potencia_neta = inyeccion - retiro
#   neta > 0 → descargando (entrega al sistema) | neta < 0 → cargando.
# pmax_mw = potencia de descarga (inyección) declarada en la API.
# Llaves confirmadas contra la API CEN el 2026-06-21.
BESS = {
    "AS2A_B": {
        "nombre": "BESS Andes Solar IIA", "parque": "AS2A", "pmax_mw": 84.0,
        "iny": ["BESS ANDES SOLAR IIA (inyección)"],
        "ret": ["BESS ANDES SOLAR IIA (retiro)"],
    },
    "AS2B_B": {
        "nombre": "BESS Andes Solar IIB", "parque": "AS2B", "pmax_mw": 136.5,
        "iny": ["BESS ANDES SOLAR IIB (inyección)"],
        "ret": ["BESS ANDES SOLAR IIB (retiro)"],
    },
    "AS3_B": {
        "nombre": "BESS Andes Solar III", "parque": "AS3", "pmax_mw": 177.0,
        "iny": ["SAE PFV Andes Solar III (Inyección)"],
        "ret": ["SAE PFV Andes Solar III (Retiro de central)",
                "SAE PFV Andes Solar III (Retiro del sistema)"],
    },
    "AS4_B": {
        "nombre": "BESS Andes Solar IV", "parque": "AS4", "pmax_mw": 140.0,
        "iny": ["BESS ANDES SOLAR IV (inyección)"],
        "ret": ["BESS ANDES SOLAR IV (retiro)"],
    },
    "BOL_B": {
        "nombre": "BESS Bolero", "parque": "BOL", "pmax_mw": 160.0,
        "iny": ["SAE PFV Bolero (Inyección)"],
        "ret": ["SAE PFV Bolero (Retiro de central)",
                "SAE PFV Bolero (Retiro del sistema)"],
    },
    "ET1_B": {
        "nombre": "BESS Andes ET1", "parque": "AS1", "pmax_mw": 14.08,
        "iny": ["BESS ANDES ET1 (Inyección)"],
        "ret": ["BESS ANDES ET1 (retiro)"],
    },
}

# Mapa inverso llave_opreal → (codigo_bess, flujo) para clasificar filas en adquisición.
BESS_LLAVE_MAP = {}
for _cod, _b in BESS.items():
    for _ll in _b["iny"]:
        BESS_LLAVE_MAP[_ll] = (_cod, "iny")
    for _ll in _b["ret"]:
        BESS_LLAVE_MAP[_ll] = (_cod, "ret")

# ── Open-Meteo: variables por tecnología ──────────────────────────────────────
OPENMETEO_VARS_SOLAR = [
    "shortwave_radiation",          # GHI (W/m²)
    "direct_normal_irradiance",     # DNI (W/m²)
    "diffuse_radiation",            # DHI (W/m²)
    "global_tilted_irradiance",     # GTI con tilt configurado (W/m²)
    "temperature_2m",               # °C
    "windspeed_10m",                # m/s — para cálculo Tc
    "cloudcover",                   # % nubosidad total
    "cloudcover_low",               # % nubosidad baja (camanchaca)
    "is_day",                       # 1=día, 0=noche
    "surface_pressure",             # hPa
    "relativehumidity_2m",          # %
]

OPENMETEO_VARS_EOLICA = [
    "windspeed_10m",                # m/s — para shear
    "windspeed_80m",                # m/s — interpolar a 100m
    "windspeed_120m",               # m/s — interpolar a 100m
    "winddirection_10m",            # ° — dirección
    "winddirection_80m",            # ° — dirección a hub
    "windgusts_10m",                # m/s — ráfagas máximas
    "temperature_2m",               # °C — para densidad del aire
    "surface_pressure",             # hPa — para densidad del aire
    "relativehumidity_2m",          # %
    "boundary_layer_height",        # m — estabilidad atmósfera
    "cloudcover",                   # %
]

# ── Parámetros FV ──────────────────────────────────────────────────────────────
PANEL_NOCT     = 45.0    # °C — Normal Operating Cell Temperature típico
PANEL_GAMMA    = -0.004  # /°C — coef. temperatura silicio cristalino
PANEL_TILT_DEG = 20.0    # ° — inclinación promedio de paneles
PANEL_AZIMUTH  = 0.0     # ° — 0=norte verdadero (hemisferio sur)

# ── Parámetros eólicos ─────────────────────────────────────────────────────────
# Curva de potencia simplificada de turbina típica onshore (clase IEC II/III):
#   v < cut-in            → 0
#   cut-in ≤ v < rated    → rampa cúbica P = Pmax·((v³-v_in³)/(v_rated³-v_in³))
#   rated ≤ v ≤ cut-out   → Pmax (corregido por densidad)
#   v > cut-out           → 0 (turbina se detiene por seguridad)
TURBINA_CP       = 0.45    # Coef. de potencia (Betz ~0.593, real ~0.40-0.48)
TURBINA_V_CUTIN  = 3.0     # [m/s] velocidad de arranque
TURBINA_V_RATED  = 12.0    # [m/s] velocidad nominal — se alcanza Pmax
TURBINA_V_CUTOUT = 25.0    # [m/s] velocidad de corte — la turbina se detiene
AIRE_R           = 287.05  # J/(kg·K) — constante gas ideal aire seco

# Rango físico plausible del exponente de cizalle (wind shear α). Fuera de esto
# el dato meteorológico es ruido (viento muy bajo) y se descarta.
SHEAR_ALPHA_MIN  = -0.10
SHEAR_ALPHA_MAX  = 0.60
