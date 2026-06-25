# CLAUDE.md — Dashboard ERNC AES Andes
> Contexto completo para Claude Code. Leer al inicio de cada sesión.
> Autor: Erick Herrera — AES Andes, Antofagasta, Chile.
> Última actualización: 2026-06-22 (Sesión 17 — KPIs, fixes solar/eólica/CMG, mapa satelital MapTiler, sección BESS).

---

## DESCRIPCIÓN DEL PROYECTO

Dashboard operacional para **11 parques de energías renovables (ERNC) de AES Andes** en Chile:
- 6 parques solares FV (norte, Atacama/Antofagasta)
- 5 parques eólicos (sur, Biobío/Coquimbo)

**Proyecto independiente** del dashboard CTM Mejillones (térmicas ANG/CCR). Hereda el stack y patrones de ese proyecto pero con visualización significativamente más rica.

**Estado actual:** En producción en Streamlit Cloud. GitHub Actions corre cada hora (:10 UTC) para adquisición CEN y meteo Open-Meteo.

---

## URLS DE PRODUCCIÓN

- **GitHub:** https://github.com/ukubrick/ernc-aes-dashboard (público — necesario para Streamlit Cloud free tier)
- **Supabase:** https://ozeubcqoxsihmmfpswoa.supabase.co (proyecto `ernc-aes`)
- **Streamlit Cloud:** share.streamlit.io (cuenta ukubrick, main file: app_ernc.py)

---

## PALETA DE COLORES AES (aplicada en todo el proyecto)

```python
AES_AZUL     = "#3B4CE8"   # azul primario AES — Solar FV, acción principal
AES_AZUL_OSC = "#2530B0"   # azul oscuro — base sidebar
AES_CYAN     = "#4DC8DC"   # cyan — Eólica, acentos sidebar
AES_VIOLETA  = "#9B6FD4"   # violeta — CMG, datos secundarios
AES_VERDE    = "#5AB848"   # verde — positivo / OK
AES_AMBAR    = "#F59E0B"   # ambar — PCP programada / alerta
AES_ROJO     = "#EF4444"   # rojo — crítico / limitaciones
AES_GRIS     = "#F5F7FA"   # fondo general (tema claro) — NUNCA blanco puro como fondo
AES_TEXTO    = "#1A1F36"   # texto principal (azul muy oscuro, no negro puro)
AES_MUTED    = "#6B7280"   # texto secundario
AES_BORDE    = "#E5E7EB"   # bordes / separadores
AES_BLANCO   = "#FFFFFF"   # fondo de cards
```

---

## STACK TECNOLÓGICO

```
Frontend:        Streamlit (Python), tema claro, paleta AES
Mapa 2D:         pydeck (ScatterplotLayer sobre Carto Positron — light)
Gráficos:        Plotly (template plotly_white, paleta AES)
Base de datos:   Supabase (REST API via supabase-py — NO psycopg2 directo)
Adquisición:     Python + GitHub Actions (cron horario, minuto :10 UTC)
Meteorología:    Open-Meteo (gratuita, sin key, resolución horaria, forecast 7d)
API energía:     CEN (SIPUB + Operaciones)
CMG:             JSON S3 público del Coordinador Eléctrico Nacional
Exportación:     ReportLab (PDF, in-memory BytesIO)
Autorefresh:     streamlit-autorefresh (cada 3.600.000 ms)
```

### Por qué supabase-py y NO psycopg2
La conexión TCP directa a Supabase (puerto 5432 y 6543) falla desde redes locales con restricciones de egress (IPv6 / firewall). La REST API de Supabase (HTTPS puerto 443) siempre funciona. Se usa `supabase-py >= 2.0.0`.

---

## CREDENCIALES Y VARIABLES DE ENTORNO

```env
# API CEN
CEN_USER_KEY=10eb683f68b8af18378a8e11727ea6ea    # SIP (pública)
CEN_OPS_KEY=38215ca9ca6d2b1b96666df29164bc5b     # Operaciones

# Supabase — proyecto ernc-aes
SUPABASE_URL=https://ozeubcqoxsihmmfpswoa.supabase.co
SUPABASE_KEY=REDACTED_SERVICE_ROLE_KEY   # service_role (escribe sin RLS)
```

> REGLA DE SEGURIDAD: `service_role` key SOLO en scripts de adquisición y GitHub Actions Secrets.
> El frontend (app_ernc.py / Streamlit Cloud) usa el `anon key` (`sb_publishable_...`) para lectura.
> `.env` y `.streamlit/secrets.toml` están en `.gitignore` — nunca se suben a GitHub.

### GitHub Actions Secrets configurados (repo ukubrick/ernc-aes-dashboard) ✅
```
CEN_USER_KEY   ✅
CEN_OPS_KEY    ✅
SUPABASE_URL   ✅
SUPABASE_KEY   ✅ (service_role)
```

### Streamlit Cloud Secrets configurados ✅
```toml
SUPABASE_URL = "https://ozeubcqoxsihmmfpswoa.supabase.co"
SUPABASE_KEY = "sb_publishable_..."   # anon key — solo lectura
```
El `anon key` se encuentra en: Supabase → proyecto ernc-aes → Settings → API → Project API keys → anon public.

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
│   ├── mapa_ernc.py                          ← mapa 2D pydeck (Carto Positron, ScatterplotLayer)
│   ├── kpis_generales.py                     ← fila KPIs con tooltips help=
│   ├── tab_solar.py                          ← tab Solar FV (parque_activo, tooltips, plotly_white)
│   ├── tab_eolica.py                         ← tab Eólica (parque_activo, tooltips, plotly_white)
│   ├── tab_forecast.py                       ← forecast 7 días + mensaje claro si no hay datos
│   └── tab_insights.py                       ← hallazgos automáticos (cards light, sin emojis)
└── .github/
    └── workflows/
        └── adquisicion_ernc.yml              ← cron horario :10
```

---

## PARQUES (11 confirmados en API CEN)

### Solares FV

| Código | Nombre Display | id_central | llave_opreal | llave_PCP | P_max (MW) | Lat | Lon |
|--------|---------------|-----------|-------------|----------|-----------|-----|-----|
| AS1 | Andes Solar I | 374 | PFV ANDES SOLAR | ANDES_FV | 23.97 | -24.010753 | -68.584921 | OSM way 745505231 |
| AS2A | Andes Solar 2A | 643 | PFV ANDES SOLAR IIA | ANDES_2A_FV | 91.09 | -24.009143 | -68.574685 | OSM way 1296706746 |
| AS2B | Andes Solar 2B | 1850 | PFV ANDES SOLAR IIB | ANDES_2B_FV | 220.0 | -24.000723 | -68.575145 | OSM way 974171190 |
| AS3 | Andes Solar III | 2322 | PFV Andes Solar III | ANDES_3_FV | 175.0 | -24.001486 | -68.565828 | OSM way 1296706747 |
| AS4 | Andes Solar IV | 2076 | PFV ANDES SOLAR IV | ANDES_4_FV | 220.0 | -24.021944 | -68.573460 | OSM way 1144233017 |
| BOL | PFV Bolero | 456 | PFV BOLERO | BOLERO_1_FV | 161.3 | -23.475195 | -69.408486 | Sierra Gorda, Antofagasta |

### Eólicos

| Código | Nombre Display | id_central | llave_opreal | llave_PCP | P_max (MW) | Lat | Lon | Referencia |
|--------|---------------|-----------|-------------|----------|-----------|-----|-----|-----------|
| CL | PE Campo Lindo | 1845 | PE CAMPO LINDO | CAMPO_LINDO_EO | 76.8 | -37.404179 | -72.494720 | Los Ángeles, Biobío |
| OLM | PE Los Olmos | 1757 | PE LOS OLMOS | LOS_OLMOS_EO | 115.92 | -37.649278 | -72.473876 | Mulchén, Biobío |
| CUR | PE Los Cururos | 318 | PE LOS CURUROS | LOS_CURUROS_EO | 115.08 | -31.012533 | -71.637465 | Los Cururos Sur, Coquimbo |
| STM | PE San Matías | 2091 | PE SAN MATIAS | SAN_MATIAS_EO | 87.5 | -37.434120 | -72.552807 | Los Ángeles, Biobío |
| MSM | PE Mesamavida | 1758 | PE MESAMÁVIDA | MESAMAVIDA_EO | 70.56 | -37.489984 | -72.459097 | Los Ángeles, Biobío |

**Capacidad total:** ~891 MW Solar + ~466 MW Eólica = **~1.357 MW**

> Coordenadas confirmadas por Erick Herrera (2026-06-19) desde OSM y datos AES.

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
- **CRÍTICO:** El `anon key` necesita políticas RLS explícitas para poder leer. Sin ellas retorna `[]` silenciosamente (no lanza error). SQL ejecutado en producción (2026-06-19):

```sql
CREATE POLICY "anon_select" ON generacion_real_ernc       FOR SELECT USING (true);
CREATE POLICY "anon_select" ON generacion_programada_ernc  FOR SELECT USING (true);
CREATE POLICY "anon_select" ON meteo_ernc                  FOR SELECT USING (true);
CREATE POLICY "anon_select" ON cmg_ernc                    FOR SELECT USING (true);
CREATE POLICY "anon_select" ON limitaciones_ernc           FOR SELECT USING (true);
CREATE POLICY "anon_select" ON sscc_ernc                   FOR SELECT USING (true);
```
Si se crea una tabla nueva, agregar su política antes de que el dashboard la consulte.

---

## CONVENCIONES DE CÓDIGO

```python
# Hora CEN: convención 1-24 → usar hora - 1 para convertir a 0-based
hora_0based = int(item["hora"]) - 1  # gen-real v3

# PCP v4: fecha_hora ya viene 0-based, NO convertir
fecha_hora = item["fecha_hora"][:19]  # solo truncar a segundos

# fecha_hora en DB: siempre string "YYYY-MM-DD HH:MM:SS" en hora America/Santiago
# Gen = 0 horas nocturnas (solar): is_day=False → NO es error
# BESS: id_central=None → ignorar en v1

# Retry: SIEMPRE usar _get_with_retry() para todas las llamadas CEN
# Rate limit 429: el retry exponencial lo maneja — es normal ver 1-2 retries

# Supabase: usar supabase-py, NO psycopg2
# Conexión TCP directa (5432/6543) falla desde redes locales

# TIMEZONE EN QUERIES: los fecha_hora en DB están en hora Santiago (UTC-3).
# NUNCA usar datetime.now(timezone.utc) para filtrar — usar _ahora_santiago():
#   from datetime import datetime, timezone, timedelta
#   def _ahora_santiago(): return datetime.now(timezone(timedelta(hours=-3)))
# Esta función ya existe en utils/db.py — usarla en cualquier query nueva.

# st.plotly_chart: SIEMPRE agregar key= único explícito para evitar
# StreamlitDuplicateElementId cuando hay múltiples gráficos en tabs/columnas.
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
| **8 — Bugs producción** | ✅ COMPLETA | StreamlitDuplicateElementId, timezone UTC vs Santiago, RLS sin políticas anon, key rotado |
| **9 — Mejoras visuales + fixes** | ✅ COMPLETA | Ver sección SESIÓN 9 |
| **10 — Fix paginación PCP v4 + ventana 5 días** | ✅ COMPLETA | Ver sección SESIÓN 10 |
| **11 — UX mejoras múltiples** | ✅ COMPLETA | Ver sección SESIÓN 11 |

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

---

## SISTEMA DE DISEÑO VISUAL (actualizado Sesión 9)

El diseño del dashboard está documentado aquí como referencia para replicar en otros dashboards (ej. CTM).

### Principios generales
- **Fondo**: `#F5F7FA` (gris muy suave), **nunca blanco puro como fondo de página**
- **Cards**: siempre `#FFFFFF` con `border-radius: 10-12px`
- **Sin emojis** en ningún componente
- **Sin comentarios** de "qué hace" en el código — solo comentarios del WHY
- Todo `st.plotly_chart()` lleva `key=` único explícito
- Timezone siempre `America/Santiago` (UTC-3), nunca `timezone.utc`
- **f-strings**: NO usar backslash dentro del f-string (error Python < 3.12) — extraer a variable antes
- **Fuente**: Inter (Google Fonts), pesos 400/500/600/700/800

### Sidebar
```css
/* Gradiente de 3 tonos azul muy oscuro */
background: linear-gradient(160deg, #2530B0 0%, #111540 60%, #0d1035 100%);
box-shadow: 4px 0 20px rgba(0,0,0,0.25);

/* Título empresa */
font-size: 22px; font-weight: 800; color: white; letter-spacing: -0.5px;

/* Etiquetas de sección (SOLAR FV / EÓLICA) */
font-size: 10px; font-weight: 700; color: #4DC8DC;
text-transform: uppercase; letter-spacing: 1.2px;

/* Botón normal */
background: rgba(255,255,255,0.06);
border: 1px solid rgba(255,255,255,0.12);
border-radius: 8px; transition: all 0.20s cubic-bezier(0.4,0,0.2,1);

/* Botón hover */
background: rgba(77,200,220,0.22); border-color: #4DC8DC;
transform: translateX(3px);

/* Botón activo */
background: linear-gradient(90deg, #4DC8DC 0%, #38b5cc 100%);
color: #2530B0; font-weight: 700;
box-shadow: 0 4px 12px rgba(77,200,220,0.40);
```

### KPI cards (métricas Streamlit)
```css
background: #FFFFFF; border-radius: 12px;
border: 1px solid #E5E7EB;
border-top: 4px solid [color por posición];   /* diferenciador visual principal */
box-shadow: 0 2px 12px rgba(59,76,232,0.08);
transition: transform 0.20s ease, box-shadow 0.20s ease;

/* Hover lift */
transform: translateY(-3px);
box-shadow: 0 8px 24px rgba(59,76,232,0.15);

/* Color borde-top por posición (7 KPIs) */
1º Gen Total    → #3B4CE8  azul
2º Solar FV     → #3B4CE8  azul
3º Eólica       → #4DC8DC  cyan
4º Desvío PCP   → #F59E0B  ámbar
5º CMG Crucero  → #9B6FD4  violeta
6º CMG Charrua  → #4DC8DC  cyan
7º Limitaciones → #EF4444  rojo

/* Tipografía interna */
Label:  10px, 700, uppercase, letter-spacing 0.8px, color #6B7280
Valor:  22px, 800, color #1A1F36
Delta:  12px, 600
```

### Tabs
```css
/* Barra contenedora */
background: #FFFFFF; border-bottom: 3px solid #3B4CE8;
border-radius: 8px 8px 0 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05);

/* Tab inactiva */
color: #6B7280; font-size: 13px; font-weight: 500; padding: 9px 18px;
transition: all 0.20s cubic-bezier(0.4,0,0.2,1);

/* Tab activa */
background: linear-gradient(135deg, #3B4CE8 0%, #2530B0 100%);
color: white; font-weight: 700;
box-shadow: 0 -2px 10px rgba(59,76,232,0.30);

/* Contenido del tab */
animation: fadeInUp 0.35s ease both;
```

### Gráficos Plotly
```python
# Configuración estándar en update_layout
fig.update_layout(
    template="plotly_white",
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#F5F7FA",
    transition=dict(duration=500, easing="cubic-in-out"),  # animación entre datos
)

# Colores de trazas por tipo
Solar FV estimada    → #3B4CE8  (fill tozeroy rgba(59,76,232,0.10))
Eólica estimada      → #4DC8DC  (fill tozeroy rgba(77,200,220,0.12))
PCP programada       → #F59E0B  (línea dash, sin fill)
Gen real             → color primario de tecnología
Viento / GHI         → #6B7280  (dot, eje secundario y2)
```
```css
/* Wrapper CSS del gráfico */
border-radius: 12px; overflow: hidden;
box-shadow: 0 2px 10px rgba(0,0,0,0.06);
animation: fadeInUp 0.5s ease both;
transition: box-shadow 0.2s ease;
/* Hover */
box-shadow: 0 6px 20px rgba(59,76,232,0.12);
```

### Animaciones CSS (keyframes definidos en app_ernc.py)
```css
fadeInUp:     opacity 0→1, translateY 16px→0  — página, gráficos, tablas, cards
fadeInLeft:   opacity 0→1, translateX -12px→0 — cards de insights (escalonado)
pulse-border: box-shadow pulsante rojo         — insight crítico
dot-pulse:    scale 1→1.5→1                   — punto indicador en crítico
```
- Delay escalonado en insights: `animation-delay: idx * 0.06s`
- KPI cards con delay: `nth-child(n) { animation-delay: n*0.05s }`

### Cards de insights
```css
critico:  bg #FEF2F2, borde-izq #EF4444, badge rgba(239,68,68,0.12)
alerta:   bg #FFFBEB, borde-izq #F59E0B, badge rgba(245,158,11,0.12)
positivo: bg #F0FDF4, borde-izq #5AB848, badge rgba(90,184,72,0.10)
info:     bg #EFF6FF, borde-izq #3B4CE8, badge rgba(59,76,232,0.10)
border-radius: 0 10px 10px 0;  /* solo esquinas derechas redondeadas */
```

### Mapa pydeck
```css
border-radius: 14px; overflow: hidden;
box-shadow: 0 4px 16px rgba(0,0,0,0.12);
animation: fadeInUp 0.6s ease both;
```
- Estilo mapa: Carto Positron (light), NO Dark Matter
- Vista Chile completo: lat=-33.5, lon=-70.8, zoom=4.6
- Vista por parque: zoom=8.5, centrado en coordenadas del parque

### Tipografía
```
Título principal:  30px, 800, letter-spacing -0.5px, color #1A1F36
Subtítulos:        13px, 600, color #1A1F36
Texto secundario:  11-12px, 400/500, color #6B7280
Labels uppercase:  10-11px, 700, letter-spacing 0.8-1.2px
```

### Sidebar — sección fuentes de datos
Al final del sidebar, antes de la firma:
- Bloque con `background: rgba(255,255,255,0.07)`, borde sutil
- Título "FUENTES DE DATOS" en cyan 10px uppercase
- 4 filas: Gen. real CEN / PCP programada / Meteo Open-Meteo / CMG CEN S3
- Hora en formato `DD/MM HH:MM` — función `_fmt_hora(ts)` en `app_ernc.py`
- Query: `utils/db.query_ultimas_actualizaciones()` — devuelve dict con keys `gen_real`, `gen_prog`, `meteo`, `cmg`

### Firma al pie del sidebar
```html
<div style='border-top:1px solid rgba(255,255,255,0.12); text-align:center'>
  Dashboard creado por
  <b>Erick Herrera</b>
  AES Andes
</div>
```

---

## DEPLOY EN PRODUCCIÓN (2026-06-19)

### GitHub
- Repo: `https://github.com/ukubrick/ernc-aes-dashboard` (público)
- Push inicial: `git init` → `git add .` → `git commit` → `git push` ✅
- Credenciales guardadas en Keychain Mac — no pidió token personal

### Streamlit Cloud
- Conectado con cuenta GitHub ukubrick
- Main file: `app_ernc.py` | Branch: `main`
- Secrets configurados en Settings → Secrets (SUPABASE_URL + anon SUPABASE_KEY) ✅
- El repo debe ser público para Streamlit Cloud free tier

### GitHub Actions ✅
- Archivo: `.github/workflows/adquisicion_ernc.yml`
- Cron: `"10 * * * *"` (minuto :10 de cada hora UTC)
- Step 1: `python Adquisicion_ernc.py` | Step 2: `python Adquisicion_meteo_ernc.py`
- 4 secrets configurados en repo → Settings → Secrets and variables → Actions

### Para correr localmente
```bash
cd "/Users/erickosvaldoherrerakerr/Desktop/ML DATA/Dashboard ERNC/ernc-aes-dashboard"
source .venv/bin/activate
streamlit run app_ernc.py
# Si el puerto está ocupado: kill $(lsof -ti:8501)
```

---

## BUGS CONOCIDOS Y RESUELTOS (Sesión 8 — 2026-06-19)

### Bug 1: StreamlitDuplicateElementId en st.plotly_chart
- **Síntoma:** App crasheaba al navegar entre tabs con error `StreamlitDuplicateElementId`.
- **Causa:** Todos los `st.plotly_chart()` carecían de `key=` explícito. Streamlit genera IDs automáticos que colisionan al re-renderizar dentro de tabs/columnas.
- **Fix:** Agregar `key=` único a cada llamada. Convención usada:
  - `key="solar_grafico_gen"`, `key="solar_grafico_ghi"`
  - `key="eolica_grafico_gen"`, `key="eolica_grafico_viento"`
  - `key="forecast_grafico_portfolio"`, `key=f"forecast_grafico_parque_{parque}"`
  - `key="mapa_grafico_tendencia"`, `key="cmg_grafico_historico"`
- **Regla:** Todo `st.plotly_chart` nuevo debe tener `key=` único. Si el gráfico depende de un selector (ej. parque), incluirlo en el key: `key=f"nombre_{variable}"`.

### Bug 2: Queries retornaban vacío por timezone incorrecto
- **Síntoma:** Dashboard mostraba 0.0 MW y `—` en todos los KPIs pese a haber datos en Supabase.
- **Causa:** Las queries en `utils/db.py`, `tab_eolica.py`, `tab_solar.py` y `tab_forecast.py` usaban `datetime.now(timezone.utc)` para el filtro `gte("fecha_hora", desde)`. Los `fecha_hora` en DB están en hora local de Santiago (UTC-3), por lo que el filtro buscaba 3 horas hacia el futuro y no encontraba registros.
- **Fix:** Reemplazar `datetime.now(timezone.utc)` por `_ahora_santiago()` definida en `utils/db.py`:
  ```python
  def _ahora_santiago():
      from datetime import datetime, timezone, timedelta
      return datetime.now(timezone(timedelta(hours=-3)))
  ```
- **Regla:** NUNCA usar `timezone.utc` para filtrar `fecha_hora` en este proyecto. Siempre `_ahora_santiago()`.

### Bug 3: RLS bloqueaba lectura con anon key (dashboard sin datos)
- **Síntoma:** Idéntico al Bug 2 — todos los valores `—` y `0.0 MW`. Se detectó después de corregir el Bug 2.
- **Causa:** Supabase habilita RLS por defecto en todas las tablas. Sin políticas `SELECT` explícitas para `anon`, las queries retornan `[]` silenciosamente (sin error). El `anon key` del frontend no podía leer ninguna tabla.
- **Fix:** Ejecutar en Supabase SQL Editor:
  ```sql
  CREATE POLICY "anon_select" ON generacion_real_ernc       FOR SELECT USING (true);
  CREATE POLICY "anon_select" ON generacion_programada_ernc  FOR SELECT USING (true);
  CREATE POLICY "anon_select" ON meteo_ernc                  FOR SELECT USING (true);
  CREATE POLICY "anon_select" ON cmg_ernc                    FOR SELECT USING (true);
  CREATE POLICY "anon_select" ON limitaciones_ernc           FOR SELECT USING (true);
  CREATE POLICY "anon_select" ON sscc_ernc                   FOR SELECT USING (true);
  ```
- **Regla:** Al crear tabla nueva → agregar política antes de usar en el dashboard.

---

## SESIÓN 9 — MEJORAS VISUALES Y FIXES (2026-06-19)

### Fixes
1. **Forecast eólica = 0**: `openmeteo_api.py` nunca llamaba a `calcular_potencia_eolica_estimada()` en el bloque eólico. Fix: agregar llamada con `(v100m, rho, pmax)` al final del bloque `else`. Requiere re-ejecutar el workflow para repoblar `p_eolica_estimada_mw` en DB.

2. **PCP en forecast**: nueva función `_cargar_pcp_forecast()` en `tab_forecast.py` que carga `generacion_programada_ernc` desde ahora hasta `+2 días`. Se muestra como línea amber dash en gráfico portfolio y por parque. No requiere datos adicionales — usa tabla ya existente.

### Nuevas funcionalidades
3. **Sidebar — fuentes de datos**: nueva función `query_ultimas_actualizaciones()` en `utils/db.py` que consulta el `MAX(fecha_hora)` de las 4 tablas principales. Se muestra en el sidebar con hora en formato `DD/MM HH:MM`.

4. **Sidebar — firma**: "Dashboard creado por Erick Herrera" al pie, con separador y estilo sutil.

5. **Pestaña Estadísticas** (`components/tab_estadisticas.py`): MWh acumulado, FP ranking, desvío vs PCP, ingreso USD estimado.

6. **Mapa auto-center**: `render_mapa(gen_por_parque, parque_activo)` centra en el parque seleccionado desde sidebar (zoom 8.5 vs 4.6 en vista general Chile).

7. **KPIs duales CMG**: 7 columnas — CRUCERO 220 (solar norte) + CHARRUA 220 (eólica sur), ingreso separado por tecnología.

### Rediseño visual completo
- Sidebar con gradiente oscuro AES, botones con efecto hover translateX, activo en cyan
- KPI cards con borde-top de color diferente por tipo, hover lift
- Tabs con gradiente azul en activa, fadeInUp en contenido
- Gráficos con `transition 500ms`, border-radius, shadow y hover glow
- Insights con fadeInLeft escalonado, dot-pulse en críticos, badge coloreado
- Título principal agrandado a 30px/800
- Título sidebar "AES Andes ERNC" a 22px/800, sin ícono

---

## SESIÓN 10 — FIX PAGINACIÓN PCP Y VENTANA 5 DÍAS (2026-06-20)

### Bug crítico corregido: paginación PCP v4 cortaba en página 1

**Síntoma:** Solo ~33 registros en `generacion_programada_ernc` (1 hora por parque) pese a haber datos en la API.

**Causa:** En `utils/cen_api.py`, función `fetch_gen_programada()`, la lógica de corte del loop usaba:
```python
total = data.get("total", len(items))   # "total" no existe en la respuesta v4
if page * 5000 >= total:                # fallback a 5000 → 1*5000 >= 5000 → True → corta en pag 1
    break
```
La API PCP v4 devuelve `totalPages` (no `total`). Como `total` era `None`, el fallback `len(items) = 5000` hacía que la condición se cumpliera siempre en la primera página.

**Fix aplicado** (`utils/cen_api.py:195`):
```python
total_pages = data.get("totalPages", 1) if isinstance(data, dict) else 1
if page >= total_pages:
    break
```

**Estructura real de respuesta PCP v4:**
```json
{ "data": [...], "totalPages": 63, "page": 1, "limit": 5000 }
```
- Cada página = una hora del sistema completo (~5000 generadores)
- Ventana 2 días = ~63 páginas | Ventana 5 días = ~244 páginas
- ~5s por página → 2 días ≈ 5 min | 5 días ≈ 19 min

### Ampliación de ventana

- `DIAS_VENTANA` cambiado de `2` a `5` en `config.py` — aplica a gen-real, PCP, meteo y SSCC
- `timeout-minutes` del workflow subido de `40` a `60` para cubrir los ~19 min de PCP

### Commits
- `5c92280` fix: corregir paginación PCP v4 — usar totalPages en vez de total
- `0e6e51d` config: ampliar ventana adquisición PCP a 5 días, timeout workflow a 60 min

---

## PENDIENTES

- [ ] Confirmar nodo CMG correcto para eólicos sur (CHARRUA_______220 vs otro)
- [ ] Agregar logo AES Andes en sidebar cuando esté disponible (assets/logo_aes.png)
- [ ] `st.segmented_control` requiere Streamlit >= 1.38 — verificar versión en Streamlit Cloud
- [ ] Correr workflow manual para repoblar `p_eolica_estimada_mw` en `meteo_ernc` (fix sesión 9)
- [x] Gráficos comprimidos en primer render de tab — RESUELTO en Sesión 13 (navegación de vista única)
- [ ] **Satélite en el mapa**: reactivar vista Satélite agregando un token gratuito (Mapbox o MapTiler) a `secrets.toml`. El style raster ESRI ya está dormido en `mapa_ernc.py` (`_ESRI_SAT_STYLE`); sin token, pydeck no lo renderiza. (Sesión 15)
- [ ] **Ventana PCP**: si la query PCP de 5 días se sigue colgando/degradando en la API del CEN, bajar `DIAS_VENTANA` del PCP a 1-2 días para que el cron sea más robusto. (Sesión 15)

---

## SESIÓN 13 — FIX DEFINITIVO COMPRESIÓN GRÁFICOS + NAVEGACIÓN (2026-06-21)

### Bug raíz: gráficos Plotly comprimidos al abrir un tab por primera vez

**Causa confirmada:** `st.tabs` renderiza TODOS los paneles en el DOM simultáneamente
y oculta los inactivos con `display:none`. Un `st.plotly_chart(use_container_width=True)`
dentro de un panel oculto se inicializa midiendo el ancho del contenedor como ~0px →
el gráfico queda comprimido. Al cambiar el selectbox/parque/fecha se dispara un rerun
que re-renderiza el gráfico con el tab ya visible → recién ahí mide bien. El fix de
`range=[x_min,x_max]` (Sesión 12) atacaba el espacio vacío del eje, NO este problema de ancho.

**Fix definitivo — navegación de vista única:** se eliminó `st.tabs` del layout principal.
- `app_ernc.py`: nueva `_navegacion()` + estado `st.session_state["vista"]` (variable normal,
  no key de widget) + barra de botones (`type="primary"` = activo). Se renderiza SOLO la vista
  activa. El gráfico siempre se monta en un contenedor visible y a ancho real → nunca se comprime.
- Se eliminó el hack frágil de `key` dinámico + `default=` en `st.tabs` (`tab_forzado`,
  `_tabs_key`, `_tab_map`) que además rompía la navegación del sidebar.

**Regla:** NUNCA poner `st.plotly_chart` en paneles de `st.tabs` inactivos. Para vistas
con gráficos, usar navegación de vista única (renderizar solo la activa).

### Bug: navegación del sidebar no cambiaba de central
Resuelto por el mismo cambio: el sidebar escribe `st.session_state["vista"]` directamente
(variable normal, no widget) → navegación 100% fiable.

### Selección de parque (one-shot)
El sidebar fuerza el selectbox de Solar/Eólica una sola vez vía `st.session_state["_sync_parque"]`,
consumido con `pop()` en el tab. Después el desplegable es dueño de su estado y el usuario puede
cambiar la central libremente sin que se revierta. Antes la lógica forzaba el selectbox en cada
rerun, revirtiendo la elección manual.

### Refactor / limpieza
- Eliminado helper `_xmin()` sin uso en `tab_solar.py` y `tab_eolica.py`.
- Eliminado CSS muerto de `.stTabs`; reemplazado por estilo de botones de navegación
  (`.block-container .stButton button[kind=primary|secondary]`).
- `tab_insights.py` conserva `st.tabs` interno (solo tablas/métricas, sin Plotly → no sufre el bug).

---

## SESIÓN 11 — MEJORAS UX MÚLTIPLES (2026-06-20)

### Cambios implementados

1. **Mapa — zoom inicial reducido**: de `zoom=4.6` a `zoom=3.9`, centrado en lat=-32.0 para que los 6 parques solares del norte (Atacama) y los 5 eólicos del sur (Biobío) no se solapen al cargar.

2. **Keep-alive Streamlit Cloud**: el workflow de GitHub Actions hace un `curl` a la URL de producción al final de cada ejecución horaria, evitando la hibernación por inactividad.

3. **Filtrado valores negativos gen bruta**: en `tab_solar.py` y `tab_eolica.py` se filtran `gen_real_mw < 0` antes de graficar (pueden aparecer por despacho negativo del BESS asociado).

4. **Modelo FV — ceros nocturnos excluidos**: el trazado "Modelo FV" solo muestra horas donde `is_day=True`, eliminando la línea plana en 0 que contaminaba el gráfico nocturno.

5. **Ventana configurable en Solar y Eólica**: selector de 24/48/72/120 horas para ambos tabs (key `solar_ventana_horas` / `eolica_ventana_horas`).

6. **Layout Solar y Eólica refactorizado**:
   - Gráfico de generación a ancho completo (sin columna lateral)
   - Fila de 6 métricas horizontales debajo del gráfico (gen, cap, FP, desvío, GHI/viento, temp/shear)
   - Expander "Variables y fórmulas del modelo FV/eólico" con tabla de series y explicación matemática
   - GHI/viento en gráficos separados debajo

7. **Tab Eólica — shear en gráfico propio**: `wind_shear_alpha` en subgráfico de 160px separado con línea de umbral α=0.30, en lugar de eje secundario mezclado con velocidades.

8. **Tab Insights — subtab meteorológico**: nueva pestaña "Condiciones meteorológicas" con tabla de parámetros actuales Solar (GHI, Tc, nubosidad) y Eólica (v10m, v100m, ráfagas, shear) para todos los parques. Alertas marcadas con `!` y `~`.

9. **Forecast — gráficos más altos**: portfolio 380px, parque 320px (antes 320/260). Columnas del selector tipo/parque ampliadas a [1,3].

10. **Limitaciones — query ampliada**: `query_limitaciones_activas()` ahora devuelve también limitaciones con retorno registrado en los últimos 30 días. El tab muestra tabla separada activas vs históricas.

### Keys de plotly_chart actualizados
Ahora incluyen el parque en el key para evitar StreamlitDuplicateElementId al cambiar parques:
- `solar_grafico_gen_{parque}`, `solar_grafico_ghi_{parque}`
- `eolica_grafico_gen_{parque}`, `eolica_grafico_viento_{parque}`, `eolica_grafico_shear_{parque}`

---

## SESIÓN 12 — FIXES NAVEGACIÓN Y EJE X (2026-06-21)

### Bug: gráficos comprimidos en primer render de tab

**Síntoma:** Al abrir por primera vez una pestaña (Solar FV, Eólica, Forecast, Estadísticas), los datos del gráfico aparecen apilados hacia la derecha (o izquierda) con espacio vacío.

**Causa investigada:** Se descartó que fuera un problema de ancho SVG (Streamlit 1.58.0 mide 940px correctamente desde el primer render). La causa real son **dos fuentes de espacio vacío en el eje X**:
1. **Lado derecho:** `xaxis=dict(range=[corte, None])` — `None` hace que Plotly extienda el eje hasta el tiempo actual del sistema. Si los datos tienen lag (ej. datos hasta las 20:00 pero son las 03:00 del día siguiente), el eje muestra 7 horas vacías a la derecha.
2. **Lado izquierdo:** `corte = ahora - ventana` puede ser anterior al primer dato en DB (ej. ventana=7d pero datos desde hace 5d), dejando 2 días vacíos al inicio.

**Fix aplicado en `tab_solar.py` y `tab_eolica.py`:**
```python
# Calcular x_min y x_max desde los datos reales — no desde la ventana teórica
_xmins, _xmaxs = [], []
if not df_gen.empty:
    _xmins.append(df_gen["fecha_hora"].min())
    _xmaxs.append(df_gen["fecha_hora"].max())
if not df_prog.empty:
    _xmins.append(df_prog["fecha_hora"].min())
    _xmaxs.append(df_prog["fecha_hora"].max())
x_min = min(_xmins) if _xmins else corte
x_max = max(_xmaxs) if _xmaxs else None
# ...
xaxis=dict(range=[x_min, x_max])  # reemplaza range=[corte, None]
```
El mismo patrón aplica a `_grafico_ghi()`, `_grafico_viento()` y `_grafico_shear()`.

**Estado:** El fix reduce el problema pero no lo elimina completamente en producción (datos en DB con lag > 1 día pueden seguir causando compresión visual al primer render). Queda pendiente investigación adicional.

### Bug: navegación sidebar rota

**Síntoma:** Botones del sidebar no cambiaban de tab activo.

**Causa:** `st.session_state["main_tabs"] = valor` es ignorado silenciosamente por Streamlit cuando la key ya está asociada a un widget activo. No se puede escribir sobre el state de un widget vivo.

**Fix aplicado en `app_ernc.py`:**
```python
# Estrategia: key dinámica por destino fuerza recreación del componente con default= correcto
if tab_forzado and tab_forzado in _tab_map:
    _key = f"tabs_{tab_forzado}_{parque_activo}"   # key nueva → Streamlit recrea st.tabs
    st.session_state["_tabs_key"] = _key
    _default = _tab_map[tab_forzado]               # default= activa el tab correcto
else:
    _key = st.session_state.get("_tabs_key", "tabs_default")  # reutiliza key actual
    _default = None                                 # sin default → mantiene posición actual

tab_resumen, tab_solar, ... = st.tabs(tab_labels, key=_key, default=_default)
```

**Por qué funciona:** Al cambiar el key, Streamlit crea un componente nuevo y respeta `default=`. En reruns siguientes (cambio de ventana, parque), la key no cambia → el tab activo se preserva. El `tab_forzado` se consume con `pop()` en cada rerun.

**Regla:** Para navegar programáticamente entre tabs en Streamlit, NUNCA escribir en `session_state[tab_key]` directamente. Usar key dinámica + `default=`.

### Commits sesión 12
- `843289a` fix: rango X calculado desde datos reales (x_min/x_max) en tab_solar y tab_eolica
- `d5fa6d7` fix: navegación sidebar restaurada — key dinámico con default= al tab correcto

## SESIÓN 14 — FÓRMULAS, MODELOS CORREGIDOS, CMG Y PESTAÑA ML (2026-06-21)

### Correcciones de fórmulas / adquisición
- **Viento en m/s (bug crítico):** Open-Meteo entrega viento en **km/h** por defecto. Se trataba
  como m/s → el modelo eólico sobreestimaba (mostraba Pmax casi siempre). Fix: `wind_speed_unit:"ms"`
  en `_params_solar` y `_params_eolica` (`openmeteo_api.py`). **Requiere re-correr adquisición meteo.**
- **Curva de potencia eólica realista:** `calcular_potencia_eolica_estimada` ahora usa cut-in (3 m/s),
  rampa cúbica hasta rated (12 m/s), meseta a Pmax hasta cut-out (25 m/s) y **0 sobre cut-out**.
  Constantes nuevas en `config.py`: `TURBINA_V_CUTIN/RATED/CUTOUT`.
- **Wind shear α acotado:** se limita a `[-0.10, 0.60]` (`SHEAR_ALPHA_MIN/MAX`) y se ignora con vientos
  <1.5 m/s (antes daba α>2 absurdos). `interpolar_viento_100m` corregido.
- **Modelo FV de noche:** en `tab_solar._grafico_gen` la noche se marca NaN con `connectgaps=False`,
  eliminando la diagonal falsa. Ya NO se filtran los puntos nocturnos (eso causaba el artefacto).
- **Saneamiento gen real:** `cen_api.fetch_gen_real` descarta valores > 110% Pmax (físicamente
  imposibles). El resto se auto-corrige con el upsert horario de ventana 5 días (sistema tipo CTM).

### CMG — nodos reales del feed S3
Los nombres en `CMG_NODOS_TODOS` no calzaban con el feed (n.º de guiones bajos). Solo CRUCERO y
CHARRUA matcheaban. Nombres reales confirmados (8): `CRUCERO/ATACAMA/TARAPACA/CARDONES/P.AZUCAR/
QUILLOTA/CHARRUA/P.MONTT` + `______220`. `query_cmg_ultimo` ahora usa `limit(400)` para que todos
aparezcan. **Los nodos nuevos se poblarán al correr la adquisición CMG.**

### Leyendas y hovers
- Fórmulas movidas a expander "Fórmulas del modelo" con `st.latex` (tipografía científica elegante).
- Hovers de las series simplificados a solo valor + nombre corto (antes la fórmula tapaba el valor).

### Nueva pestaña ML Analysis (`components/tab_ml.py`)
Sub-navegación con `st.radio` (no `st.tabs`, para no reintroducir el bug de compresión). Modelos
entrenados en vivo con histórico de Supabase. Requiere `scikit-learn>=1.4.0` (agregado a requirements):
1. **Forecast de generación** — RandomForest meteo→gen por parque; R²/MAE, comparación con modelo
   físico, importancia de variables y pronóstico aplicado al forecast meteo. (Solar AS1: R²≈0.95.)
2. **Detección de anomalías** — residuos del modelo (z-score>3) + IsolationForest; marca horas raras.
3. **Predicción de CMG** — RandomForest con rezagos por nodo + pronóstico recursivo 12h.
4. **Análisis de eficiencia** — performance ratio real/teórico por parque + clustering KMeans.
Todas las secciones degradan con mensaje claro si faltan datos (umbral ≥48 registros).

### Pendiente operativo
Correr `Adquisicion_meteo_ernc.py` y `Adquisicion_ernc.py` (o esperar el cron) para repoblar la DB
con viento en m/s, nodos CMG nuevos y más histórico para los modelos ML.

---

## SESIÓN 15 — INSIGHTS, MAPA, ESTADÍSTICAS, METEO/SISTEMA Y FIX ADQUISICIÓN (2026-06-21)

### Fix crítico: paginación de limitaciones (mismo bug que PCP v4)
`fetch_limitaciones` usaba `data.get("total", len(items))` y cortaba en la página 1 → solo
aparecía 1 limitación. La API v4 publica `totalPages`, no `total`. Corregido en `utils/cen_api.py`
con paginación robusta (totalPages → total → página incompleta) y page size 500. **Validado
contra la API real: pasó de 1 → 4 limitaciones** (Campo Lindo, Los Olmos, Bolero, Mesamávida).
Mismo patrón aplicado a `fetch_gen_real`. El matching de nombres ahora normaliza tildes.

### Adquisición más confiable (`_get_with_retry`)
Sesión HTTP reutilizable, reintenta en 429/5xx además de red, respeta `Retry-After`, backoff
exponencial con jitter. **OJO PCP:** la query de 5 días del sistema completo puede degradarse en
la API (se observó page 1 colgada >25 min). El cron se auto-corrige; evaluar bajar la ventana PCP
a 1-2 días si reincide.

### Insights nuevos (`utils/insights.py`)
CMG negativo (vertimiento forzado, crítico), parque FV caído con buen GHI (ratio<25%, crítico),
generación eólica baja con buen viento (curtailment/falla), y "sin telemetría reciente".

### Botones de central clicables + reorden (puntos 4 y 5)
Las tarjetas KPI de Solar/Eólica eran markdown con `cursor:pointer` falso → ahora son `st.button`
reales que setean el selectbox (escribir la key antes de crear el widget + rerun). Reordenado:
series de tiempo primero, leyenda + fórmulas al final.

### Sidebar (punto 9)
Bloque "Fuentes de datos" movido arriba (bajo el título) con semáforo de conexión palpitante
(`pulse-green`/`pulse-red`) y estado global Conectado/Parcial/Sin conexión. Helper
`_estado_fuente(ts, horas_max)`.

### Estadísticas (punto 6)
Donut de mix solar/eólica, área apilada por tecnología en el tiempo, heatmap de FP por hora del día.

### Nueva pestaña Meteo & Sistema (`components/tab_meteo_sistema.py`)
Alertas meteo anticipadas (forecast 48h), heatmaps de nubosidad y viento hub pronosticados, y
contexto de mercado CMG nacional (spread Norte-Sur + ranking). Reutiliza `meteo_ernc`/`cmg_ernc` —
sin tablas nuevas.

### Mapa (`components/mapa_ernc.py`)
Selector **Claro / Detallado** (Voyager) + ciudades de referencia. **Satélite descartado:** pydeck
no renderiza TileLayer raster (necesita callback JS) y el map_style raster exige token Mapbox. El
style ESRI quedó dormido por si se agrega un token gratuito a futuro.

### Demanda CEN: NO disponible en el plan SIP
Todas las variantes (`demanda-real`, `demanda`, v1-v5) dan 404. `costo-marginal-real/v4` existe
pero publica con días de rezago y son ~260k páginas. No usable en tiempo real.

---

## SESIÓN 16 — REBRANDING A "PULSAR" + LOGO EN SIDEBAR (2026-06-21)

El dashboard pasa a llamarse **Pulsar** (enfoque en predicción). Cambios en `app_ernc.py`:

- **Nombre:** "Dashboard ERNC — AES Andes" → **"Pulsar — AES Andes"** en `page_title`,
  `page_icon` (`assets/logo_pulsar.png`) y header principal (`<h1>`).
- **Logo en sidebar:** `assets/logo_pulsar.png` reemplaza el título de texto. Debajo va
  "Creado por **Erick Herrera**". Se eliminó el título "AES Andes ERNC" del top y la firma
  "Dashboard creado por…" del pie del sidebar.

### Keying del logo (importante)
El PNG entregado venía **flatten en RGB con el patrón de transparencia (checkerboard)
horneado como píxeles reales**: fondo 242–249, logo blanco 251–255. Por eso `st.image()`
y los filtros CSS (`brightness/invert/mix-blend-mode`) dejaban un recuadro gris.
**Solución (PIL + numpy en `render_sidebar`):** key por luminancia con corte en **251**
(justo encima del máximo del checkerboard) → `alpha = clip((bright-251)*80)`, color forzado
a blanco puro, reescalado a 320px con LANCZOS, embebido como base64 en `<img>`. Resultado:
fondo 100% transparente, logo blanco nítido sobre el gradiente azul del sidebar.

**Regla:** si se reemplaza el logo, usar un PNG con transparencia real (no flatten). Si trae
checkerboard horneado, ajustar el umbral del key al máximo del fondo (~251 en este archivo).

---

## SESIÓN 17 — SECCIÓN PRINCIPAL, FIXES SOLAR/EÓLICA, CMG, MAPA SATELITAL Y BESS (2026-06-22)

### Sección principal (KPIs) — `components/kpis_generales.py`
- Reemplazados los `st.metric` (con tooltip `?`) por **cards HTML** en grid `kpi-grid`
  (6 columnas → 3 → 2 responsive). Cada card lleva borde-top de color, valor, delta y
  una **nota inline** con la explicación del cálculo + la **última hora** del dato.
- **CMG ahora es un promedio** ("CMG Promedio") de los nodos del SEN **excluyendo
  `P.MONTT_______220`** (otro sistema). El ingreso estimado se calcula sobre ese promedio.
  Se pasó de 7 a 6 cards.
- Eliminado el header "Ultima lectura: HH:MM" (ya está en el sidebar) y el **punto rojo
  suelto** bajo Desvío vs PCP.

### Navegación — `app_ernc.py`
- Botones de sección repartidos en **2 filas** (no apretados), padding mayor,
  `min-height:46px`, `white-space:normal`. Nueva vista **"BESS"** entre Eólica y Forecast.

### Fix métricas Solar y Eólica — `tab_solar.py` / `tab_eolica.py`
- **Desvío vs PCP**: ahora compara gen real y PCP **en la misma hora**
  (`_gen_prog_mismo_hora`). Antes comparaba la última hora de gen contra la última PCP
  (a veces futura) → daba −100% o "—".
- **GHI / Temp / Viento**: eran `if valor else "—"` → con valor 0 mostraban "—"
  (0 es *falsy*). Corregido a `is not None`. De noche GHI muestra "0 W/m²" honestamente.
- Eliminados todos los `?` (help) de los paneles; la explicación quedó en `st.caption`.
- **Shear**: quitado `fill="tozeroy"`+`rangemode="tozero"` (rompía con α negativo),
  rango fijo `[-0.15, 0.65]` y **clip a `[-0.10, 0.60]`** de valores viejos absurdos.
  Los α de −2..+5 eran datos pre-Sesión 14; se corrigen al repoblar meteo.

### Forecast — `tab_forecast.py`
- **Eliminada la línea PCP** (solo llegaba a D+1, engañosa en 7 días). El pronóstico
  ahora es el **modelo físico propio** sobre el forecast Open-Meteo, con nota explicativa.
  Borrada `_cargar_pcp_forecast()`.

### ML Analysis — clustering de eficiencia — `tab_ml.py`
- Scatter rediseñado: **centroides** (X grande por grupo), etiquetas por nivel
  (**Alta/Media/Baja eficiencia** ordenadas por PR, verde/ámbar/rojo), línea PR=1.0,
  leyenda con conteo y `st.caption` con guía de interpretación.

### Meteo & Sistema — `tab_meteo_sistema.py`
- Reordenado: **heatmaps primero** (nubosidad → viento), luego **alertas con 3
  prioridades** (alta/media/baja) con colores, contador-resumen y animación leve
  (`alertaIn` + `pulseAlta` en críticas). Nuevas reglas: recurso eólico bajo, nubosidad
  moderada.

### CMG — `app_ernc.py::_render_tab_cmg`
- **Serie de tiempo primero, tabla después** (con **máx/mín 48h** por nodo).
  Quitados los `?`. Corregido el filtro histórico **UTC→Santiago**. Nuevas **alertas**:
  costo cero (<0.5, vertimiento), CMG alto (>200, oportunidad), desacople (spread>50),
  máximo de ventana. Línea de costo cero en el gráfico.
- **Nota:** la convergencia de nodos tras 21-jun 00:00 **no es bug** — es real (nodos
  convergen sin congestión) + los 6 nodos nuevos solo tienen datos desde el fix Sesión 14.

### Mapa satelital — `components/mapa_ernc.py`
- Vista **"Satelite"** con **MapTiler** (style `hybrid` hospedado). Aparece solo si hay
  `MAPTILER_KEY`. **CRÍTICO:** el `DeckGlJsonChart` de Streamlit exige `map_style` como
  **STRING URL** — un dict de style raster MapLibre revienta con
  `e.mapStyle?.indexOf is not a function`. Por eso se usa la URL hospedada, NO un dict.
- La capa de **nubes OpenWeather NO** puede inyectarse en un style-URL (pydeck no
  renderiza raster dicts ni TileLayers raster). Quedaría para un mapa folium aparte.
  `OPENWEATHER_KEY` ya configurada pero sin uso por esta limitación.
- Eliminado el dict muerto `_ESRI_SAT_STYLE`. Helpers nuevos: `_secret()`,
  `maptiler_disponible()`, `_satelite_style_url()`.

### Secrets nuevas (gitignored: `.env` y `.streamlit/secrets.toml`)
```
MAPTILER_KEY      ← satélite (MapTiler free)
OPENWEATHER_KEY   ← reservada para nubes (pendiente folium)
```
En Streamlit Cloud: agregarlas en Settings → Secrets.

### BESS — sección completa nueva
Los BESS de AES aparecen en gen-real/v3 como **centrales separadas** (`id_central=None`,
`tipo='BESS'`) con llaves `(Inyección)`=descarga y `(Retiro)`=carga, ambas positivas.
**No** se filtran por idCentral → hay que escanear el feed completo.

- **5 BESS confirmados** (`config.py::BESS`, llaves validadas contra la API 21-jun):
  | Código | BESS | Parque | Pmax desc. (MW) |
  |--------|------|--------|-----------------|
  | AS2A_B | Andes Solar IIA | AS2A | 84.0 |
  | AS2B_B | Andes Solar IIB | AS2B | 136.5 |
  | AS3_B  | Andes Solar III | AS3 | 177.0 |
  | AS4_B  | Andes Solar IV | AS4 | 140.0 |
  | BOL_B  | Bolero | BOL | 160.0 |
  | ~~ET1_B~~ | ~~Andes ET1~~ | — | eliminado Sesión 22 (no existe) |
- Convención: `potencia_neta_mw = inyeccion - retiro` (>0 descarga, <0 carga).
  AS3 y BOL tienen 2 llaves de retiro ("de central" + "del sistema") → se suman.
- `utils/cen_api.py::fetch_gen_bess()` (ventana 2 días, scan completo, agrega por
  `(bess, fecha_hora)`). Validado: 254 registros, signos correctos (carga mediodía,
  descarga punta tarde).
- `utils/db.py`: `upsert_generacion_bess()` (on_conflict `bess,fecha_hora`) +
  `query_bess_ultimas_horas()` (try/except → `[]` si la tabla no existe).
- `schema.sql`: tabla `generacion_bess_ernc` + RLS `anon_select` + índice
  `idx_bess_fecha`. **Ejecutado en Supabase (Sesión 17).**
- `Adquisicion_ernc.py`: paso `adquirir_gen_bess()` integrado al cron.
- `components/tab_bess.py`: estado (cargando/descargando/reposo), potencia neta,
  descarga/carga 24h, ciclos eq. (cap. energía = Pmax × 4h asumido), gráfico
  carga/descarga + **SoC estimado** (integración del flujo neto, anclado al mínimo),
  y **arbitraje vs CMG** del nodo del parque (ingreso descarga − costo carga + spread).

### Mapa satelital migrado a folium (post-fix MapTiler)
La vista **Satelite** se migró de pydeck a **`streamlit-folium`** porque pydeck/Streamlit
no puede superponer capas raster (nubes) ni renderizar styles dict (crash
`mapStyle?.indexOf is not a function`). Implementado en
`components/mapa_ernc.py::_render_satelite_folium()`:
- Base **Esri World Imagery** (token-free, no necesita MapTiler) + etiquetas Carto.
- **Nubosidad OWM en vivo** (`OPENWEATHER_KEY`, opacity 0.9 — densidad codificada en el
  tile) + **día/noche** con `folium.plugins.Terminator` (tiempo real).
- `LayerControl` para alternar nubes/etiquetas; markers `CircleMarker` con popup por parque.
- `st_folium(..., returned_objects=[])` para no disparar reruns.
- Satelite es **default** del selector y siempre disponible (ESRI sin key).
- Claro/Detallado siguen en **pydeck** con marcadores en píxeles (`radius_units=pixels`,
  no se agrandan al zoom) y labels escalonados para el complejo Andes Solar.
- Caption con **hora real Santiago** (usa `ZoneInfo("America/Santiago")`, NO offset fijo).
- Dependencias nuevas en `requirements.txt`: `folium`, `streamlit-folium`.
- Eliminado el dict/URL MapTiler muerto. La `MAPTILER_KEY` ya no se usa (queda en secrets
  por si se quiere volver a un style hosted).

### Pendientes Sesión 17
- [ ] **TZ GLOBAL (PRIORITARIO próxima sesión):** reemplazar TODOS los offset fijos `-3`
      por `ZoneInfo("America/Santiago")`. `utils/db.py::_ahora_santiago()` y varios tabs
      usan `timezone(timedelta(hours=-3))`, que en **invierno chileno (UTC-4)** corre las
      ventanas/filtros **1 h** respecto a los timestamps reales de la DB (guardados con
      `TZ_CHILE`=ZoneInfo en adquisición). El mapa YA se corrigió (Sesión 17); falta el resto.
- [ ] Re-correr `Adquisicion_meteo_ernc.py` para repoblar shear acotado y viento en m/s.
- [ ] Capacidad real de energía (MWh) de cada BESS para SoC/ciclos exactos — hoy se
      asume duración 4h (`_HORAS_BESS`). La API CEN no publica MWh.
- [ ] (item 6 usuario) Info técnica del Coordinador para recalcular fórmulas y confirmar
      el nodo CMG real de cada parque.
- [ ] Nubes OWM: confirmar que `OPENWEATHER_KEY` quedó activa (daba 401 al crearse; las
      keys nuevas tardan ~2 h). Si sigue 401, revisar la key.

---

## SESIÓN 18 — PARÁMETROS TÉCNICOS REALES (CARTAS CEN) + PESTAÑA INFOTÉCNICA (2026-06-22)

Erick aportó `parametros_pe_pulsar.xlsx` + `parametros_pfv_pulsar.xlsx` (cartas CEN
y fichas de fabricante). Se ajustaron los cálculos y se agregó una pestaña de referencia.

### Cambios en `config.py`
- **`PMAX_NETA`**: Pmax neta CEN por parque (None donde no hay carta: BOL, MSM).
- **`PMAX_FP`**: Pmax para FACTOR DE PLANTA — neta CEN si existe, si no la config.
  Caso especial **MSM = 67.2 MW** (potencia total instalada, no la config 70.56).
  Totales: `PMAX_FP_TOTAL` (1108), `_SOLAR` (682), `_EOLICA` (426).
- **`TURBINA_PARQUE`**: curva de potencia por parque eólico (cut-in/rated/cut-out +
  fabricante/modelo/n_wtg/rotor/hub). CL: Vestas V150-4.3 (cut-out **24.5**), MSM:
  Nordex N149-4.8. Resto default 3/12/25.
- **`BESS_HORAS`**: duración declarada (AS2B 4.95 h, AS3 3 h, AS4 5 h).
- **`INFOTECNICA`**: ficha consolidada por parque (Pmax bruta/neta, Pmin, SSCC,
  equipos, nota de cálculo, fuente) — solo para la pestaña de referencia.

### Regla de cálculo (FP)
Prioridad AES: **Pmax neta CEN aceptada > potencia neta verificada SSCC > potencia
total instalada documentada**. Se cambió el FP a `PMAX_FP` en `kpis_generales.py`
(totales y notas), `tab_solar.py`, `tab_eolica.py` (métrica ahora "Pmax neta CEN"),
`tab_estadisticas.py`, `utils/insights.py`, `utils/pdf_report.py` y las tablas/botones
del sidebar en `app_ernc.py`. El **modelo FV** sigue usando `PMAX` (bruta); el **modelo
eólico** usa `PMAX_FP` (neta) + la curva `TURBINA_PARQUE` en `utils/openmeteo_api.py`.
**Requiere re-correr `Adquisicion_meteo_ernc.py`** para repoblar `p_eolica_estimada_mw`.

### Nueva pestaña Infotécnica (`components/tab_infotecnica.py`)
Vista `"Infotecnica"` (última en `VISTAS`). Tablas: potencias+SSCC FV, potencias+SSCC
eólica, curva de potencia eólica por parque, BESS (energía = Pmax×horas), y fichas
expandibles por parque con equipos y fuentes. Solo lectura, sin Plotly.

---

## SESIÓN 19 — UX MAYOR: ALARMAS, NAV POR CATEGORÍAS, BESS/ML/ESTADÍSTICAS (2026-06-22)

1. **Insights → Alarmas** (`tab_insights.py` + `utils/insights.py`): sección renombrada.
   `Insight` ahora tiene `timestamp`; `evaluar_insights(..., ultima_hora)` lo estampa.
   Cards muestran **fecha/hora** del evento. Semáforo verde/amarillo/rojo (3 tarjetas de
   conteo) + filtros por **severidad** y categoría. Subtab meteo: columna **Fecha/hora**
   por parque + última lectura. Dispatch pasa `ultima_hora`.
2. **Mapa & Resumen** (`app_ernc._render_tab_resumen`): mapa a **ancho completo**; tabla
   de estado **debajo** con Pmax neta, FP, **% capacidad (ProgressColumn)**, PCP y Desvío.
   Serie 24h ahora **apilada Solar/Eólica** + línea PCP ámbar.
3. **BESS** (`tab_bess.py`): métricas extra (máx desc/carga, horas desc/carga, energía neta),
   **CSV** de la serie del BESS, y **tabla resumen de los 6 BESS** (estado, carga/descarga,
   horas, ciclos) con CSV. Nueva subsección ML **"BESS — operación"** en `tab_ml.py`
   (perfil horario, dispersión neta vs CMG, correlación de arbitraje, importancia hora/CMG).
4. **Estadísticas** (`tab_estadisticas.py`): 2ª fila de KPIs (FP portfolio, mejor parque,
   precio medio capturado, **CO₂ evitado**), cumplimiento PCP, y **CSV** de detalle.
5. **ML Analysis** (`tab_ml.py`): **fix R² absurdo** — el forecast de generación usa
   `train_test_split` aleatorio (la gen depende del clima concurrente, no de su pasado),
   con `np.clip` a [0,Pmax]; el backtest cronológico queda solo para visualización.
   Expanders de **metodología/fundamento teórico** en las 4 subsecciones. Eficiencia usa
   `PMAX_FP`.
6. **Sidebar/Nav** (`app_ernc.py`): logo **más grande (210px) y más arriba** (padding
   reducido + recorte de `stSidebarUserContent`). Nueva **card KPI BESS** (estado + % de
   uso, neta) en `kpis_generales.py` (grid 4-col responsive, 8 cards). Navegación en **2
   niveles**: `st.segmented_control` de **categorías** (Operación / Análisis / Alarmas &
   Mercado / Referencia) → botones de vista; auto-curado al saltar desde el sidebar.
7. **Tooltips `?` eliminados** de TODO el software (`help=` quitado en forecast, ml,
   estadísticas, meteo_sistema, solar, eólica).

---

## SESIÓN 20 — FIXES NAVEGACIÓN + MAPA NUBOSIDAD CONFIGURABLE (2026-06-22)

### Navegación 2 niveles — fixes (`app_ernc.py`)
- **Crash** `StreamlitAPIException`: el handler de los botones de vista escribía
  `st.session_state["nav_cat"]` DESPUÉS de instanciar el widget con esa key → prohibido.
  Se eliminó esa escritura.
- **Las categorías no cambiaban**: la lógica forzaba `nav_cat` a la categoría de la
  vista activa en cada rerun, revirtiendo la elección del usuario. Ahora solo se fuerza
  con el flag `_force_cat` (lo setean los botones del sidebar al saltar a Solar/Eólica);
  el desplegable respeta la selección del usuario. **Regla:** para sincronizar la
  categoría desde el sidebar, setear `st.session_state["_force_cat"]` ANTES del rerun;
  nunca escribir `nav_cat` tras crear el `selectbox`.
- Categoría = **`st.selectbox` real (menú desplegable)** centrado (`st.columns([1,2,1])`),
  con CSS propio (borde azul AES, gradiente, sombra al hover, ícono azul). Botones de
  vista centrados (relleno de columnas cuando la categoría tiene <4 vistas).
- Comportamiento: elegir categoría muestra sus botones; el contenido carga al hacer clic
  en una vista (menú de 2 niveles).

### KPIs — card BESS (`kpis_generales.py`)
Nueva card "BESS — Almacenamiento" (estado, % de uso sobre Pmax descarga, potencia neta);
helper `_agregado_bess(bess_rows)`. Grid pasó a `repeat(4,1fr)` responsive (8 cards).

### Mapa satelital (`components/mapa_ernc.py`)
- **Vista por defecto en región de Antofagasta**: `center=[-23.8,-69.1]`, `zoom=7`
  (antes Chile completo) para observar nubosidad del complejo solar norte.
- **Nubosidad configurable por el usuario**: `st.selectbox` "Paleta de nubosidad" con
  presets (Suave/Normal/Densa/Alto contraste/Azulada). **IMPORTANTE:** el endpoint OWM
  **Weather Maps 2.0** (`maps.openweathermap.org/maps/2.0/weather/CL/...` con `palette=`)
  es **de pago** → con la key gratuita devuelve tiles en blanco. Se usa el tile gratuito
  **`clouds_new`** (`tile.openweathermap.org/map/clouds_new/...`); la intensidad/color se
  logra con `opacity` + `refuerzo` (apilar la capa N veces) + **filtros CSS**
  (`contrast/brightness/hue-rotate`) aplicados por `className` e inyectados con
  `m.get_root().header.add_child(folium.Element(<style>))`. Helpers `_build_cloud_layers`,
  `_css_filtros_nubes`, dicts `_CLOUD_PRESETS`/`_CLOUD_FILTROS`. Default "Densa".

---

## SESIÓN 21 — MENÚ DESPLEGABLE TIPO ESCRITORIO (REPLICADO DEL CTM) (2026-06-22)

Se reemplazó la navegación de 2 niveles (selectbox de categoría → botones de vista,
Sesión 19/20) por el **patrón de barra de menú de escritorio** que funcionó bien en el
dashboard CTM (`dashboard_api/app.py`).

### Cambio en `app_ernc.py::_navegacion()`
- Cada **categoría** de `CATEGORIAS` es ahora un `st.popover` a todo el ancho, en una
  fila (`st.columns(len(CATEGORIAS))`). Al hacer clic, el popover **se despliega hacia
  abajo** mostrando las vistas de esa categoría como botones (`type="primary"` = vista
  activa). La categoría activa muestra inline la vista elegida: `f"{cat}  ·  {vista}"`.
- Se eliminó el `st.selectbox` de categoría y la lógica de `nav_cat` / `_force_cat`
  (la categoría activa se **deriva** de `vista`, no se almacena). El handler consume y
  limpia `nav_cat`/`_force_cat` heredados. `_categoria_de()` queda sin uso (inocuo).
- El sidebar sigue saltando a Solar/Eólica escribiendo solo `st.session_state["vista"]`.

### CSS (en `get_css()`)
Se cambió el bloque del selectbox por el del popover:
```css
[data-testid="stPopover"] > div > button { width:100%; min-height:48px; font-weight:700;
  background:linear-gradient(180deg,#FFFFFF,#F3F5FF); border:1.6px solid #C7CDF5;
  border-radius:10px; color:#2530B0; justify-content:center; }
[data-testid="stPopover"] > div > button[aria-expanded="true"] {
  background:linear-gradient(135deg,#3B4CE8,#2530B0); color:#fff; border-color:#2530B0; }
```

**Ventaja:** se ve como app de escritorio, ocupa todo el ancho, y al renderizar solo la
vista activa evita el bug de Plotly width=0 dentro de `st.tabs`. **Regla:** mantener este
patrón sincronizado con el CTM si se rediseña la navegación en cualquiera de los dos.

---

## SESIÓN 22 — NUEVOS ENDPOINTS CEN (CMG FUTURO + RESPALDO 8B) + LIMPIEZA BESS (2026-06-23)

Tras revisar el catálogo completo de la API CEN (`resumen_endpoints_adquisicion_coordinador.md`,
95 SIP + 44 Operaciones) y tomar como referencia las adquisiciones recién hechas en el
dashboard CTM (`../dashboard_api/Adquisicion.py`), se integraron 2 endpoints nuevos.

### CMG programado PCP (CMG futuro) — NUEVO
- Endpoint: `/cmg-programado-pcp/v4/findByDate` (SIP). **1-indexado** (page=0 da 502),
  NO filtra por barra → se pagina todo con **limit=4000** (las 8 barras 220 kV caben en
  page 1) y se filtra local por `llave_cmg`. Se conserva el programa más reciente
  (mayor `fecha_programa`) por `(nodo, fecha_hora)`.
- `config.py::CMG_PROG_LLAVE_A_NODO`: mapea `llave_cmg` (Crucero220, Charrua220, …) a los
  MISMOS nombres de nodo del feed S3 (`CRUCERO_______220`, …) → el CMG futuro slotea con
  el online sin tocar el resto del dashboard.
- `utils/cen_api.py::fetch_cmg_programado()`, `utils/db.py::upsert_cmg_programado()` +
  `query_cmg_programado(horas)` (try/except → `[]` si la tabla no existe).
- `schema.sql`: tabla `cmg_programado_ernc` (nodo, cmg_usd_mwh, fecha_hora, fecha_programa)
  + RLS `anon_select` + índice. **PENDIENTE: ejecutar este bloque en Supabase SQL Editor.**
- `Adquisicion_ernc.py`: paso `adquirir_cmg_programado()` integrado al cron.
- Validado contra API: **968 registros, los 8 nodos × 121 h**.

### CMG online 8 barras — RESPALDO del feed S3
- Endpoint: `/costos-marginales-online-8b/v4/findAll` (SIP). Devuelve `{fecha, barras:[{nombre,
  valores:[{fecha(epoch ms), valor}]}]}` — últimas ~24 h horarias de las 8 barras.
- `config.py::CMG_8B_NOMBRE_A_NODO` mapea "Crucero 220 KV" → `CRUCERO_______220`.
- `fetch_cmg_online_8b()` convierte epoch ms a hora Santiago y escribe en **cmg_ernc**
  (mismos nodos). Se usa como **fallback en `adquirir_cmg()`** cuando el feed S3 falla o
  está en mantenimiento. Validado: 138 registros.

### `pronostico-erv` — DESCARTADO (sin datos)
`/pronostico-erv/v4/findByDate` responde **200 pero `data:[]` / `totalPages:0`** en todas
las ventanas probadas (hoy, ±2d, ±5d) → no hay datos publicados en nuestro plan SIP. Igual
que demanda real (Sesión 15). No se implementó.

### Limpieza BESS — ET1_B eliminado
El BESS **Andes ET1 (`ET1_B`, AS1, 14.08 MW) no existe** → eliminado de `config.py::BESS` y
`BESS_HORAS` (quedan **5 BESS**), de los textos "6 BESS" en `kpis_generales.py` y
`tab_bess.py`, y de la tabla en CLAUDE.md. **Borradas 68 filas** de `generacion_bess_ernc`
en Supabase. `BESS_LLAVE_MAP` se regenera solo → ya no mapea las llaves ET1.

### Pendiente Sesión 22
- [ ] Ejecutar el bloque `cmg_programado_ernc` de `schema.sql` en Supabase (antes de que el
      cron escriba). Sin la tabla, `adquirir_cmg_programado` fallará en el upsert.
- [ ] (Opcional) Consumir `query_cmg_programado()` en el tab CMG / arbitraje BESS para
      mostrar el CMG futuro junto al online.

---

## SESIÓN 23 — NASA POWER, FIXES MAPA, ARBITRAJE BESS Y UX (2026-06-23)

Continuación de la Sesión 22 (CMG programado + 8b). Se cerró el ciclo de valor de los
endpoints nuevos y se pulió UX en mapa, ML, forecast y estadísticas.

### NASA POWER — 2ª fuente solar (validación de GHI)
- `utils/nasapower_api.py`: GHI/temp/viento horario satelital (gratis, sin key). Rezago
  ~3-7 días → **validación, no forecast**. Se guarda en `meteo_ernc` con `fuente='nasa-power'`.
  **OJO entorno:** el reloj simulado (2026) está en el futuro de la data real de NASA → devuelve
  `-999`; el parseo se validó con fechas 2024 reales. En producción real poblará con su rezago.
- `Adquisicion_nasa_ernc.py`: backfill 10 días. En el workflow corre **1 vez/día (12 UTC)**
  vía guard `if [ "$(date -u +%H)" = "12" ]` (NASA actualiza a diario, no cada hora).
- `tab_ml.py::"Validación recurso (NASA)"`: compara GHI Open-Meteo vs NASA (sesgo/RMSE/
  correlación + serie + dispersión) por parque solar.
- **Sidebar:** fila "NASA POWER" en Fuentes de datos (umbral 192h por el rezago). NO cuenta
  para el semáforo global de conexión (es validación, no tiempo real). `query_ultimas_
  actualizaciones` devuelve `nasa`.
- Descartado **AccuWeather** (free tier 50/día insuficiente) y **OpenWeather Solar** (de pago).
  `pronostico-erv` también descartado (Sesión 22): 200 pero `data:[]`.

### Mapa satelital (`components/mapa_ernc.py`)
- **Nubosidad**: probamos imagen interpolada Open-Meteo (se veía tenue) y rectángulos (feos).
  **Final: tile OWM `clouds_new` (textura real) + selector de COLOR** (Natural/Azul/Roja/Violeta)
  vía filtros CSS (`sepia+saturate+hue-rotate` por className). `_build_cloud_layers` +
  `_css_filtros_nubes` restaurados. Eliminadas `_cloud_grid`/`_cloud_image`/`_cloud_color`.
- **Viento**: nuevo `_viento_actual_parques()` trae viento ACTUAL (vel+dir) de **los 11 parques**
  en 1 llamada Open-Meteo (antes leía `wind_dir_80m` de meteo_ernc → solo salía en eólicas, porque
  los solares no guardan dirección). Flecha grande (glifo ➜, rotación = rumbo−90) con **velocidad
  m/s rotulada encima**, color por intensidad.
- **Auto-refresh del mapa cada 5 min** (`st_autorefresh` en `render_mapa`, TTL caché 300s).

### CMG (tab CMG, `app_ernc.py`)
- Serie de tiempo: TODOS los nodos con **misma línea punteada** (antes CRUCERO/CHARRUA eran
  sólidas/gruesas).
- Nueva sección **"CMG programado PCP"** (futuro) con marca de "ahora" (pasado vs proyectado).

### Arbitraje BESS (ML, `tab_ml.py`)
- **Fix "Sin CMG suficiente":** el online S3 (`cmg_ernc`) es muy escaso (≈41 filas/20d, 0 solape
  con horas BESS) → ahora se combina con el **CMG programado** (denso, horario) como fuente del
  nodo. `_dataset_bess` usa `cmg_online.combine_first(cmg_prog)`. Validado 64/64 filas con CMG.
- Nueva **recomendación de arbitraje a futuro** (`_recomendacion_arbitraje`): ventanas óptimas de
  carga/descarga según CMG programado próximas horas + margen de ciclo estimado.
- Los 2 gráficos BESS (scatter neta–CMG, importancia hora vs CMG) ahora con **explicación clara**.

### Meteo & Sistema — heatmap nubosidad
- Fix "todo celeste": escala **fija 0–100%** (`zmin/zmax`). El norte solar es 0% real (desierto)
  → antes Plotly auto-escalaba a −0.4..0.4. Viento fijo 0–15 m/s.

### Solar / Eólica (`tab_solar.py`, `tab_eolica.py`)
- **Modelo FV/eólico**: línea **sólida** (no punteada) en la serie + swatch acorde.
- **Leyendas reescritas** en lenguaje simple ("lo que el parque inyectó de verdad", "lo que
  debería generar según el sol/viento", etc.).

### Forecast 7d (`tab_forecast.py`)
- Checkbox **"Comparar con modelo ML"**: RandomForest meteo→gen real del parque (45d) superpuesto
  al modelo físico (`_ml_forecast_parque`, features según tecnología). NASA no aplica (histórico).

### Estadísticas (`tab_estadisticas.py`)
- Nueva sección **"Almacenamiento BESS"**: descarga/carga total, energía neta, round-trip
  aparente, ciclos eq., barras carga/descarga por BESS, tabla + CSV. `render_tab_estadisticas`
  recibe `bess_rows`.

### Limpieza
- BESS **ET1_B eliminado** (Sesión 22): no existe → fuera de config, textos "6→5 BESS",
  68 filas borradas en DB.

### Pendiente Sesión 23
- [ ] Esperar a que el cron pueble `nasa-power` en producción (fecha real) para que la sección
      de validación NASA muestre datos.
- [ ] TZ global (`ZoneInfo` vs offset −3) sigue pendiente desde Sesión 17.

---

## SESIÓN 24 — POBLADO NASA POWER + FIX DESFASE HORARIO LST (2026-06-24)

La sección **ML → Validación recurso (NASA)** salía vacía. Se pobló con datos reales y se
corrigió un bug de timezone en la fuente NASA.

### Por qué salía vacía (reloj del entorno adelantado)
El reloj del entorno está en **2026-06-24**, pero NASA POWER tiene rezago real de **~85 días**
(no los 3-7 que asumía la doc) → su data real más reciente llega solo a **2026-03-30**. Dos
bloqueos para el cruce Open-Meteo vs NASA:
1. La sección miraba **30 días** hacia atrás desde junio → nunca alcanzaba marzo.
2. El Open-Meteo en DB es de junio-julio (ventana móvil 5 días) → **cero solape** con NASA. Y el
   endpoint *forecast* de Open-Meteo devuelve **GHI `None`** para fechas tan atrás.

### Solución de poblado (backfill puntual, marzo 2026)
- **NASA:** `fetch_nasa_meteo(dias=120)` → trae su data real (filtra `-999`). ~864 reg/parque solar.
- **Open-Meteo histórico:** se usó el **Archive API (ERA5)** `archive-api.open-meteo.com/v1/archive`
  (`shortwave_radiation,temperature_2m,wind_speed_10m`, `timezone=America/Santiago`, `wind_speed_unit=ms`).
  El *forecast* NO sirve radiación histórica; el *archive* sí (límite: desde ~2026-03-23).
- Ambos en `meteo_ernc` con `fuente` correspondiente → la validación cruza por `fecha_hora`.
- **Dedup** `(parque,fecha_hora,fuente)` obligatorio antes del upsert (Open-Meteo trae duplicados
  por DST, si no → error `ON CONFLICT DO UPDATE cannot affect row a second time`).

### Cambio de código — ventana de la sección
`components/tab_ml.py::_meteo_por_fuente` default **`dias=30 → 120`** para que el comparador
alcance la data de NASA en este entorno (en prod real es inocuo: solo trae más historia).

### BUG CORREGIDO — desfase horario LST (≈2 h) en NASA POWER
`utils/nasapower_api.py` pedía `time-standard: LST` (**hora solar local**, basada en longitud) y
guardaba la hora cruda como si fuera civil. Open-Meteo usa hora civil `America/Santiago` → la serie
NASA quedaba **~2 h corrida** (pico NASA 11h vs Open-Meteo 13h). Esto inflaba el RMSE y partía la
nube de dispersión en dos bandas.
- **Fix:** pedir `time-standard: **UTC**` y convertir con
  `datetime.strptime(k,"%Y%m%d%H").replace(tzinfo=timezone.utc).astimezone(TZ_CHILE)`.
- Aplica también al cron diario futuro, no solo al backfill.
- **Impacto (AS1):** RMSE **339 → 32 W/m²**, correlación **0.64 → 0.997**, sesgo −9 W/m² (real,
  diferencia genuina modelo vs satélite). BOL: RMSE 18, corr 0.999.
- **Regla:** NASA POWER siempre en UTC + `astimezone(TZ_CHILE)`. NUNCA `time-standard: LST` para
  cruzar con fuentes en hora civil.

### Pendiente Sesión 24
- [ ] En producción con reloj real, el cron diario `Adquisicion_nasa_ernc.py` poblará solo (rezago
      de días) — el backfill de marzo fue puntual para este entorno simulado.
- [ ] (Opcional) Anclar la ventana del comparador a la última fecha de NASA en vez del fijo 120 d.

---

## SESIÓN 25 — TRACKERS FV, LOGIN, ML FORECAST, BESS SIDEBAR, PDF/RECOMENDACIONES, WORKFLOW 30 MIN (2026-06-24)

Lote grande de 9 ítems pedidos por Erick. Decisiones de modelado confirmadas con él:
trackers = ganancia tracking 1-eje + **derate disponibilidad 0.80**; **stow a 16 m/s**.

### 1. Password gate (`app_ernc.py`)
- `_password_correcto()` al inicio de `main()` (antes de cargar datos). Contraseña
  compartida: `st.secrets["APP_PASSWORD"]` → `os.environ` → fallback **`"carbon"`**.
- Pantalla de login centrada con logo. **Logo keyed:** `_logo_keyed_html(color, width)` —
  reusa la lógica de Sesión 16 (key por luminancia, corte 251 sobre el checkerboard
  horneado) pero recolorea a **negro azulado** `(26,31,54)` y lo centra. En el sidebar el
  logo sigue blanco.
- En Streamlit Cloud: agregar `APP_PASSWORD` en Settings → Secrets (opcional).

### 2-3. Modelo FV con trackers + viento solar (`config.py`, `utils/calculos.py`, `utils/openmeteo_api.py`, `components/tab_solar.py`)
- `config.py`: `TRACKER_GAIN=1.18`, `TRACKER_AVAIL=0.80`, `TRACKER_STOW_WIND_MS=16.0`,
  `TRACKER_POA_MAX=1100`. Se agregó `windgusts_10m` a `OPENMETEO_VARS_SOLAR`.
- `calculos.py`: **nuevo** `poa_tracker(gti_fijo, ghi, wind, gusts)` — POA de seguidores
  1-eje = `GTI_fijo × 1.18`, acotado a `[GHI, 1100]`; **si viento/ráfaga ≥ 16 m/s → POA=GHI**
  (stow horizontal). `calcular_potencia_fv_estimada(...)` ahora recibe el POA y aplica el
  factor `availability=0.80`. El `gti` que entra ya debe ser POA.
- `openmeteo_api.py`: el bloque Solar calcula `poa = poa_tracker(...)` y guarda
  `p_fv_estimada_mw = calcular_potencia_fv_estimada(poa, tc, pmax)`. **Requiere re-correr
  `Adquisicion_meteo_ernc.py`** (ya hecho en la sesión; el cron lo mantiene).
- `tab_solar.py`: métrica **"Viento 10m"** + ráfagas + **aviso de stow** cuando viento/ráfaga
  ≥ 16 m/s (paneles horizontales). Select amplía a `wind_speed_10m,wind_gusts_10m`.
- Todos los consumidores leen la columna `p_fv_estimada_mw` ya almacenada → solo cambia el
  punto de cálculo (openmeteo_api).

### 4. ML en Forecast 7d (`components/tab_forecast.py`)
- `_ml_forecast_parque` ahora devuelve **(df, métricas)** con R²/MAE de holdout 80/20.
- **Nuevo** `_ml_portfolio_total()`: suma el ML de los 11 parques → banda data-driven.
- Checkbox "Superponer pronóstico ML del portfolio" + **KPI "Total ML 7d"** (delta vs físico).
- En el detalle por parque: 3 métricas (R², MAE, horas) + nota de confiabilidad.

### 5. BESS en el sidebar (`app_ernc.py::render_sidebar`)
- Nuevo parámetro `bess_rows`. Sección "BESS · Almacenamiento" con botones por BESS y estado
  inline (▲ descarga / ▼ carga / reposo). Click → vista "BESS".

### 6-7. Referencia: PDF + Recomendaciones (`utils/pdf_report.py`, `utils/recomendaciones.py`, `app_ernc.py`)
- `CATEGORIAS["Referencia"] = ["Recomendaciones", "Reportes", "Infotecnica"]`. El botón PDF
  **se movió del sidebar** a Referencia → Reportes.
- **`utils/recomendaciones.py` (nuevo):** `generar_recomendaciones(...)` → lista de
  `Recomendacion(prioridad, horizonte, titulo, detalle, categoria)`. Reglas: CMG muy bajo/alto,
  BESS vs precio, desvíos >±25%, limitaciones persistentes, buen FP global.
- **PDF reescrito:** paleta AES, **sin emojis** (antes tenía ⚡🔴…), secciones: portada,
  resumen ejecutivo, estado Solar/Eólica, **tabla BESS**, **recomendaciones**, alarmas.
  Nueva firma con `bess_rows`, `recomendaciones`, `cmg_promedio`.
- `app_ernc.py`: helper `cmg_promedio_sen()` (excl. P.MONTT). Vista Recomendaciones con cards
  coloreadas por prioridad. Vista Reportes con botón generar + descarga.

### 8. Workflow de potencia cada 30 min (`Adquisicion_potencia_ernc.py`, `.github/workflows/potencia_ernc.yml`)
- Script ligero que solo corre **gen-real + BESS** (reusa funciones de `Adquisicion_ernc.py`).
  Cron `25,55 * * * *`, timeout 15 min, `concurrency` para no solaparse. **No usa CEN_OPS_KEY.**
  Bajó el lag de la generación de ~5-6 h a ~real (corre 2×/h además del horario completo).

### Fixes del cron (CEN_OPS_KEY opcional) — 2 bugs encadenados
El workflow de 30 min no define `CEN_OPS_KEY` (solo la usa SSCC, plan Operaciones):
1. `Adquisicion_ernc.py`: el chequeo de env estaba a **nivel de módulo** → `sys.exit(1)` al
   importarlo. Movido a `_verificar_entorno()` llamado desde `main()`.
2. `utils/cen_api.py::_get_keys`: leía `os.environ["CEN_OPS_KEY"]` con corchetes → `KeyError`
   en cada llamada gen-real/BESS. Ahora `os.environ.get("CEN_OPS_KEY", "")`.
- **Regla:** `CEN_OPS_KEY` es OPCIONAL; solo SSCC la necesita. Cualquier script SIP-only
  (gen-real, BESS, PCP, CMG, limitaciones) debe correr sin ella.

### Viento del mapa = tiempo real (consulta de Erick)
`mapa_ernc._viento_actual_parques()` usa el endpoint **`current`** de Open-Meteo (nowcast del
modelo, ~15 min), caché 5 min + auto-refresh 5 min. Es viento **modelado** (no medido por
SCADA/anemómetro del parque). Independiente de la adquisición CEN/DB.

### Pendiente Sesión 25
- [ ] (Opcional) Aclarar en tooltip del mapa que el viento es "modelo/pronóstico", no medición.
- [ ] En Streamlit Cloud: agregar `APP_PASSWORD` si se quiere cambiar de `carbon`.
- [ ] El subdominio `*.streamlit.app` se puede personalizar (Settings → General). Si se cambia,
      actualizar el `curl` keep-alive en `adquisicion_ernc.yml`.

---

*Actualizado 2026-06-24 — Sesiones 1–25.*
*Stack: Streamlit + folium/pydeck + supabase-py + GitHub Actions + Open-Meteo + API CEN + NASA POWER*
