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

# Todos los nodos CMG que se guardan en DB (se persisten aunque no estén mapeados a parque)
CMG_NODOS_TODOS = [
    "CRUCERO_______220",   # norte, parques solares
    "CHARRUA_______220",   # sur, parques eólicos (probable)
    "QUILLOTA_____220",
    "PAN_DE_AZUCAR_220",
    "CARDONES_____220",
    "NOGALES______220",
    "ANCOA________220",
    "POLPAICO_____220",
]

# ── SSCC: centralUnidad API → código interno ───────────────────────────────────
LLAVES_SSCC = {
    "PE-SANMATIAS": "STM",
}

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
TURBINA_CP      = 0.45    # Coef. de potencia (Betz ~0.593, real ~0.40-0.48)
TURBINA_V_RATED = 12.0    # Velocidad nominal típica [m/s] — velocidad a la que se alcanza Pmax
AIRE_R          = 287.05  # J/(kg·K) — constante gas ideal aire seco
