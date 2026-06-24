"""Motor de recomendaciones operacionales del portfolio ERNC.

Traduce el estado actual (generación, desvíos, CMG, BESS, limitaciones) y el forecast
en recomendaciones accionables: qué mirar ahora y qué decisiones tomar a futuro. Se usa
tanto en la vista Referencia como en el reporte PDF.
"""
from __future__ import annotations
from dataclasses import dataclass

from config import (
    NOMBRE_DISPLAY, PARQUES_SOLAR, PARQUES_EOLICA, PMAX_FP, BESS,
)
from utils.calculos import calcular_factor_planta, calcular_desvio


@dataclass
class Recomendacion:
    prioridad: str   # alta | media | baja
    horizonte: str   # ahora | corto | futuro
    titulo: str
    detalle: str
    categoria: str = "operacion"   # operacion | mercado | mantenimiento | almacenamiento


def _bess_neta_total(bess_rows: list | None) -> tuple[float | None, str]:
    if not bess_rows:
        return None, "—"
    import pandas as pd
    df = pd.DataFrame(bess_rows)
    if df.empty or "bess" not in df.columns:
        return None, "—"
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    ult = df.sort_values("fecha_hora").drop_duplicates("bess", keep="last")
    return float(ult["potencia_neta_mw"].sum()), ult["fecha_hora"].max().strftime("%d/%m %H:%M")


def generar_recomendaciones(
    gen_por_parque: dict,
    prog_por_parque: dict,
    cmg_por_parque: dict,
    cmg_promedio: float | None,
    bess_rows: list | None,
    lim_rows: list | None,
) -> list[Recomendacion]:
    recs: list[Recomendacion] = []

    # ── Mercado: nivel de CMG ──────────────────────────────────────────────────
    if cmg_promedio is not None:
        if cmg_promedio < 5:
            recs.append(Recomendacion(
                "alta", "ahora", "CMG muy bajo — cargar baterías",
                f"El CMG promedio del SEN está en {cmg_promedio:.1f} USD/MWh. Conviene "
                "priorizar la carga de los BESS para descargar luego en horas de mayor precio.",
                "almacenamiento",
            ))
        elif cmg_promedio > 150:
            recs.append(Recomendacion(
                "alta", "ahora", "CMG alto — maximizar inyección y descargar BESS",
                f"El CMG promedio está en {cmg_promedio:.1f} USD/MWh. Ventana favorable para "
                "descargar las baterías y capturar ingreso; evitar curtailment evitable.",
                "mercado",
            ))

    # ── Almacenamiento: estado del BESS vs precio ──────────────────────────────
    neta, hora_bess = _bess_neta_total(bess_rows)
    if neta is not None and cmg_promedio is not None:
        if neta > 1 and cmg_promedio < 30:
            recs.append(Recomendacion(
                "media", "ahora", "BESS descargando con precio bajo",
                f"Los BESS están descargando {neta:.0f} MW (al {hora_bess}) con CMG "
                f"{cmg_promedio:.1f} USD/MWh. Revisar si conviene retener energía para una "
                "punta de precio más alta dentro del día.",
                "almacenamiento",
            ))
        elif neta < -1 and cmg_promedio > 120:
            recs.append(Recomendacion(
                "media", "ahora", "BESS cargando con precio alto",
                f"Los BESS están cargando {abs(neta):.0f} MW con CMG alto "
                f"({cmg_promedio:.1f} USD/MWh). Evaluar postergar la carga a una ventana "
                "de precio más bajo para mejorar el arbitraje.",
                "almacenamiento",
            ))

    # ── Operación: desvíos y factor de planta por parque ───────────────────────
    desvios_altos = []
    for p in PARQUES_SOLAR + PARQUES_EOLICA:
        gen = gen_por_parque.get(p)
        prog = prog_por_parque.get(p)
        dev = calcular_desvio(gen, prog)
        if dev["desvio_pct"] is not None and abs(dev["desvio_pct"]) > 25:
            desvios_altos.append((p, dev["desvio_pct"]))
    if desvios_altos:
        detalle = "; ".join(f"{NOMBRE_DISPLAY[p]} ({d:+.0f}%)" for p, d in desvios_altos[:6])
        recs.append(Recomendacion(
            "alta", "corto", "Desvíos vs PCP fuera de banda",
            f"Parques con desvío > ±25% respecto a la programación: {detalle}. Revisar "
            "telemetría, disponibilidad y declaración de PCP para evitar penalizaciones.",
            "operacion",
        ))

    # ── Mantenimiento: limitaciones persistentes ───────────────────────────────
    if lim_rows:
        nombres = sorted({l.get("instalacion_nombre", l.get("parque", "")) for l in lim_rows})
        recs.append(Recomendacion(
            "media", "futuro", "Limitaciones de transmisión activas",
            f"{len(lim_rows)} limitación(es) activas ({', '.join(n for n in nombres if n)}). "
            "Gestionar con el Coordinador la holgura de transmisión; considerar el BESS para "
            "desplazar energía a horas sin congestión.",
            "mantenimiento",
        ))

    # ── Positivo: buen desempeño global ────────────────────────────────────────
    gen_total = sum(v for v in gen_por_parque.values() if v is not None)
    fp_total = calcular_factor_planta(gen_total, sum(PMAX_FP.values()))
    if fp_total is not None and fp_total > 60 and not desvios_altos:
        recs.append(Recomendacion(
            "baja", "ahora", "Portfolio operando con buen factor de planta",
            f"Factor de planta global {fp_total:.0f}% y sin desvíos relevantes. Mantener "
            "condiciones; buen momento para tareas de mantenimiento menor planificado.",
            "operacion",
        ))

    if not recs:
        recs.append(Recomendacion(
            "baja", "ahora", "Sin acciones críticas",
            "El portfolio opera dentro de parámetros normales. No se detectan decisiones "
            "urgentes con los datos actuales.",
            "operacion",
        ))

    orden = {"alta": 0, "media": 1, "baja": 2}
    recs.sort(key=lambda r: orden.get(r.prioridad, 3))
    return recs
