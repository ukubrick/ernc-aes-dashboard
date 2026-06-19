-- ============================================================
-- Dashboard ERNC AES Andes — Esquema Supabase
-- Proyecto: ernc-aes
-- Ejecutar en el SQL Editor de Supabase una vez al crear el proyecto
-- ============================================================

-- ── Generación real ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS generacion_real_ernc (
    id              SERIAL PRIMARY KEY,
    parque          TEXT NOT NULL,        -- código interno: AS1, AS2A, AS2B, AS3, AS4, BOL, CL, OLM, CUR, STM, MSM
    id_central      INTEGER,
    llave_opreal    TEXT,
    central         TEXT,
    gen_real_mw     NUMERIC,
    potencia_max    NUMERIC,
    factor_ernc     NUMERIC,
    valor_ernc      NUMERIC,
    tipo_tecnologia TEXT,
    fecha_hora      TEXT NOT NULL,        -- 'YYYY-MM-DD HH:MM:SS' hora 0-based America/Santiago
    hora            INTEGER,              -- 0-23
    UNIQUE (parque, fecha_hora)
);
CREATE INDEX IF NOT EXISTS idx_gen_real_parque_fecha
    ON generacion_real_ernc (parque, fecha_hora DESC);
CREATE INDEX IF NOT EXISTS idx_gen_real_fecha
    ON generacion_real_ernc (fecha_hora DESC);

-- ── Generación programada PCP ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS generacion_programada_ernc (
    id                      SERIAL PRIMARY KEY,
    parque                  TEXT NOT NULL,
    llave_gen               TEXT,
    gen_programada_mw       NUMERIC,
    capacidad_disponible_mw NUMERIC,
    costo_generacion_usd    NUMERIC,
    fecha_hora              TEXT NOT NULL,
    hora                    INTEGER,
    fecha_programa          TEXT,
    fuente                  TEXT DEFAULT 'CEN_PCP',
    UNIQUE (parque, fecha_hora, fuente)
);
CREATE INDEX IF NOT EXISTS idx_gen_prog_parque_fecha
    ON generacion_programada_ernc (parque, fecha_hora DESC);

-- ── Meteorología Open-Meteo ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS meteo_ernc (
    id                      SERIAL PRIMARY KEY,
    parque                  TEXT NOT NULL,
    fecha_hora              TEXT NOT NULL,
    -- Solar
    ghi_wm2                 NUMERIC,       -- Global Horizontal Irradiance (W/m²)
    dni_wm2                 NUMERIC,       -- Direct Normal Irradiance (W/m²)
    dhi_wm2                 NUMERIC,       -- Diffuse Horizontal Irradiance (W/m²)
    gti_wm2                 NUMERIC,       -- Global Tilted Irradiance con tilt del panel
    -- Calculados solar
    temp_celda_c            NUMERIC,       -- Temperatura de celda FV (°C)
    p_fv_estimada_mw        NUMERIC,       -- Potencia FV estimada por modelo
    eficiencia_ratio        NUMERIC,       -- gen_real / p_fv_estimada (solo cuando hay gen_real)
    cloudcover_low_pct      NUMERIC,       -- Nubosidad baja % (detección camanchaca)
    -- Eólico
    wind_speed_10m          NUMERIC,       -- m/s
    wind_speed_80m          NUMERIC,       -- m/s
    wind_speed_100m         NUMERIC,       -- m/s interpolado 80m+120m
    wind_speed_120m         NUMERIC,       -- m/s
    wind_dir_80m            NUMERIC,       -- ° dirección a hub
    wind_gusts_10m          NUMERIC,       -- m/s ráfagas máximas
    wind_shear_alpha        NUMERIC,       -- exponente ley de potencia calculado
    -- Calculados eólico
    densidad_aire           NUMERIC,       -- kg/m³ calculado desde T y P
    p_eolica_estimada_mw    NUMERIC,       -- Potencia eólica estimada por modelo
    boundary_layer_height   NUMERIC,       -- m altura capa límite (estabilidad atm.)
    -- Generales
    temp_2m                 NUMERIC,       -- °C
    humidity_2m             NUMERIC,       -- %
    cloud_cover_pct         NUMERIC,       -- % nubosidad total
    surface_pressure        NUMERIC,       -- hPa
    is_day                  BOOLEAN,       -- TRUE = hora diurna
    -- Metadatos
    fuente                  TEXT DEFAULT 'open-meteo',
    es_forecast             BOOLEAN DEFAULT FALSE,   -- TRUE = dato futuro del forecast
    UNIQUE (parque, fecha_hora, fuente)
);
CREATE INDEX IF NOT EXISTS idx_meteo_parque_fecha
    ON meteo_ernc (parque, fecha_hora DESC);
CREATE INDEX IF NOT EXISTS idx_meteo_forecast
    ON meteo_ernc (es_forecast, fecha_hora)
    WHERE es_forecast = TRUE;

-- ── CMG histórico ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cmg_ernc (
    id          SERIAL PRIMARY KEY,
    nodo        TEXT NOT NULL,
    cmg_usd_mwh NUMERIC,
    fecha_hora  TEXT NOT NULL,
    UNIQUE (nodo, fecha_hora)
);
CREATE INDEX IF NOT EXISTS idx_cmg_nodo_fecha
    ON cmg_ernc (nodo, fecha_hora DESC);

-- ── Limitaciones de transmisión ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS limitaciones_ernc (
    id                       TEXT PRIMARY KEY,    -- ID hex de la API CEN
    correlativo              INTEGER,
    parque                   TEXT,
    empresa_nombre           TEXT,
    instalacion_nombre       TEXT,
    status                   TEXT,
    fecha_perturbacion       TEXT,
    fecha_retorno_estimada   TEXT,
    fecha_efectiva_retorno   TEXT,
    potencia                 NUMERIC,
    unidad_medida_potencia   TEXT,
    produce_indisponibilidad BOOLEAN,
    afecta_sscc              BOOLEAN,
    observacion              TEXT,
    created                  TEXT,
    modified                 TEXT
);
CREATE INDEX IF NOT EXISTS idx_lim_parque
    ON limitaciones_ernc (parque, fecha_perturbacion DESC);

-- ── SSCC instrucciones ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sscc_ernc (
    id               SERIAL PRIMARY KEY,
    parque           TEXT,
    fecha            TEXT,
    inicio_periodo   TEXT,
    fin_periodo      TEXT,
    instruccion_sscc TEXT,
    id_configuracion INTEGER,
    central_unidad   TEXT,
    disponibilidad   NUMERIC,
    baja             NUMERIC,
    sube             NUMERIC,
    unidad_medida    TEXT,
    UNIQUE (fecha, id_configuracion, instruccion_sscc, inicio_periodo)
);
CREATE INDEX IF NOT EXISTS idx_sscc_parque_fecha
    ON sscc_ernc (parque, fecha DESC);

-- ── Vista útil: última hora por parque (para KPIs del dashboard) ──────────────
CREATE OR REPLACE VIEW ultima_gen_por_parque AS
SELECT DISTINCT ON (parque)
    parque,
    gen_real_mw,
    potencia_max,
    factor_ernc,
    fecha_hora,
    hora
FROM generacion_real_ernc
ORDER BY parque, fecha_hora DESC;

-- ── Vista: gen real + programada combinadas ───────────────────────────────────
CREATE OR REPLACE VIEW gen_real_vs_prog AS
SELECT
    r.parque,
    r.fecha_hora,
    r.hora,
    r.gen_real_mw,
    r.potencia_max,
    p.gen_programada_mw,
    p.capacidad_disponible_mw,
    CASE
        WHEN p.gen_programada_mw > 0
        THEN ROUND(((r.gen_real_mw - p.gen_programada_mw) / p.gen_programada_mw * 100)::NUMERIC, 2)
        ELSE NULL
    END AS desvio_pct
FROM generacion_real_ernc r
LEFT JOIN LATERAL (
    SELECT gen_programada_mw, capacidad_disponible_mw
    FROM generacion_programada_ernc
    WHERE parque = r.parque AND fecha_hora = r.fecha_hora
    ORDER BY fuente DESC
    LIMIT 1
) p ON TRUE;
