# APIs CEN — detalle técnico completo

> Extraído de CLAUDE.md (2026-07-01). Resumen operativo en CLAUDE.md → sección APIs CEN.

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
