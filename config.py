from zoneinfo import ZoneInfo

# ── Versión de la app ──────────────────────────────────────────────────────────
# major 2 = era Pulsar (rebrand + BESS + ML + NASA); minor sube con cada hito de datos.
# 2.7.0 — Sesión 27: programación PID + demanda por zona + glosario.
APP_VERSION = "v2.7.0"

# ── Timezone ───────────────────────────────────────────────────────────────────
TZ_CHILE = ZoneInfo("America/Santiago")

# ── APIs CEN ──────────────────────────────────────────────────────────────────
API_BASE_SIP = "https://sipub.api.coordinador.cl"
API_BASE_OPS = "https://operacion.api.coordinador.cl"
CMG_S3_URL   = "https://cen-template-graph-pweb-prod.s3.us-east-1.amazonaws.com/CMG-online/costo-marginal-online.json"

# ── Ventanas de adquisición ────────────────────────────────────────────────────
DIAS_VENTANA     = 5    # gen. real, meteo, SSCC
DIAS_VENTANA_PCP = 1    # gen. programada PCP + CMG programado (paginan TODO el sistema → ventana corta para no exceder el timeout del cron)
DIAS_VENTANA_PID = 1    # gen. programada PID + demanda PID (reprograma intra-día; paginan todo el sistema → ventana corta)
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

# ── Demanda programada PID por zona del SEN ───────────────────────────────────
# El endpoint demanda-programada-pid/v4 entrega la demanda proyectada (MW) por hora
# y por punto de consumo, con campo `zona`. Se agrega por zona del SEN. Se excluyen
# 'Argentina' (exportación) y registros sin zona. El total agregado es indicativo de
# la FORMA del consumo (perfil día/noche) más que un valor absoluto exacto, pues el
# endpoint suma múltiples puntos/barras de cada zona.
DEMANDA_ZONAS = ["Norte", "Centro", "Centro Sur", "Sur"]
DEMANDA_ZONAS_EXCLUIR = {"Argentina", None, ""}

# Color por zona (paleta AES) para series de tiempo de demanda
DEMANDA_ZONA_COLOR = {
    "Norte":      "#F59E0B",   # ámbar — zona de los parques solares
    "Centro":     "#3B4CE8",   # azul AES
    "Centro Sur": "#4DC8DC",   # cyan — zona de los parques eólicos
    "Sur":        "#9B6FD4",   # violeta
}

# Zona del SEN donde está cada parque (para contextualizar demanda local)
ZONA_PARQUE = {
    "AS1":  "Norte", "AS2A": "Norte", "AS2B": "Norte",
    "AS3":  "Norte", "AS4":  "Norte", "BOL":  "Norte",
    "CUR":  "Norte",                                      # Coquimbo → zona Norte CEN
    "CL":   "Centro Sur", "OLM": "Centro Sur",
    "STM":  "Centro Sur", "MSM": "Centro Sur",
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

# ── Potencia máxima NETA CEN (MW) — para factor de planta y comparación con PCP ──
# Fuente: parametros_pe_pulsar / parametros_pfv_pulsar (cartas CEN), 2026-06-22.
# Prioridad recomendada por AES: Pmax neta CEN aceptada > potencia neta verificada
# SSCC > potencia total instalada documentada. None = sin carta CEN → se usa PMAX.
PMAX_NETA = {
    # Solares FV — pmax_neta_pfv_mw
    "AS1":  21.425,
    "AS2A": 86.32,
    "AS2B": 129.7287,
    "AS3":  153.226,
    "AS4":  129.7222,
    "BOL":  None,        # sin carta CEN cargada → se usa PMAX (161.3)
    # Eólicos — pmax_neta_cen_mw
    "CL":   62.945,
    "OLM":  109.13,
    "CUR":  107.7,
    "STM":  79.43,
    "MSM":  None,        # sin Pmax neta CEN → se usa potencia instalada 67.2 MW
}

# Pmax recomendada para FACTOR DE PLANTA: neta CEN si existe, si no la configurada.
# Caso especial MSM: potencia total instalada documentada = 67.2 MW (no la config 70.56).
PMAX_FP = {
    p: (PMAX_NETA[p] if PMAX_NETA.get(p) is not None else PMAX[p])
    for p in PARQUES_TODOS
}
PMAX_FP["MSM"] = 67.2

PMAX_FP_TOTAL_SOLAR  = sum(PMAX_FP[k] for k in PARQUES_SOLAR)
PMAX_FP_TOTAL_EOLICA = sum(PMAX_FP[k] for k in PARQUES_EOLICA)
PMAX_FP_TOTAL        = sum(PMAX_FP.values())

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

# CMG programado PCP — llave_cmg de la API /cmg-programado-pcp/v4 → nodo del proyecto.
# Se mapea a los MISMOS nombres de nodo del feed S3 (CMG_NODOS_TODOS) para que el
# CMG futuro slotee con el histórico online sin tocar el resto del dashboard.
# Llaves confirmadas contra la API (2026-06-23) — solo barras 220 kV relevantes.
CMG_PROG_LLAVE_A_NODO = {
    "Crucero220":     "CRUCERO_______220",
    "Atacama220_BP1": "ATACAMA_______220",
    "Tarapaca220":    "TARAPACA______220",
    "Cardones220":    "CARDONES______220",
    "PAzucar220":     "P.AZUCAR______220",
    "Quillota220":    "QUILLOTA______220",
    "Charrua220":     "CHARRUA_______220",
    "PMontt220":      "P.MONTT_______220",
}

# CMG online 8 barras — nombre de barra de /costos-marginales-online-8b/v4 → nodo.
# Fuente API alternativa/respaldo del feed S3 (mismos 8 nodos).
CMG_8B_NOMBRE_A_NODO = {
    "Crucero 220 KV":   "CRUCERO_______220",
    "Atacama 220 KV":   "ATACAMA_______220",
    "Tarapaca 220 KV":  "TARAPACA______220",
    "Cardones 220 KV":  "CARDONES______220",
    "P.Azucar 220 KV":  "P.AZUCAR______220",
    "Quillota 220 KV":  "QUILLOTA______220",
    "Charrua 220 KV":   "CHARRUA_______220",
    "P.Montt 220 KV":   "P.MONTT_______220",
}

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
    "windspeed_10m",                # m/s — para cálculo Tc y protección de trackers
    "windgusts_10m",                # m/s — ráfagas; gatillan stow de trackers
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
PANEL_TILT_DEG = 20.0    # ° — inclinación de referencia (GTI fijo de Open-Meteo)
PANEL_AZIMUTH  = 0.0     # ° — 0=norte verdadero (hemisferio sur)

# ── Trackers solares (todos los parques FV de AES) ─────────────────────────────
# Los parques FV usan seguidores de 1 eje (N-S, rotación E-O). El POA con tracking
# es mayor que el de tilt fijo. Modelo pragmático: POA_track = GTI_fijo × TRACKER_GAIN,
# acotado a [GHI, ~1100]. Un derate de disponibilidad cubre la confiabilidad del 80%.
TRACKER_GAIN          = 1.18   # ganancia media POA tracking 1-eje vs tilt fijo (~+18%)
TRACKER_AVAIL         = 0.80   # confiabilidad/disponibilidad de los trackers (80%)
TRACKER_STOW_WIND_MS  = 16.0   # [m/s] sobre esto los trackers se ponen horizontales (stow)
TRACKER_POA_MAX       = 1100.0 # [W/m²] tope físico plausible del POA con tracking

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

# ── Curva de potencia por parque eólico (cartas CEN / fichas fabricante) ─────────
# Cuando un parque tiene cut-in/rated/cut-out específicos se usan en el modelo
# físico; si faltan se cae al default Pulsar (3/12/25 m/s). Fuente: Modelo_Eolico
# de parametros_pe_pulsar (2026-06-22).
TURBINA_PARQUE = {
    "CL":  {"v_cutin": 3.0, "v_rated": 12.0, "v_cutout": 24.5,
            "fabricante": "Vestas", "modelo": "V150-4.3 MW Mk3E", "n_wtg": 15,
            "p_unit_mw": 4.3, "rotor_m": 150, "hub_m": 140},
    "CUR": {"v_cutin": 3.0, "v_rated": 12.0, "v_cutout": 25.0,
            "fabricante": "Vestas", "modelo": "V100-1.8 MW (ref. curva PQ)", "n_wtg": None,
            "p_unit_mw": 1.8, "rotor_m": 100, "hub_m": None},
    "OLM": {"v_cutin": 3.0, "v_rated": 12.0, "v_cutout": 25.0,
            "fabricante": None, "modelo": None, "n_wtg": None,
            "p_unit_mw": None, "rotor_m": None, "hub_m": None},
    "STM": {"v_cutin": 3.0, "v_rated": 12.0, "v_cutout": 25.0,
            "fabricante": None, "modelo": None, "n_wtg": None,
            "p_unit_mw": None, "rotor_m": None, "hub_m": None},
    "MSM": {"v_cutin": 3.0, "v_rated": 12.0, "v_cutout": 25.0,
            "fabricante": "Nordex", "modelo": "N149-4.8 MW", "n_wtg": 14,
            "p_unit_mw": 4.8, "rotor_m": 149, "hub_m": 145},
}

# ── Duración (horas) y energía declarada de cada BESS ────────────────────────────
# bess_horas de parametros_pfv (cuando existe). Para SoC/ciclos exactos se requiere
# la energía real (MWh) — la API CEN no la publica; se asume 4 h donde falte.
BESS_HORAS = {
    "AS2A_B": None,
    "AS2B_B": 4.9478,   # PFV+BESS, ~560 MWh declarados (EE-EN-2023-0733)
    "AS3_B":  3.0,      # 171.3 MW × 3 h ≈ 514 MWh (Fluence + CATL)
    "AS4_B":  5.0,
    "BOL_B":  None,
}

# ── INFOTÉCNICA: ficha consolidada por parque (para la pestaña de referencia) ─────
# Resume parametros_pe_pulsar + parametros_pfv_pulsar (cartas CEN, 2026-06-22).
# Pensado para lectura humana en el dashboard, no para cálculo.
INFOTECNICA = {
    # ── Solares FV ──────────────────────────────────────────────────────────────
    "AS1": {
        "pmax_bruta_mw": 21.795, "pmax_neta_mw": 21.425, "pmin_neta_mw": 0.27,
        "sscc": "CSF+ / CSF-", "equipos": "Módulo ET-Solar 300 W policrist.; 15 inversores "
        "Power Electronics FS-1500CH; seguidores 1 eje N-S (backtracking); trafos Ormazabal 1700 kVA",
        "nota": "Para FP/PCP usar Pmax neta 21.425 MW; mínimo operativo 0.27 MW.",
        "fuente": "DE 01906-26; DE06208-21",
    },
    "AS2A": {
        "pmax_bruta_mw": 86.75, "pmax_neta_mw": 86.32, "pmin_neta_mw": 0.0,
        "sscc": "No documentado", "equipos": "BESS/SAE asociado en API (no consolidado)",
        "nota": "Pmax neta 86.32 MW para FP neto; mínimo neto aceptado 0 MW.",
        "fuente": "DE01507-22; DE01443-21",
    },
    "AS2B": {
        "pmax_bruta_mw": 135.8345, "pmax_neta_mw": 129.7287, "pmin_neta_mw": 2.34,
        "sscc": "No consolidado", "equipos": "23 centros transf. (trafo 5.4 MVA + 2 inv. GPTech "
        "2.65 MVA); 46 inversores 121.9 MVA AC; BESS 560 MWh; FV DC 180 MWp; 3 STATCOM GPTech",
        "nota": "Operación FV pura: Pmax neta 129.73 MW. El config dashboard (220 MW) es "
        "capacidad de proyecto/API, no el valor neto CEN vigente.",
        "fuente": "DE06717-24; DE06719-24; EE-EN-2023-0733",
    },
    "AS3": {
        "pmax_bruta_mw": 158.9339, "pmax_neta_mw": 153.226, "pmin_neta_mw": 0.8921,
        "sscc": "CPF+/CPF-, CSF+/CSF-, CTF+/CTF-",
        "equipos": "Módulo JA Solar 175.95 MWp; BESS Fluence+CATL 171.3 MW × 3 h (acople DC); "
        "trackers Soltec; optimizadores AMPT; 152 inversores GPTech; trafo 220/33/33 kV 300 MVA",
        "nota": "Pmax neta 153.23 MW para FV; modo conjunto/BESS sólo al modelar CRCA.",
        "fuente": "DE03456-26; DE03458-26; DE01263-26; ECR Andes Solar III",
    },
    "AS4": {
        "pmax_bruta_mw": 132.3687, "pmax_neta_mw": 129.7222, "pmin_neta_mw": 2.3535,
        "sscc": "CPF+/CPF-, CTF+/CTF-; CT habilitado",
        "equipos": "PFV+BESS (CRCA) acople DC, modos generación/descarga/carga; comparte "
        "transformador 33/33/220 kV con Andes Solar IIB",
        "nota": "Pmax neta 129.72 MW para FV; revisar el config dashboard (220 MW) contra Pmax neta.",
        "fuente": "DE03566-26; DE03567-26; DE01287-26; DE02265-26",
    },
    "BOL": {
        "pmax_bruta_mw": None, "pmax_neta_mw": None, "pmin_neta_mw": None,
        "sscc": "No documentado", "equipos": "Sólo id/llaves/coordenadas/Pmax de config.",
        "nota": "Falta carta CEN de Pmax/mínimo técnico y P&D. Se mantiene config 161.3 MW.",
        "fuente": "CLAUDE.md",
    },
    # ── Eólicos ─────────────────────────────────────────────────────────────────
    "CL": {
        "pmax_bruta_mw": 65.71, "pmax_neta_mw": 62.945, "pmin_neta_mw": 6.33,
        "sscc": "CPF+, CPF-, CT (habilitado desde 2026-02-26)",
        "equipos": "15× Vestas V150-4.3 MW Mk3E; rotor 150 m; hub 140 m; trafo 33/33/220 kV 240/300 MVA",
        "nota": "FP con Pmax neta 62.945 MW. CPF: estatismo 2-8% (3.64%), banda muerta 25 mHz.",
        "fuente": "DE01261-26; EE-EN-2022-1184-RB; Curva PQ Campo Lindo",
    },
    "CUR": {
        "pmax_bruta_mw": 109.4, "pmax_neta_mw": 107.7, "pmin_neta_mw": None,
        "sscc": "CSF+, CSF- (habilitado desde 2025-08-14)",
        "equipos": "Vestas V100-1.8 MW (referencia curva PQ); CSF ±60 MW, tasa 12 MW/min",
        "nota": "FP con Pmax neta 107.7 MW. Límites CSF son potencias activas netas.",
        "fuente": "DE04966-25; DE06205-21; Diagrama PQ Los Cururos",
    },
    "OLM": {
        "pmax_bruta_mw": 111.95, "pmax_neta_mw": 109.13, "pmin_neta_mw": 10.01,
        "sscc": "CT, CPF+, CPF- (CT desde 2026-03-26; CPF desde 2026-06-04)",
        "equipos": "Curva Q por tensión (DE01904-26 CT)",
        "nota": "FP con Pmax neta 109.13 MW. CT informa mínimo puntual 0.493/0.263 MW; "
        "CPF usa mínimo sin pausa de WTG 10.82/10.01 MW.",
        "fuente": "DE01904-26; DE03631-26",
    },
    "STM": {
        "pmax_bruta_mw": 83.208, "pmax_neta_mw": 79.43, "pmin_neta_mw": 7.995,
        "sscc": "CPF+, CPF- (aportes actualizados desde 2026-03-05)",
        "equipos": "Curva PQ San Matías; parámetros operacionales en aprobación",
        "nota": "FP con Pmax neta 79.43 MW. Estatismo 2-8% (3.64%), banda muerta 25-200 mHz.",
        "fuente": "DE01407-26; Curva PQ San Matías",
    },
    "MSM": {
        "pmax_bruta_mw": None, "pmax_neta_mw": None, "pmin_neta_mw": None,
        "sscc": "—",
        "equipos": "14× Nordex N149-4.8 MW; rotor 149 m; hub 145 m; P50 ~233965 MWh/año; FC P50 39.7%",
        "nota": "Sin Pmax neta CEN: usar potencia total instalada 67.2 MW para FP. "
        "WSM: MV_T02 (66-118° y 247-293°) y MV_T10 (177-198°, ajuste 4.5 MW); impacto total 0.2%.",
        "fuente": "R20-34-02 Mesamávida; DE05549-22; Nordex reactive capability",
    },
}
