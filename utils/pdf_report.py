"""
Generación de reporte PDF del portfolio ERNC (Pulsar — AES Andes) con ReportLab.
Documento estructurado con paleta AES (sin emojis): portada, resumen ejecutivo, estado
por tecnología, almacenamiento BESS, recomendaciones y alarmas.
"""
from __future__ import annotations
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from config import NOMBRE_DISPLAY, TECNOLOGIA, PMAX_FP, PMAX_FP_TOTAL, PARQUES_TODOS, BESS
from utils.calculos import calcular_factor_planta, calcular_desvio, calcular_ingreso_estimado

# ── Paleta AES ────────────────────────────────────────────────────────────────
_AZUL    = colors.HexColor("#3B4CE8")
_AZUL_OSC = colors.HexColor("#2530B0")
_CYAN    = colors.HexColor("#4DC8DC")
_VIOLETA = colors.HexColor("#9B6FD4")
_VERDE   = colors.HexColor("#5AB848")
_AMBAR   = colors.HexColor("#F59E0B")
_ROJO    = colors.HexColor("#EF4444")
_TEXTO   = colors.HexColor("#1A1F36")
_MUTED   = colors.HexColor("#6B7280")
_BORDE   = colors.HexColor("#E5E7EB")
_GRIS    = colors.HexColor("#F5F7FA")
_BLANCO  = colors.white


def _styles() -> dict:
    getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", fontSize=24, textColor=_TEXTO,
                                 fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4),
        "subtitulo": ParagraphStyle("subtitulo", fontSize=12, textColor=_MUTED,
                                    fontName="Helvetica", alignment=TA_CENTER, spaceAfter=3),
        "seccion": ParagraphStyle("seccion", fontSize=13, textColor=_AZUL_OSC,
                                  fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6),
        "normal": ParagraphStyle("normal", fontSize=9, textColor=_TEXTO,
                                 fontName="Helvetica", spaceAfter=3, leading=13),
        "rec_alta": ParagraphStyle("rec_alta", fontSize=9.5, textColor=_ROJO,
                                   fontName="Helvetica-Bold", spaceAfter=1),
        "rec_media": ParagraphStyle("rec_media", fontSize=9.5, textColor=_AMBAR,
                                    fontName="Helvetica-Bold", spaceAfter=1),
        "rec_baja": ParagraphStyle("rec_baja", fontSize=9.5, textColor=_VERDE,
                                   fontName="Helvetica-Bold", spaceAfter=1),
        "ins_critico": ParagraphStyle("ins_critico", fontSize=9, textColor=_ROJO,
                                      fontName="Helvetica-Bold", spaceAfter=1),
        "ins_alerta": ParagraphStyle("ins_alerta", fontSize=9, textColor=_AMBAR,
                                     fontName="Helvetica-Bold", spaceAfter=1),
        "ins_positivo": ParagraphStyle("ins_positivo", fontSize=9, textColor=_VERDE,
                                       fontName="Helvetica-Bold", spaceAfter=1),
        "detalle": ParagraphStyle("detalle", fontSize=8, textColor=_MUTED,
                                  fontName="Helvetica", spaceAfter=5, leftIndent=12, leading=11),
        "pie": ParagraphStyle("pie", fontSize=7, textColor=_MUTED,
                              fontName="Helvetica", alignment=TA_CENTER),
    }


def _estilo_tabla(filas, anchos, color_hdr=_AZUL_OSC):
    t = Table(filas, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), color_hdr),
        ("TEXTCOLOR",      (0, 0), (-1, 0), _BLANCO),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0), 8),
        ("ALIGN",          (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING",     (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING",  (0, 0), (-1, 0), 6),
        ("FONTNAME",       (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",       (0, 1), (-1, -1), 8),
        ("ALIGN",          (1, 1), (-1, -1), "CENTER"),
        ("ALIGN",          (0, 1), (0, -1),  "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_GRIS, _BLANCO]),
        ("GRID",           (0, 0), (-1, -1), 0.4, _BORDE),
        ("TOPPADDING",     (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 1), (-1, -1), 4),
    ]))
    return t


def _tabla_parques(parques, gen_por_parque, prog_por_parque, cmg_por_parque, color_hdr):
    enc = ["Parque", "Pmax MW", "Gen MW", "FP %", "Desvío %", "Ingreso USD/h"]
    filas = [enc]
    for p in parques:
        gen  = gen_por_parque.get(p)
        prog = prog_por_parque.get(p)
        cmg  = cmg_por_parque.get(p)
        fp   = calcular_factor_planta(gen, PMAX_FP[p])
        dev  = calcular_desvio(gen, prog)
        ingr = calcular_ingreso_estimado(gen, cmg) if gen and cmg else None
        filas.append([
            NOMBRE_DISPLAY[p],
            f"{PMAX_FP[p]:.1f}",
            f"{gen:.1f}" if gen is not None else "—",
            f"{fp:.1f}" if fp is not None else "—",
            f"{dev['desvio_pct']:+.1f}" if dev["desvio_pct"] is not None else "—",
            f"{ingr:,.0f}" if ingr is not None else "—",
        ])
    return _estilo_tabla(filas, [4.8*cm, 2*cm, 2*cm, 1.6*cm, 2*cm, 2.8*cm], color_hdr)


def _tabla_kpis(datos):
    t = Table(datos, colWidths=[5.5*cm, 5*cm])
    t.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), _MUTED),
        ("TEXTCOLOR", (1, 0), (1, -1), _TEXTO),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_GRIS, _BLANCO]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, _BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _tabla_bess(bess_rows):
    import pandas as pd
    enc = ["BESS", "Estado", "Potencia neta MW", "Pmax MW"]
    filas = [enc]
    net = {}
    if bess_rows:
        df = pd.DataFrame(bess_rows)
        if not df.empty and "bess" in df.columns:
            df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
            ult = df.sort_values("fecha_hora").drop_duplicates("bess", keep="last")
            net = dict(zip(ult["bess"], ult["potencia_neta_mw"]))
    for cod, b in BESS.items():
        n = net.get(cod)
        if n is None:
            estado, neto = "Sin dato", "—"
        elif n > 1:
            estado, neto = "Descargando", f"{n:.1f}"
        elif n < -1:
            estado, neto = "Cargando", f"{n:.1f}"
        else:
            estado, neto = "En reposo", f"{n:.1f}"
        filas.append([b["nombre"].replace("BESS ", ""), estado, neto, f"{b['pmax_mw']:.0f}"])
    return _estilo_tabla(filas, [4.8*cm, 3*cm, 3.6*cm, 2.4*cm], _VIOLETA)


def generar_pdf(
    gen_por_parque: dict[str, float | None],
    prog_por_parque: dict[str, float | None],
    cmg_crucero: float | None,
    cmg_por_parque: dict[str, float | None],
    n_limitaciones: int,
    insights: list,
    ultima_hora: str | None,
    bess_rows: list | None = None,
    recomendaciones: list | None = None,
    cmg_promedio: float | None = None,
) -> bytes:
    """Genera el PDF del reporte operacional. Retorna bytes para descarga en Streamlit."""
    from config import PARQUES_SOLAR, PARQUES_EOLICA

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm)
    sty = _styles()
    story = []

    ahora = datetime.now().strftime("%d/%m/%Y %H:%M hrs")
    hora_dato = ultima_hora[11:16] if ultima_hora else "—"
    cmg_ref = cmg_promedio if cmg_promedio is not None else cmg_crucero

    # ── Portada ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph("Pulsar — AES Andes", sty["titulo"]))
    story.append(Paragraph("Reporte operacional del portfolio renovable", sty["subtitulo"]))
    story.append(Paragraph(f"Generado: {ahora}   ·   Última lectura CEN: {hora_dato} hrs", sty["subtitulo"]))
    story.append(Spacer(1, 0.2*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=14))

    # ── Resumen ejecutivo ─────────────────────────────────────────────────────
    gen_total  = sum(v for v in gen_por_parque.values() if v is not None)
    gen_solar  = sum(gen_por_parque.get(p) or 0 for p in PARQUES_SOLAR)
    gen_eolica = sum(gen_por_parque.get(p) or 0 for p in PARQUES_EOLICA)
    prog_total = sum(v for v in prog_por_parque.values() if v is not None)
    fp_total   = calcular_factor_planta(gen_total, PMAX_FP_TOTAL)
    dev_global = calcular_desvio(gen_total, prog_total)

    story.append(Paragraph("Resumen ejecutivo", sty["seccion"]))
    story.append(_tabla_kpis([
        ["Generación total",  f"{gen_total:,.1f} MW  ({fp_total:.0f}% FP)" if fp_total else f"{gen_total:,.1f} MW"],
        ["Solar FV",          f"{gen_solar:,.1f} MW"],
        ["Eólica",            f"{gen_eolica:,.1f} MW"],
        ["Desvío vs PCP",     f"{dev_global['desvio_pct']:+.1f}%" if dev_global["desvio_pct"] is not None else "—"],
        ["CMG promedio SEN",  f"{cmg_ref:.1f} USD/MWh" if cmg_ref else "—"],
        ["Limitaciones activas", str(n_limitaciones)],
    ]))

    # ── Estado por tecnología ─────────────────────────────────────────────────
    story.append(Paragraph("Estado por parque — Solar FV", sty["seccion"]))
    story.append(_tabla_parques(PARQUES_SOLAR, gen_por_parque, prog_por_parque, cmg_por_parque, _AZUL_OSC))
    story.append(Paragraph("Estado por parque — Eólica", sty["seccion"]))
    story.append(_tabla_parques(PARQUES_EOLICA, gen_por_parque, prog_por_parque, cmg_por_parque, _CYAN))

    # ── BESS ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("Almacenamiento BESS", sty["seccion"]))
    story.append(_tabla_bess(bess_rows))
    story.append(Paragraph(
        "Potencia neta = inyección (descarga, +) − retiro (carga, −). FP = factor de planta "
        "sobre Pmax neta CEN. Ingreso estimado = Gen × CMG del nodo del parque.",
        sty["pie"],
    ))

    story.append(PageBreak())

    # ── Recomendaciones ───────────────────────────────────────────────────────
    story.append(Paragraph("Recomendaciones", sty["seccion"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_BORDE, spaceAfter=8))
    if recomendaciones:
        _est = {"alta": "rec_alta", "media": "rec_media", "baja": "rec_baja"}
        _lbl = {"alta": "PRIORIDAD ALTA", "media": "PRIORIDAD MEDIA", "baja": "INFORMATIVO"}
        _hor = {"ahora": "Ahora", "corto": "Corto plazo", "futuro": "A futuro"}
        for r in recomendaciones:
            cab = f"[{_lbl.get(r.prioridad, '')}] · {_hor.get(r.horizonte, '')} — {r.titulo}"
            story.append(Paragraph(cab, sty[_est.get(r.prioridad, "normal")]))
            story.append(Paragraph(r.detalle, sty["detalle"]))
    else:
        story.append(Paragraph("Sin recomendaciones: el portfolio opera en parámetros normales.", sty["normal"]))

    # ── Alarmas ───────────────────────────────────────────────────────────────
    story.append(Paragraph("Alarmas automáticas", sty["seccion"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_BORDE, spaceAfter=8))
    if not insights:
        story.append(Paragraph("Sin alarmas activas. Portfolio operando en parámetros normales.", sty["normal"]))
    else:
        _est = {"critico": "ins_critico", "alerta": "ins_alerta", "positivo": "ins_positivo", "info": "normal"}
        _lbl = {"critico": "CRITICO", "alerta": "ALERTA", "positivo": "OK", "info": "INFO"}
        for ins in insights:
            sev = ins.severidad
            cab = f"[{_lbl.get(sev, sev.upper())}] · {ins.nombre_parque} — {ins.titulo}"
            story.append(Paragraph(cab, sty[_est.get(sev, "normal")]))
            story.append(Paragraph(ins.detalle, sty["detalle"]))

    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_BORDE, spaceAfter=4))
    story.append(Paragraph(f"Pulsar — AES Andes   ·   Reporte generado automáticamente   ·   {ahora}", sty["pie"]))

    doc.build(story)
    return buf.getvalue()
