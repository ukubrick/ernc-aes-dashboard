# CLAUDE.md — Dashboard ERNC AES Andes
> Contexto completo para Claude Code. Leer al inicio de cada sesión.
> Autor: Erick Herrera — AES Andes, Antofagasta, Chile.
> Última actualización: 2026-06-19 (Sesión 7 completada — proyecto completo).

---

## DESCRIPCIÓN DEL PROYECTO

Dashboard operacional para **11 parques de energías renovables (ERNC) de AES Andes** en Chile:
- 6 parques solares FV (norte, Atacama/Antofagasta)
- 5 parques eólicos (sur, Biobío/Coquimbo)

**Proyecto independiente** del dashboard CTM Mejillones (térmicas ANG/CCR). Hereda el stack y patrones de ese proyecto pero con visualización significativamente más rica.

---

## STACK TECNOLÓGICO

```
Frontend:        Streamlit (Python)
Mapa 3D:         pydeck (deck.gl TerrainLayer + ColumnLayer + ScatterplotLayer)
Gráficos:        Plotly (interactivos)
Base de datos:   Supabase (REST API via supabase-py — NO psycopg2 directo)
Adquisición:     Python + GitHub Actions (cron horario, minuto :10)
Meteorología:    Open-Meteo (gratuita, sin key, resolución horaria)
API energía:     CEN (SIPUB + Operaciones)
CMG:             JSON S3 público del Coordinador Eléctrico Nacional
Exportación:     ReportLab (PDF)
Autorefresh:     streamlit-autorefresh (cada 3.600.000 ms)
```

### Por qué supabase-py y NO psycopg2
La conexión TCP directa a Supabase (puerto 5432 y 6543) falla desde redes locales con restricciones de egress (IPv6 / firewall). La REST API de Supabase (HTTPS puerto 443) siempre funciona. Se usa `supabase-py >= 2.0.0`.

---

## CREDENCIALES Y VARIABLES DE ENTORNO

```env
# API CEN
CEN_USER_KEY=<ver .env / GitHub Secrets>    # SIP (pública)
CEN_OPS_KEY=<ver .env / GitHub Secrets>     # Operaciones

# Supabase — proyecto ernc-aes
SUPABASE_URL=https://ozeubcqoxsihmmfpswoa.supabase.co
SUPABASE_KEY=REDACTED_SERVICE_ROLE_KEY   # service_role (escribe sin RLS)
```

> ⚠️ En el frontend (app_ernc.py) usar el `anon key` (`sb_publishable_...`) para lectura, no el secret.
> El `service_role` key solo debe usarse en el script de adquisición (servidor/GitHub Actions).

### GitHub Actions Secrets a configurar
```
CEN_USER_KEY
CEN_OPS_KEY
SUPABASE_URL
SUPABASE_KEY
```

---

## ESTRUCTURA DE ARCHIVOS

```
ernc-aes-dashboard/
├── CLAUDE.md                                 ← este archivo
├── .env                                      ← credenciales locales (gitignored)
├── .env.example                              ← plantilla sin valores reales
├── .gitignore
├── config.py                                 ← TODAS las constantes del proyecto
├── schema.sql                                ← esquema Supabase (ya ejecutado)
├── requirements.txt
├── Adquisicion_ernc.py                       ← script de adquisición CEN
├── Adquisicion_meteo_ernc.py                 ← (Sesión 3) meteorología Open-Meteo
├── app_ernc.py                               ← (Sesión 4) app Streamlit principal
├── utils/
│   ├── __init__.py
│   ├── cen_api.py                            ← wrappers APIs CEN
│   ├── db.py                                 ← cliente Supabase + upserts + queries
│   ├── openmeteo_api.py                      ← (Sesión 3) wrapper Open-Meteo
│   ├── calculos.py                           ← (Sesión 3) fórmulas derivadas
│   └── insights.py                           ← (Sesión 6) motor de alertas automáticas
├── components/
│   ├── __init__.py
│   ├── mapa_ernc.py                          ← (Sesión 4) mapa 3D pydeck
│   ├── kpis_generales.py                     ← (Sesión 4) fila de KPIs
│   ├── tab_solar.py                          ← (Sesión 5) tab Solar FV
│   ├── tab_eolica.py                         ← (Sesión 5) tab Eólica
│   ├── tab_forecast.py                       ← (Sesión 6) forecast 7 días
│   ├── tab_insights.py                       ← (Sesión 6) hallazgos automáticos
│   └── detalle_parque.py                     ← (Sesión 5) vista por parque
├── assets/
│   └── logo_aes.png
└── .github/
    └── workflows/
        └── adquisicion_ernc.yml              ← cron horario :10
```

---

## PARQUES (11 confirmados en API CEN)

### Solares FV

| Código | Nombre Display | id_central | llave_opreal | llave_PCP | P_max (MW) | Lat | Lon |
|--------|---------------|-----------|-------------|----------|-----------|-----|-----|
| AS1 | Andes Solar I | 374 | PFV ANDES SOLAR | ANDES_FV | 23.97 | -24.10 | -69.85 |
| AS2A | Andes Solar 2A | 643 | PFV ANDES SOLAR IIA | ANDES_2A_FV | 91.09 | -24.10 | -69.85 |
| AS2B | Andes Solar 2B | 1850 | PFV ANDES SOLAR IIB | ANDES_2B_FV | 220.0 | -24.10 | -69.85 |
| AS3 | Andes Solar III | 2322 | PFV Andes Solar III | ANDES_3_FV | 175.0 | -24.12 | -69.87 |
| AS4 | Andes Solar IV | 2076 | PFV ANDES SOLAR IV | ANDES_4_FV | 220.0 | -24.08 | -69.83 |
| BOL | PFV Bolero | 456 | PFV BOLERO | BOLERO_1_FV | 161.3 | -26.20 | -69.90 |

### Eólicos

| Código | Nombre Display | id_central | llave_opreal | llave_PCP | P_max (MW) | Lat | Lon |
|--------|---------------|-----------|-------------|----------|-----------|-----|-----|
| CL | PE Campo Lindo | 1845 | PE CAMPO LINDO | CAMPO_LINDO_EO | 76.8 | -37.80 | -72.40 |
| OLM | PE Los Olmos | 1757 | PE LOS OLMOS | LOS_OLMOS_EO | 115.92 | -36.20 | -72.60 |
| CUR | PE Los Cururos | 318 | PE LOS CURUROS | LOS_CURUROS_EO | 115.08 | -30.30 | -71.00 |
| STM | PE San Matías | 2091 | PE SAN MATIAS | SAN_MATIAS_EO | 87.5 | -38.10 | -72.50 |
| MSM | PE Mesamavida | 1758 | PE MESAMÁVIDA | MESAMAVIDA_EO | 70.56 | -37.50 | -72.20 |

**Capacidad total:** ~1.358 MW Solar + ~466 MW Eólica = **~1.824 MW**

> ⚠️ Coordenadas aproximadas. Confirmar con AES Andes antes de producción.

### BESS asociados (en API gen-real, id_central=None — ignorar en v1)
AS2A, AS2B, AS3, AS4, BOL tienen BESS/SAE asociados que aparecen en la API.
Filtrar por `llave_opreal` exacta para excluirlos.

---

## APIS CEN — DETALLES TÉCNICOS CONFIRMADOS

### Autenticación
Parámetro `user_key` en query string. Dos planes:
- **SIP** (`sipub.api.coordinador.cl`): `CEN_USER_KEY`
- **Operaciones** (`operacion.api.coordinador.cl`): `CEN_OPS_KEY`

### Rate Limiting
La API CEN devuelve **429 Too Many Requests** cuando se hacen varias llamadas consecutivas rápidas. El retry exponencial (10s → 20s → 40s) lo maneja correctamente. Es normal ver 1-2 retries por ejecución.

### Generación Real (gen-real/v3) ✅ CONFIRMADO
```
GET https://sipub.api.coordinador.cl/generacion-real/v3/findByDate
    ?startDate=YYYY-MM-DD
    &endDate=YYYY-MM-DD
    &idCentral={id}         ← SÍ filtra en servidor
    &pageSize=5000
    &page=1
    &user_key={CEN_USER_KEY}
```
- Campos clave: `gen_real_mw`, `fecha_hora`, `hora` (1-24), `potencia_maxima`, `llave_opreal`, `factor_ernc`, `valor_ernc`, `tipo_tecnologia`
- **Convención hora:** CEN usa 1-24 → convertir con `hora - 1` para obtener 0-based
- Gen = 0 en horas nocturnas para parques solares — **es normal, NO es error de adquisición**
- La API devuelve también BESS (id_central=None) — filtrar por `llave_opreal` exacta

### Generación Programada PCP (gen-programada-pcp/v4) ✅ CONFIRMADO
```
GET https://sipub.api.coordinador.cl/generacion-programada-pcp/v4/findByDate
    ?startDate=YYYY-MM-DD
    &endDate=YYYY-MM-DD
    &limit=5000
    &page=1
    &user_key={CEN_USER_KEY}
```
- ⚠️ **NO filtra por idCentral** — el parámetro es ignorado por el servidor
- Campo clave de la llave: `llave_gen` (confirmado en v4, NOT `id_unidad_programacion`)
- `fecha_hora` ya viene en formato `YYYY-MM-DD HH:MM:SS` hora 0-based — NO requiere conversión de hora
- Tarda ~12 min si se recorre todo el sistema — en cron horario usar ventana reducida (2 días)
- El lote PCP puede traer duplicados `(parque, fecha_hora, fuente)` → **deduplicar antes del upsert**
- Campos adicionales: `costo_generacion_usd`, `capacidad_disponible_mw`, `fecha_programa`, `barra`

### CMG S3 ✅ CONFIRMADO (estructura real)
```python
# URL: https://cen-template-graph-pweb-prod.s3.us-east-1.amazonaws.com/CMG-online/costo-marginal-online.json
# Headers: {"Referer": "https://www.coordinador.cl/"}
# Estructura REAL (distinta a lo documentado inicialmente):
{
  "maintenance": false,
  "data": [
    {
      "name": "CRUCERO_______220",
      "horas": [
        {"hora": "2026-06-18 23:00", "total": 296.1},
        ...  # últimas ~100 horas, actualiza cada ~15 min
      ]
    },
    ... # 8 nodos en total
  ]
}
```
- Tomar `horas[-1]` para el valor más reciente de cada nodo
- `hora` viene como `"YYYY-MM-DD HH:MM"` (sin segundos) → agregar `:00` al guardar
- Nodo confirmado para parques del norte: `CRUCERO_______220`
- Parques eólicos del sur: nodo CMG **pendiente de confirmar**

### Limitaciones de Transmisión ✅ CONFIRMADO
```
GET https://sipub.api.coordinador.cl/limitaciones-transmision/v4/findByDate
    ?startDate=YYYY-MM-DD   ← 30 días hacia atrás
    &endDate=YYYY-MM-DD
    &limit=100
    &page=1
    &user_key={CEN_USER_KEY}
```
- Filtrar local por `instalacion_nombre` — match parcial contra nombre del parque
- Campo `correlativo` llega como **float** (ej: `2026001401.0`) → castear con `int(float(v))`
- Limitaciones activas confirmadas (junio 2026): PE CAMPO LINDO (64.5 MW pendiente)
- Otras conocidas históricamente: PE MESAMAVIDA, PE LOS OLMOS, PFV BOLERO

### SSCC (Servicios Complementarios) ✅ CONFIRMADO
```
GET https://operacion.api.coordinador.cl/servicios-complementarios/v1
    ?initDate=YYYY-MM-DD
    &endDate=YYYY-MM-DD
    &page=0
    &pageSize=-1
    &user_key={CEN_OPS_KEY}
```
- `-1` trae todos en una llamada
- Paginación: campo `content` (no `data`), campos en **camelCase**
- Solo PE San Matías confirmado con instrucciones (`PE-SANMATIAS`, `CPF(+)`)
- Parques solares generalmente no aparecen en SSCC

---

## BASE DE DATOS SUPABASE

**Proyecto:** `ernc-aes` | **Ref:** `ozeubcqoxsihmmfpswoa`
**API URL:** `https://ozeubcqoxsihmmfpswoa.supabase.co`
**Schema ejecutado:** ✅ (schema.sql aplicado 2026-06-18)

### Tablas
| Tabla | Clave única | Descripción |
|-------|-------------|-------------|
| `generacion_real_ernc` | `(parque, fecha_hora)` | Gen. real horaria por parque |
| `generacion_programada_ernc` | `(parque, fecha_hora, fuente)` | Gen. PCP horaria |
| `meteo_ernc` | `(parque, fecha_hora, fuente)` | Meteorología + calculados |
| `cmg_ernc` | `(nodo, fecha_hora)` | Costo marginal histórico |
| `limitaciones_ernc` | `id` (TEXT hex) | Limitaciones de transmisión |
| `sscc_ernc` | `(fecha, id_configuracion, instruccion_sscc, inicio_periodo)` | SSCC |

### Vistas útiles
- `ultima_gen_por_parque` — último registro de gen_real por parque (para KPIs)
- `gen_real_vs_prog` — join gen_real + programada con desvio_pct calculado

### Convención fecha_hora en DB
Siempre `"YYYY-MM-DD HH:MM:SS"` hora **0-based** en `America/Santiago`.

### RLS (Row Level Security)
- Las tablas tienen RLS habilitado por defecto en Supabase
- Escritura (adquisición): usar `service_role` key → omite RLS
- Lectura (dashboard): usar `anon` key / `publishable` key → solo SELECT

---

## CONVENCIONES DE CÓDIGO

```python
# Hora CEN: convención 1-24 → usar hora - 1 para convertir a 0-based
hora_0based = int(item["hora"]) - 1  # gen-real v3

# PCP v4: fecha_hora ya viene 0-based, NO convertir
fecha_hora = item["fecha_hora"][:19]  # solo truncar a segundos

# fecha_hora en DB: siempre string "YYYY-MM-DD HH:MM:SS"
# Gen = 0 horas nocturnas (solar): is_day=False → NO es error
# BESS: id_central=None → ignorar en v1

# Retry: SIEMPRE usar _get_with_retry() para todas las llamadas CEN
# Rate limit 429: el retry exponencial lo maneja — es normal ver 1-2 retries

# Supabase: usar supabase-py, NO psycopg2
# Conexión TCP directa (5432/6543) falla desde redes locales
```

---

## OPEN-METEO (Sesión 3 — pendiente)

```python
pip install openmeteo-requests requests-cache retry-requests
```

Variables por tecnología definidas en `config.py`:
- **Solar:** `OPENMETEO_VARS_SOLAR` (GHI, DNI, DHI, GTI, temp, viento, nubosidad)
- **Eólica:** `OPENMETEO_VARS_EOLICA` (viento 10/80/120m, dir, ráfagas, presión, BLH)

Para solares: configurar `tilt=20` y `azimuth=0` (norte, hemisferio sur).
Forecast 7 días + 2 días históricos en cada llamada.

---

## CÁLCULOS DERIVADOS (Sesión 3 — pendiente)

Implementar en `utils/calculos.py`:

| Función | Descripción |
|---------|-------------|
| `calcular_temp_celda(t_amb, ghi, wind)` | Temperatura celda FV con modelo NOCT ajustado por viento |
| `calcular_potencia_fv_estimada(gti, tc, pmax)` | P = Ppico × (GTI/1000) × [1 + γ(Tc-25)] |
| `calcular_eficiencia_real(gen_real, p_est)` | Ratio real/modelo — detecta fallas/limitaciones |
| `interpolar_viento_100m(v_80m, v_120m)` | Ley de potencia → v100m y alpha shear |
| `calcular_densidad_aire(temp_c, presion_hpa)` | ρ = P/(R×T) en kg/m³ |
| `calcular_potencia_eolica_estimada(v100m, ρ, pmax)` | P = ½ρAcpv³, cap a pmax |
| `calcular_factor_planta(gen_real, pmax)` | % de capacidad utilizada |
| `calcular_desvio(gen_real, gen_prog)` | MW y % con semáforo verde/amarillo/rojo |
| `calcular_ingreso_estimado(gen_real, cmg)` | USD horario = gen × CMG |

---

## ORDEN DE IMPLEMENTACIÓN POR SESIÓN

| Sesión | Estado | Contenido |
|--------|--------|-----------|
| **1 — Fundación** | ✅ COMPLETA | `config.py`, `utils/db.py`, `utils/cen_api.py`, `schema.sql`, `requirements.txt` |
| **2 — Adquisición** | ✅ COMPLETA | `Adquisicion_ernc.py`, `adquisicion_ernc.yml`, prueba en producción OK |
| **3 — Meteorología** | ✅ COMPLETA | `utils/openmeteo_api.py`, `Adquisicion_meteo_ernc.py`, `utils/calculos.py` |
| **4 — Mapa y Dashboard base** | ✅ COMPLETA | `components/mapa_ernc.py`, `components/kpis_generales.py`, `app_ernc.py` (sidebar + KPIs + mapa + tab CMG + tab limitaciones) |
| **5 — Tabs Solar y Eólica** | ✅ COMPLETA | `components/tab_solar.py`, `components/tab_eolica.py` (detalle_parque integrado en cada tab) |
| **6 — Forecast e Insights** | ✅ COMPLETA | `components/tab_forecast.py`, `utils/insights.py`, `components/tab_insights.py` |
| **7 — PDF y Deploy** | ✅ COMPLETA | `utils/pdf_report.py`, `.streamlit/config.toml`, deploy Streamlit Cloud, `db.py` soporta st.secrets |

---

## DATOS CONFIRMADOS EN PRODUCCIÓN (2026-06-18)

- **Gen. real:** 275 registros en Supabase (11 parques × 25 horas, ventana 2 días)
- **Gen. programada PCP:** 36 registros (llaves `_FV` y `_EO` funcionando)
- **CMG CRUCERO_______220:** 296.1 USD/MWh (nodo activo para parques del norte)
- **Limitaciones:** PE Campo Lindo con 64.5 MW pendiente
- **SSCC:** Sin instrucciones activas en ventana consultada

---

## NOTAS PARA EL MAPA 3D (Sesión 4)

```python
# TerrainLayer con tiles Terrarium (sin costo, sin token)
elevation_data = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
texture = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
# elevation_scale = 2.5  # exagerar relieve para visualización
# ColumnLayer con altura proporcional a generación actual (elevation = gen_mw × 200)
# Vista inicial: lat=-33.0, lon=-70.5, zoom=4.5, pitch=45, bearing=-10
```

---

## INSIGHTS AUTOMÁTICOS A IMPLEMENTAR (Sesión 6)

1. Desvío gen_real vs programada > ±15% (alerta si > ±25%)
2. Limitación de transmisión activa + caída de generación correlacionada
3. Eficiencia baja sin causa meteorológica: GHI > 400 W/m² pero gen < 75% esperada
4. Viento sobre cut-out: windgusts > 20 m/s en parques eólicos
5. Camanchaca: cloudcover_low > 60% pero cloudcover total < 30% (norte)
6. Wind shear alto: alpha > 0.30 (atmósfera estable, turbinas traseras afectadas)
7. CMG muy bajo (< 5 USD/MWh): ingreso horario mínimo
8. Positivo: factor de planta > 90% en parque solar (excelente recurso)

---

---

## OPEN-METEO — DETALLES IMPLEMENTACIÓN (Sesión 3)

- Wrapper en `utils/openmeteo_api.py`: usa `openmeteo-requests` + `requests-cache` (TTL 30min) + retry.
- Las variables Open-Meteo se mapean a columnas DB en `_CAMPO_MAP` dentro del mismo archivo.
- Los calculados (temp_celda, p_fv_estimada, v100m, alpha, densidad_aire) se calculan en `_response_to_registros` usando `utils/calculos.py`.
- `es_forecast=True` cuando `fecha_hora >= ahora` al momento de la adquisición.
- Pausa 1.5s entre parques para no saturar la API gratuita.
- El workflow corre `Adquisicion_meteo_ernc.py` justo después de `Adquisicion_ernc.py` en el mismo job.

---

---

## APP PRINCIPAL — NOTAS SESIÓN 4

- `app_ernc.py`: layout wide, dark theme (#0f172a), autorefresh 1h, caché datos 5 min.
- Sidebar: lista parques por tipo con gen. actual inline. Botón "Forzar actualización" limpia caché.
- `components/kpis_generales.py`: 6 métricas (Gen total, Solar, Eólica, Desvío PCP, CMG, Limitaciones). Semáforo desvío con CSS inline.
- `components/mapa_ernc.py`: TerrainLayer (tiles Terrarium) + ColumnLayer (altura = gen × 200) + ScatterplotLayer. Tooltip con nombre, gen, factor planta. Vista inicial zoom=4.5, pitch=45.
- Tab "Mapa & Resumen": mapa izq + tabla estado der + gráfico tendencia 24h (real vs programada).
- Tab "CMG": métrica última hora + gráfico histórico 48h (solo nodo CRUCERO_______220).
- Tab "Limitaciones": tabla filas activas (`fecha_efectiva_retorno IS NULL`).
- Tabs Solar y Eólica: placeholder "Sesión 5 pendiente".

---

## CAMBIOS SESIÓN 5 (2026-06-19)

- **CMG multi-nodo:** `config.py` agrega `CMG_NODOS_TODOS` (8 nodos: CRUCERO, CHARRUA, QUILLOTA, PAN_DE_AZUCAR, CARDONES, NOGALES, ANCOA, POLPAICO). Adquisición ahora guarda todos. Tab CMG muestra métricas CRUCERO+CHARRUA + tabla todos + gráfico multi-línea 48h.
- **Mapa rediseñado:** estilo Carto Dark Matter, capas halo+glow+columna+dot+texto. Sin TerrainLayer (conflicto con fondo oscuro). Columnas más gruesas y brillantes, tooltip mejorado con CSS inline.
- **Tab Solar:** KPIs por parque, selector, gráfico 48h (real+PCP+modelo), GHI+nubosidad baja, panel lateral con métricas y semáforo.
- **Tab Eólica:** KPIs por parque, selector, gráfico 48h (real+PCP+modelo eólico), viento 10m/100m+ráfagas+shear, panel lateral.
- Eólicos sur mapeados a `CHARRUA_______220` (pendiente confirmar con AES Andes).

---

## INSIGHTS — REGLAS IMPLEMENTADAS (Sesión 6)

| # | Regla | Severidad | Parque |
|---|-------|-----------|--------|
| 1 | Desvío real vs PCP > ±25% | crítico | por parque |
| 2 | Desvío real vs PCP > ±15% | alerta | por parque |
| 3 | GHI > 400 W/m² pero eficiencia < 75% del modelo | alerta | solar |
| 4 | Eficiencia > 95% del modelo | positivo | solar |
| 5 | Nubosidad baja > 60% con total < 35% (camanchaca) | alerta | solar |
| 6 | Ráfagas > 20 m/s (sobre cut-out) | crítico | eólico |
| 7 | Ráfagas > 16 m/s (acercándose al cut-out) | alerta | eólico |
| 8 | Wind shear α > 0.30 | alerta | eólico |
| 9 | Factor de planta > 90% | positivo | por parque |
| 10 | CMG < 5 USD/MWh | alerta | global |
| 11 | CMG > 200 USD/MWh | positivo | global |
| 12 | Limitación de transmisión activa | crítico | por parque |

## FORECAST — NOTAS (Sesión 6)

- Usa datos `es_forecast=True` de `meteo_ernc` — requiere `Adquisicion_meteo_ernc.py` ejecutado.
- Potencia estimada: `p_fv_estimada_mw` (solar) y `p_eolica_estimada_mw` (eólico), calculados en openmeteo_api.py.
- Agrega por hora → MWh directo (1 fila = 1 hora).
- Caché 30 min en `_cargar_forecast()`.

---

## DEPLOY STREAMLIT CLOUD (Sesión 7)

### Pasos para publicar
1. Hacer push del repo a GitHub (rama `main`)
2. Ir a [share.streamlit.io](https://share.streamlit.io) → New app
3. Repo: el del proyecto | Branch: `main` | Main file: `app_ernc.py`
4. **Settings → Secrets** → pegar:
   ```toml
   SUPABASE_URL = "https://ozeubcqoxsihmmfpswoa.supabase.co"
   SUPABASE_KEY = "sb_publishable_..."   # ← anon key, NO el service_role
   ```
5. Deploy → URL pública lista

### Notas
- `db.py` lee `st.secrets` primero, luego `os.environ` — funciona en cloud y local sin cambios.
- Los scripts de adquisición (`Adquisicion_ernc.py`, `Adquisicion_meteo_ernc.py`) siguen corriendo en GitHub Actions con el `service_role` key — **no** se exponen en el frontend.
- `.streamlit/secrets.toml` está en `.gitignore` — solo usar el panel de Streamlit Cloud para configurarlos.
- El `anon key` de Supabase solo tiene permisos SELECT (RLS) — seguro para frontend público.

## PDF REPORTE (Sesión 7)

- `utils/pdf_report.py`: portada, KPIs globales, tabla por parque (gen, FP, desvío, ingreso estimado), insights automáticos con severidad coloreada.
- Botón "Generar reporte PDF" en sidebar → genera en memoria → botón de descarga aparece debajo.
- No requiere escribir archivos en disco — usa `io.BytesIO`.

*Generado 2026-06-19 — Sesiones 1–7 completadas. Proyecto completo.*
*Stack: Streamlit + pydeck + supabase-py + GitHub Actions + Open-Meteo + API CEN*
