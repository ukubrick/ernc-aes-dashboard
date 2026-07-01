# CLAUDE.md — Dashboard ERNC AES Andes
> Contexto completo para Claude Code. Leer al inicio de cada sesión.
> Autor: Erick Herrera — AES Andes, Antofagasta, Chile.
> Última actualización: 2026-07-01 (Sesión 33 — v2.9.2).
>
> REGLA DE MANTENIMIENTO: la cabecera (todo lo anterior al historial de sesiones) es la
> ÚNICA fuente de verdad del estado actual; `config.py` manda sobre este markdown.
> Las sesiones son historia inmutable. Al cerrar cada sesión, actualizar la cabecera
> ADEMÁS de agregar el log de sesión.

---

## DESCRIPCIÓN DEL PROYECTO

Dashboard operacional **"Pulsar"** (v2.9.2) para **12 parques de energías renovables (ERNC) de AES Andes** en Chile:
- 7 parques solares FV (norte, Atacama/Antofagasta) — incluye PFV Cristales (EN_REVISION, gen=0)
- 5 parques eólicos (sur, Biobío/Coquimbo)
- 7 BESS asociados (incluye SAE Cristales 370 MW y BESS Arenales 315 MW)

**Proyecto independiente** del dashboard CTM Mejillones (térmicas ANG/CCR). Hereda el stack y patrones de ese proyecto pero con visualización significativamente más rica.

**Estado actual:** En producción en Streamlit Cloud. GitHub Actions corre cada hora (:10 UTC) para adquisición CEN y meteo Open-Meteo.

---

## URLS DE PRODUCCIÓN

- **GitHub:** https://github.com/ukubrick/ernc-aes-dashboard (público — necesario para Streamlit Cloud free tier)
- **Supabase:** https://ozeubcqoxsihmmfpswoa.supabase.co (proyecto `ernc-aes`)
- **Streamlit Cloud:** share.streamlit.io (cuenta ukubrick, main file: app_ernc.py)

---

## REGLAS APRENDIDAS — NO VIOLAR

Destiladas de bugs reales (referencia SNN = sesión en docs/sesiones.md):

1. **Cache Streamlit:** una función `@st.cache_data` NUNCA debe emitir elementos de
   Streamlit (progress, spinner) ni vía closure → `CacheReplayClosureError` en cache hit. (S33)
2. **Plotly + st.tabs:** `st.tabs` renderiza paneles ocultos con `display:none` → Plotly mide
   width=0 y el gráfico queda comprimido. Renderizar SOLO la vista activa (botones + session_state);
   nunca `st.plotly_chart` dentro de un tab inactivo. (S13)
3. **st.plotly_chart:** SIEMPRE `key=` único explícito (incluir el parque si depende de un
   selector) → evita StreamlitDuplicateElementId. (S8)
4. **Timezone:** `fecha_hora` en DB está en hora Santiago. NUNCA filtrar con
   `datetime.now(timezone.utc)` ni offset fijo −3 → usar `_ahora_santiago()` de `utils/db.py`
   (ZoneInfo, respeta DST). (S8/S27)
5. **PostgREST trunca a 1000 filas por request.** Toda query que pueda superar 1000 filas DEBE
   paginar con `.range()`; `.limit(N)` NO sube el tope del servidor. (S28/S29)
6. **RLS Supabase:** el anon key sin política `SELECT` retorna `[]` SILENCIOSAMENTE. Toda tabla
   nueva necesita su `CREATE POLICY anon_select` antes de que el dashboard la consulte. (S8)
7. **Hora CEN:** gen-real v3 usa hora 1-24 (`hora - 1` para 0-based); PCP/PID v4 ya vienen
   0-based, NO convertir. (S1/S2)
8. **Paginación CEN v4:** las respuestas traen `totalPages` (NO `total`) — cortar el loop con
   `page >= totalPages`. PCP/PID/demanda NO filtran por idCentral en servidor → paginar todo y
   filtrar local; deduplicar `(parque, fecha_hora, fuente)` antes del upsert. (S10/S15)
9. **CMG S3:** requiere header `Referer: https://www.coordinador.cl/`; hora sin segundos →
   agregar `:00`. Fallback: endpoint `costos-marginales-online-8b`. (S2/S22)
10. **Limitaciones:** `correlativo` llega como float → `int(float(v))`; normalizar tildes en el
    match de nombres. (S2/S15)
11. **SSCC (Operaciones):** respuesta en `content` (no `data`), campos camelCase, `pageSize=-1`
    trae todo. `CEN_OPS_KEY` es OPCIONAL — solo SSCC la usa; scripts SIP-only deben correr sin
    ella (`os.environ.get`, no corchetes). (S2/S25)
12. **st.metric:** el label se trunca con "…" → la hora del dato va en `st.caption` debajo,
    no en el label. (S31)
13. **Parques sin PCP:** `LLAVES_GEN_PROG[cod] = []` para no romper el loop de adquisición
    (patrón Cristales). (S32)
14. **Umbral de stow es POR PARQUE:** usar `stow_umbral(parque)` (Andes 11.15, Bolero 12.5,
    default 16 m/s) — nunca hardcodear 16. (S33)
15. **Rezago de fuentes:** gen-real CEN llega con ~4-5 h de rezago; meteo Open-Meteo es ~actual;
    NASA POWER ~85 días. No comparar como simultáneos; mostrar la hora del dato. (S24/S26/S31)
16. **NASA POWER:** pedir `time-standard: UTC` y convertir a Santiago — NUNCA LST (desfase ~2 h). (S24)
17. **Open-Meteo:** pedir viento con `wind_speed_unit: "ms"` (default km/h). El nivel 80m puede
    venir corrupto por celda → `interpolar_viento_100m` valida el bracket físico [v10, v120]. (S14/S29)
18. **Navegación Streamlit:** no escribir en `session_state[key]` de un widget vivo; para forzar
    estado usar keys one-shot consumidas con `pop()` (`_sync_parque`, `_force_bess`). (S12/S13/S20)
19. **f-strings:** sin backslash dentro (Python < 3.12) — extraer a variable.
20. **Sin emojis** en componentes; fondo nunca blanco puro; cards #FFFFFF sobre #F5F7FA.
21. **PCP y PID comparten tabla** (`generacion_programada_ernc`) — separar SIEMPRE por `fuente`
    antes de graficar/sumar para no duplicar. (S27)

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

# TIMEZONE EN QUERIES: los fecha_hora en DB están en hora Santiago.
# NUNCA usar datetime.now(timezone.utc) ni offset fijo -3 para filtrar.
# Usar _ahora_santiago() de utils/db.py (ZoneInfo("America/Santiago"), respeta DST — S27).

# st.plotly_chart: SIEMPRE agregar key= único explícito para evitar
# StreamlitDuplicateElementId cuando hay múltiples gráficos en tabs/columnas.

# SECRETOS: NUNCA escribir valores reales de keys/tokens/passwords en CLAUDE.md ni en
# ningún archivo commiteado (el repo es PÚBLICO). Solo nombre de variable + dónde vive
# (.env local / GitHub Actions Secrets / Streamlit Cloud Secrets). El historial de git
# ya fue purgado una vez (2026-07-01) — no reintroducir.
```

---

## STACK TECNOLÓGICO

```
Frontend:        Streamlit (Python), tema claro, paleta AES
Mapa:            folium + streamlit-folium, SOLO satelital (Esri World Imagery + nubes OWM) — pydeck eliminado (S26)
Gráficos:        Plotly (template plotly_white, paleta AES)
Base de datos:   Supabase (REST API via supabase-py — NO psycopg2 directo)
Adquisición:     Python + GitHub Actions (cron horario, minuto :10 UTC)
Meteorología:    Open-Meteo (gratuita, sin key, resolución horaria, forecast 7d)
API energía:     CEN (SIPUB + Operaciones)
CMG:             JSON S3 público del Coordinador Eléctrico Nacional
Exportación:     ReportLab (PDF, in-memory BytesIO)
ML/Optimización: scikit-learn + LightGBM (forecast probabilístico) + PuLP (optimizador BESS)
Validación:      NASA POWER (GHI satelital, rezago ~85 días)
Autorefresh:     streamlit-autorefresh (cada 3.600.000 ms)
```

### Por qué supabase-py y NO psycopg2
La conexión TCP directa a Supabase (puerto 5432 y 6543) falla desde redes locales con restricciones de egress (IPv6 / firewall). La REST API de Supabase (HTTPS puerto 443) siempre funciona. Se usa `supabase-py >= 2.0.0`.

---

## CREDENCIALES Y VARIABLES DE ENTORNO

```env
# API CEN — valores reales SOLO en .env local y GitHub Actions Secrets (NUNCA en archivos commiteados)
CEN_USER_KEY=<ver .env / GitHub Secrets>    # SIP (plan público)
CEN_OPS_KEY=<ver .env / GitHub Secrets>     # Operaciones

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
├── CLAUDE.md                        ← este archivo
├── .env / .env.example              ← credenciales locales (gitignored) / plantilla
├── config.py                        ← TODAS las constantes del proyecto (parques, BESS, umbrales)
├── schema.sql                       ← esquema Supabase (ejecutado)
├── requirements.txt
├── app_ernc.py                      ← app Streamlit principal (login, sidebar, navegación, CSS, vistas Resumen/CMG)
├── Adquisicion_ernc.py              ← cron horario: gen-real, PCP, BESS, CMG (+8b), CMG prog, limitaciones, SSCC
├── Adquisicion_meteo_ernc.py        ← cron horario: meteo Open-Meteo + calculados
├── Adquisicion_potencia_ernc.py     ← cron :25/:55: solo gen-real + BESS (baja lag)
├── Adquisicion_pid_ernc.py          ← cron :40: gen programada PID + demanda PID
├── Adquisicion_nasa_ernc.py         ← 1×/día 12 UTC: NASA POWER (validación GHI)
├── Backfill_historico_ernc.py       ← utilidad puntual (NO cron): gen-real/BESS histórico
├── Backfill_meteo_historico_ernc.py ← utilidad puntual: meteo histórica eólica (reanálisis)
├── Recompute_shear_ernc.py          ← utilidad puntual: recálculo wind_shear_alpha
├── utils/
│   ├── cen_api.py                   ← wrappers APIs CEN (retry, paginación totalPages)
│   ├── db.py                        ← cliente Supabase + upserts + queries (paginación .range())
│   ├── openmeteo_api.py             ← wrapper Open-Meteo + calculados por tecnología
│   ├── nasapower_api.py             ← NASA POWER (UTC → Santiago)
│   ├── calculos.py                  ← fórmulas físicas (FV trackers/stow, eólica, derivados)
│   ├── insights.py                  ← motor de alarmas automáticas
│   ├── recomendaciones.py           ← recomendaciones operativas
│   └── pdf_report.py                ← reporte PDF (ReportLab)
├── components/
│   ├── mapa_ernc.py                 ← mapa satelital folium (nubes OWM, viento actual, stow)
│   ├── kpis_generales.py            ← cards KPI HTML
│   ├── tab_solar.py / tab_eolica.py ← detalle por parque (vista fusionada "Parques")
│   ├── tab_bess.py                  ← estado/SoC/arbitraje BESS
│   ├── tab_forecast.py              ← forecast 7 días (físico + ML)
│   ├── tab_ml.py                    ← 8 análisis ML (RF, probabilístico CQR, anomalías, CMG, eficiencia, soiling, BESS LP, NASA)
│   ├── tab_estadisticas.py          ← acumulados, FP, ingresos, CO2, BESS
│   ├── tab_historicos.py            ← consultas por rango de fechas (toda la DB)
│   ├── tab_insights.py              ← alarmas (cards clicables)
│   ├── tab_meteo_sistema.py         ← alertas meteo + heatmaps + contexto CMG
│   ├── tab_infotecnica.py           ← fichas técnicas por parque
│   ├── tab_glosario.py              ← glosario (gate con clave)
│   └── demanda.py                   ← demanda por zona (componente reutilizable)
├── assets/logo_pulsar.png
├── .streamlit/config.toml           ← (+ secrets.toml gitignored)
└── .github/workflows/
    ├── adquisicion_ernc.yml         ← cron horario :10 (completo + keep-alive)
    ├── potencia_ernc.yml            ← cron :25/:55 (gen-real + BESS)
    └── programacion_pid_ernc.yml    ← cron :40 (PID + demanda)
```

---

## PARQUES (12 confirmados en API CEN)

### Solares FV

| Código | Nombre Display | id_central | llave_opreal | llave_PCP | P_max (MW) | Lat | Lon |
|--------|---------------|-----------|-------------|----------|-----------|-----|-----|
| AS1 | Andes Solar I | 374 | PFV ANDES SOLAR | ANDES_FV | 23.97 | -24.010753 | -68.584921 | OSM way 745505231 |
| AS2A | Andes Solar 2A | 643 | PFV ANDES SOLAR IIA | ANDES_2A_FV | 91.09 | -24.009143 | -68.574685 | OSM way 1296706746 |
| AS2B | Andes Solar 2B | 1850 | PFV ANDES SOLAR IIB | ANDES_2B_FV | 220.0 | -24.000723 | -68.575145 | OSM way 974171190 |
| AS3 | Andes Solar III | 2322 | PFV Andes Solar III | ANDES_3_FV | 175.0 | -24.001486 | -68.565828 | OSM way 1296706747 |
| AS4 | Andes Solar IV | 2076 | PFV ANDES SOLAR IV | ANDES_4_FV | 220.0 | -24.021944 | -68.573460 | OSM way 1144233017 |
| BOL | PFV Bolero | 456 | PFV BOLERO | BOLERO_1_FV | 161.3 | -23.475195 | -69.408486 | Sierra Gorda, Antofagasta |
| CRI | PFV Cristales | 2419 | PFV Cristales | *(sin PCP aún)* | 300.0 | -24.1024 | -68.7756 | EN_REVISION, gen=0 (Sesión 32) |

### Eólicos

| Código | Nombre Display | id_central | llave_opreal | llave_PCP | P_max (MW) | Lat | Lon | Referencia |
|--------|---------------|-----------|-------------|----------|-----------|-----|-----|-----------|
| CL | PE Campo Lindo | 1845 | PE CAMPO LINDO | CAMPO_LINDO_EO | 76.8 | -37.404179 | -72.494720 | Los Ángeles, Biobío |
| OLM | PE Los Olmos | 1757 | PE LOS OLMOS | LOS_OLMOS_EO | 115.92 | -37.649278 | -72.473876 | Mulchén, Biobío |
| CUR | PE Los Cururos | 318 | PE LOS CURUROS | LOS_CURUROS_EO | 115.08 | -31.012533 | -71.637465 | Los Cururos Sur, Coquimbo |
| STM | PE San Matías | 2091 | PE SAN MATIAS | SAN_MATIAS_EO | 87.5 | -37.434120 | -72.552807 | Los Ángeles, Biobío |
| MSM | PE Mesamavida | 1758 | PE MESAMÁVIDA | MESAMAVIDA_EO | 70.56 | -37.489984 | -72.459097 | Los Ángeles, Biobío |

**Capacidad total:** ~1.191 MW Solar + ~466 MW Eólica = **~1.657 MW** (`PMAX_TOTAL` en config.py)

> Coordenadas confirmadas por Erick Herrera (2026-06-19) desde OSM y datos AES.

### BESS asociados (7 en `config.BESS` — adquiridos desde Sesión 17)
AS2A_B (84), AS2B_B (136.5), AS3_B (177), AS4_B (140), BOL_B (160), CRI_B (370),
ARE_B (Arenales, 315 — sin parque FV propio aún). En la API gen-real aparecen como
centrales separadas (`id_central=None`, llaves `(Inyección)`/`(Retiro)`); se adquieren
vía `fetch_gen_bess()` a la tabla `generacion_bess_ernc`. En gen-real de parques,
filtrar por `llave_opreal` exacta para excluirlos.

---


## APIS CEN — RESUMEN OPERATIVO

Detalle completo (endpoints, params, quirks, estructura S3): ver @docs/api_cen.md
- Auth por `user_key` en query string: plan SIP (`sipub.api.coordinador.cl`) y
  Operaciones (`operacion.api.coordinador.cl`). Rate limit 429 → `_get_with_retry()`.
- Endpoints en uso: gen-real v3, PCP v4, PID v4, demanda PID v4, CMG S3 (+respaldo 8b),
  CMG programado v4, limitaciones v4, SSCC v1.

## BASE DE DATOS SUPABASE — RESUMEN

Detalle completo (tablas, vistas, RLS): ver @docs/db.md
- Proyecto `ernc-aes` (ref `ozeubcqoxsihmmfpswoa`). Acceso SOLO por REST (supabase-py).
- Tablas: generacion_real_ernc, generacion_programada_ernc (PCP+PID por `fuente`),
  generacion_bess_ernc, meteo_ernc, cmg_ernc, cmg_programado_ernc, demanda_ernc,
  limitaciones_ernc, sscc_ernc.
- `fecha_hora` siempre "YYYY-MM-DD HH:MM:SS" 0-based en America/Santiago.
- Tabla nueva ⇒ política `anon_select` ANTES de consultarla desde el dashboard.

## OPEN-METEO (implementado — ver "OPEN-METEO — DETALLES IMPLEMENTACIÓN" más abajo)

```python
pip install openmeteo-requests requests-cache retry-requests
```

Variables por tecnología definidas en `config.py`:
- **Solar:** `OPENMETEO_VARS_SOLAR` (GHI, DNI, DHI, GTI, temp, viento, nubosidad)
- **Eólica:** `OPENMETEO_VARS_EOLICA` (viento 10/80/120m, dir, ráfagas, presión, BLH)

Para solares: configurar `tilt=20` y `azimuth=0` (norte, hemisferio sur).
Forecast 7 días + 2 días históricos en cada llamada.

---

## CÁLCULOS DERIVADOS (implementados en `utils/calculos.py`)

> Nota: el modelo FV incluye trackers 1-eje con stow por viento (`poa_tracker`, umbral
> POR PARQUE vía `stow_umbral()` — Sesiones 25/33) y el eólico usa curva de potencia por
> parque (`TURBINA_PARQUE`, Sesiones 14/18). Esta tabla es el índice de funciones:

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

## HISTORIAL DE SESIONES

Las 33 sesiones están documentadas verbatim en `docs/sesiones.md` (índice al final de este archivo).
Hitos mayores: 1-8 fundación/deploy · 9-13 UX y fixes · 14-18 modelos físicos reales ·
17 BESS · 19-21 navegación · 22-24 CMG programado/PID/NASA · 25 trackers+stow ·
27 PID+demanda · 28 etapa IA (probabilístico, LP BESS, soiling) · 32-33 Cristales/Arenales.

> Obsoleto (histórico): mapa 3D pydeck/TerrainLayer (el mapa es satelital folium desde S26).

---

## INSIGHTS AUTOMÁTICOS (implementados en `utils/insights.py` — Sesión 6, ampliados S15/S32/S33)

1. Desvío gen_real vs programada > ±15% (alerta si > ±25%)
2. Limitación de transmisión activa + caída de generación correlacionada
3. Eficiencia baja sin causa meteorológica: GHI > 400 W/m² pero gen < 75% esperada
4. Viento sobre cut-out: windgusts > 20 m/s en parques eólicos
5. Camanchaca: cloudcover_low > 60% pero cloudcover total < 30% (norte)
6. Wind shear alto: alpha > 0.30 (atmósfera estable, turbinas traseras afectadas)
7. CMG muy bajo (< 5 USD/MWh): ingreso horario mínimo
8. Positivo: factor de planta > 90% en parque solar (excelente recurso)

---

## COMANDOS

```bash
cd "/Users/erickosvaldoherrerakerr/Desktop/ML DATA/Dashboard ERNC/ernc-aes-dashboard"
source .venv/bin/activate

# App local
streamlit run app_ernc.py
kill $(lsof -ti:8501)                    # si el puerto quedó ocupado

# Adquisición manual (leen .env)
python Adquisicion_ernc.py               # completo horario: gen-real, PCP, BESS, CMG, limitaciones, SSCC
python Adquisicion_meteo_ernc.py         # meteo Open-Meteo + calculados
python Adquisicion_potencia_ernc.py      # solo gen-real + BESS (rápido)
python Adquisicion_pid_ernc.py           # gen PID + demanda PID
python Adquisicion_nasa_ernc.py          # NASA POWER (validación, rezago ~85 d)

# Utilidades puntuales (NO cron)
python Backfill_historico_ernc.py        # gen-real/BESS histórico por tramos de 7 días
python Backfill_meteo_historico_ernc.py  # meteo histórica eólica (reanálisis)
python Recompute_shear_ernc.py           # recalcula wind_shear_alpha almacenado

# Workflows (GitHub CLI)
gh workflow run adquisicion_ernc.yml
gh workflow run potencia_ernc.yml
gh workflow run programacion_pid_ernc.yml
```

---
## PENDIENTES VIVOS (lista única — actualizar aquí, no en los logs de sesión)

- [ ] Llave PCP de PFV Cristales cuando el CEN la publique → `LLAVES_GEN_PROG["CRI"]` (S32)
- [ ] Confirmar barra/nodo CMG real de Cristales (asignado CRUCERO_______220 por defecto) → `CMG_NODO["CRI"]` (S32)
- [ ] Confirmar Pmax neta CEN de Cristales cuando exista carta → `PMAX_NETA["CRI"]` (S32)
- [ ] Alta del FV de Arenales cuando el CEN publique su generación (hoy solo el BESS ARE_B) (S32/S33)
- [ ] (Opcional) Backfill de meteo para recalcular `p_fv_estimada_mw` histórico con los umbrales de stow por parque — el cron lo corrige hacia adelante (S33)
- [ ] (Opcional) Anclar la ventana del comparador NASA a la última fecha de NASA en vez del fijo 120 d (S24/S29)
- [ ] **Ventana PCP**: si la query PCP de 5 días se degrada en la API CEN, bajar la ventana PCP a 1-2 días (S15)
- [ ] (Opcional) Precipitación en `meteo_ernc` (schema + adquisición) para atribuir lavados de soiling a lluvia (S28)
- [ ] (Opcional) Informe de cumplimiento de pronóstico al CEN / skill vs PCP-PID (S28)
- [ ] Confirmación formal del nodo CMG de eólicos sur — CHARRUA_______220 en uso desde S5, sin confirmación de AES

Resueltos (histórico): logo sidebar (S16), satélite en mapa (S17/S26), gráficos comprimidos
(S13), repoblar `p_eolica_estimada_mw` (S25), TZ global ZoneInfo (S27), coordenadas de
Cristales (config.py ya tiene -24.1024/-68.7756), `.gitignore` sqlite (S29).

---

## SISTEMA DE DISEÑO — ESENCIAL

Detalle completo (CSS sidebar/KPIs/tabs/animaciones): ver @docs/diseno.md
- Fondo #F5F7FA (nunca blanco puro), cards #FFFFFF radius 10-12px, fuente Inter.
- Sin emojis. Plotly `template=plotly_white`, `paper_bgcolor=#FFFFFF`, `plot_bgcolor=#F5F7FA`.
- Navegación por popovers de categoría (patrón CTM, S21) — nunca st.tabs con Plotly.

### Paleta de colores AES

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

## RITUAL DE CIERRE DE SESIÓN (obligatorio)

Al terminar cada sesión de trabajo, antes del commit final:

1. Agregar el log "SESIÓN NN" al FINAL de `docs/sesiones.md` (NUNCA en CLAUDE.md).
2. Actualizar la CABECERA de CLAUDE.md si cambió: nº de parques/BESS, MW, stack,
   estructura de archivos, `APP_VERSION`.
3. Actualizar PENDIENTES VIVOS: agregar nuevos, marcar resueltos.
4. Si un bug enseñó una regla generalizable → agregarla a REGLAS APRENDIDAS.
5. Agregar la línea de la sesión al índice de sesiones de CLAUDE.md.
6. Actualizar "Última actualización" del header.
7. Verificar: ninguna key/token/password real en archivos commiteados.

---
## ÍNDICE DE SESIONES (detalle en docs/sesiones.md)

- OPEN-METEO — DETALLES IMPLEMENTACIÓN (Sesión 3)
- APP PRINCIPAL — NOTAS SESIÓN 4
- CAMBIOS SESIÓN 5 (2026-06-19)
- INSIGHTS — REGLAS IMPLEMENTADAS (Sesión 6)
- FORECAST — NOTAS (Sesión 6)
- DEPLOY STREAMLIT CLOUD (Sesión 7)
- PDF REPORTE (Sesión 7)
- DEPLOY EN PRODUCCIÓN (2026-06-19)
- BUGS CONOCIDOS Y RESUELTOS (Sesión 8 — 2026-06-19)
- SESIÓN 9 — MEJORAS VISUALES Y FIXES (2026-06-19)
- SESIÓN 10 — FIX PAGINACIÓN PCP Y VENTANA 5 DÍAS (2026-06-20)
- SESIÓN 11 — MEJORAS UX MÚLTIPLES (2026-06-20)
- SESIÓN 12 — FIXES NAVEGACIÓN Y EJE X (2026-06-21)
- SESIÓN 13 — FIX DEFINITIVO COMPRESIÓN GRÁFICOS + NAVEGACIÓN (2026-06-21)
- SESIÓN 14 — FÓRMULAS, MODELOS CORREGIDOS, CMG Y PESTAÑA ML (2026-06-21)
- SESIÓN 15 — INSIGHTS, MAPA, ESTADÍSTICAS, METEO/SISTEMA Y FIX ADQUISICIÓN (2026-06-21)
- SESIÓN 16 — REBRANDING A "PULSAR" + LOGO EN SIDEBAR (2026-06-21)
- SESIÓN 17 — SECCIÓN PRINCIPAL, FIXES SOLAR/EÓLICA, CMG, MAPA SATELITAL Y BESS (2026-06-22)
- SESIÓN 18 — PARÁMETROS TÉCNICOS REALES (CARTAS CEN) + PESTAÑA INFOTÉCNICA (2026-06-22)
- SESIÓN 19 — UX MAYOR: ALARMAS, NAV POR CATEGORÍAS, BESS/ML/ESTADÍSTICAS (2026-06-22)
- SESIÓN 20 — FIXES NAVEGACIÓN + MAPA NUBOSIDAD CONFIGURABLE (2026-06-22)
- SESIÓN 21 — MENÚ DESPLEGABLE TIPO ESCRITORIO (REPLICADO DEL CTM) (2026-06-22)
- SESIÓN 22 — NUEVOS ENDPOINTS CEN (CMG FUTURO + RESPALDO 8B) + LIMPIEZA BESS (2026-06-23)
- SESIÓN 23 — NASA POWER, FIXES MAPA, ARBITRAJE BESS Y UX (2026-06-23)
- SESIÓN 24 — POBLADO NASA POWER + FIX DESFASE HORARIO LST (2026-06-24)
- SESIÓN 25 — TRACKERS FV, LOGIN, ML FORECAST, BESS SIDEBAR, PDF/RECOMENDACIONES, WORKFLOW 30 MIN (2026-06-24)
- SESIÓN 26 — AUDITORÍA DE COMENTARIOS/AYUDA + FIX PCP 24h, MAPA SOLO SATELITAL, FÓRMULAS (2026-06-25)
- SESIÓN 27 — PROGRAMACIÓN PID + DEMANDA POR ZONA + GLOSARIO (2026-06-25)
- SESIÓN 28 — SIMPLIFICACIÓN + ETAPA IA: FORECAST PROBABILÍSTICO, OPTIMIZADOR BESS (MILP), SOILING (2026-06-25)
- SESIÓN 29 — FIX SERIES TRUNCADAS, SHEAR CUR, AUDITORÍA DATOS, HISTÓRICOS, NUBES (2026-06-26)
- SESIÓN 30 — FIXES RESUMEN/KPIS/FORECAST/HISTÓRICOS/CMG + GLOSARIO CON CLAVE (2026-06-30)
- SESIÓN 31 — RÁFAGA+STOW EN EL MAPA + HORA DEL DATO EN MÉTRICAS (2026-06-30)
- SESIÓN 32 — ALTA DE PFV CRISTALES (PARQUE FV + BESS) (2026-06-30)
- SESIÓN 33 — BESS ARENALES (BACKFILL + NAV), FIX FORECAST PROB, STOW EN ANOMALÍAS, UMBRAL STOW POR PARQUE (2026-07-01)

---

*Actualizado 2026-07-01 — Sesiones 1–33 (v2.9.2). Historial completo en docs/sesiones.md.*
*Stack: Streamlit + folium + supabase-py + GitHub Actions + Open-Meteo + API CEN + NASA POWER + scikit-learn + LightGBM + PuLP*
