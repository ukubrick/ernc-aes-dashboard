# Base de datos Supabase — detalle completo

> Extraído de CLAUDE.md (2026-07-01). Resumen operativo en CLAUDE.md → sección Base de datos.

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
