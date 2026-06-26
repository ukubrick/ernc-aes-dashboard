"""Recálculo puntual de wind_shear_alpha y wind_speed_100m de los registros eólicos
ya almacenados, aplicando el fix del bracket 10m-120m.

Contexto: en la celda de PE Los Cururos, Open-Meteo entrega wind_speed_80m corrupto
(cae por debajo del v10m el 82% de las horas) → el cizalle α se saturaba al tope 0.60
el 100% del tiempo. interpolar_viento_100m ahora descarta el 80m no físico y usa el
par fiable 10m-120m. Las adquisiciones futuras ya salen corregidas; este script
reescribe el histórico ya almacenado.

    python Recompute_shear_ernc.py

Utilidad de una sola vez — NO va al cron. Idempotente.
"""
from dotenv import load_dotenv
load_dotenv()

from utils.db import get_client, upsert_meteo
from utils.calculos import interpolar_viento_100m
from config import PARQUES_EOLICA

sb = get_client()

def fetch_all(parque):
    filas, i, page = [], 0, 1000
    while True:
        lote = (sb.table("meteo_ernc")
                  .select("parque,fecha_hora,fuente,es_forecast,wind_speed_10m,wind_speed_80m,wind_speed_120m,wind_speed_100m,wind_shear_alpha")
                  .eq("parque", parque)
                  .order("fecha_hora")
                  .range(i, i + page - 1).execute()).data or []
        filas.extend(lote)
        if len(lote) < page:
            break
        i += page
    return filas

total_upd = 0
for p in PARQUES_EOLICA:
    rows = fetch_all(p)
    payload = []
    cambiados = 0
    for r in rows:
        v80, v120, v10 = r.get("wind_speed_80m"), r.get("wind_speed_120m"), r.get("wind_speed_10m")
        v100_new, alpha_new = interpolar_viento_100m(v80 or 0.0, v120 or 0.0, v10)
        a_old = r.get("wind_shear_alpha")
        if a_old is None or abs((a_old or 0) - alpha_new) > 1e-4:
            cambiados += 1
        payload.append({
            "parque": r["parque"], "fecha_hora": r["fecha_hora"], "fuente": r["fuente"],
            "wind_shear_alpha": alpha_new, "wind_speed_100m": v100_new,
        })
    # upsert en lotes
    n = 0
    for k in range(0, len(payload), 500):
        n += upsert_meteo(payload[k:k+500])
    total_upd += n
    print(f"  {p}: {len(rows)} filas, {cambiados} con alpha cambiado, {n} upserted")

print(f"TOTAL upserted: {total_upd}")
