"""
Generación de reporte PDF del portfolio ERNC con ReportLab.
Produce un documento de ~4 páginas: portada, KPIs, tabla de parques e insights.
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from config import NOMBRE_DISPLAY, TECNOLOGIA, PMAX, PMAX_FP, PMAX_FP_TOTAL, PARQUES_TODOS
from utils.calculos import calcular_factor_planta, calcular_desvio, calcular_ingreso_estimado

# ── Paleta ────────────────────────────────────────────────────────────────────
_DARK       = colors.HexColor("#0f172a")
_SLATE      = colors.HexColor("#1e293b")
_AMBER      = colors.HexColor("#f59e0b")
_BLUE       = colors.HexColor("#3b82f6")
_GREEN      = colors.HexColor("#22c55e")
_RED        = colors.HexColor("#ef4444")
_YELLOW     = colors.HexColor("#fbbf24")
_TEXT       = colors.HexColor("#f1f5f9")
_MUTED      = colors.HexColor("#94a3b8")
_WHITE      = colors.white


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", fontSize=22, textColor=_AMBER,
            fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=6,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", fontSize=12, textColor=_MUTED,
            fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4,
        ),
        "seccion": ParagraphStyle(
            "seccion", fontSize=13, textColor=_AMBER,
            fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6,
        ),
        "normal": ParagraphStyle(
            "normal", fontSize=9, textColor=colors.HexColor("#334155"),
            fontName="Helvetica", spaceAfter=3,
        ),
        "insight_critico": ParagraphStyle(
            "insight_critico", fontSize=9, textColor=_RED,
            fontName="Helvetica-Bold", spaceAfter=2,
        ),
        "insight_alerta": ParagraphStyle(
            "insight_alerta", fontSize=9, textColor=_YELLOW,
            fontName="Helvetica-Bold", spaceAfter=2,
        ),
        "insight_positivo": ParagraphStyle(
            "insight_positivo", fontSize=9, textColor=_GREEN,
            fontName="Helvetica-Bold", spaceAfter=2,
        ),
        "insight_detalle": ParagraphStyle(
            "insight_detalle", fontSize=8, textColor=colors.HexColor("#475569"),
            fontName="Helvetica", spaceAfter=4, leftIndent=12,
        ),
        "pie": ParagraphStyle(
            "pie", fontSize=7, textColor=_MUTED,
            fontName="Helvetica", alignment=TA_CENTER,
        ),
    }


def _tabla_parques(
    gen_por_parque: dict,
    prog_por_parque: dict,
    cmg_por_parque: dict,
) -> Table:
    st = _styles()
    encabezado = ["Parque", "Tipo", "Cap. MW", "Gen. MW", "FP %", "Desvío %", "Ingreso USD/h"]
    filas = [encabezado]

    for p in PARQUES_TODOS:
        gen   = gen_por_parque.get(p)
        prog  = prog_por_parque.get(p)
        cmg   = cmg_por_parque.get(p)
        fp    = calcular_factor_planta(gen, PMAX_FP[p])
        dev   = calcular_desvio(gen, prog)
        ingr  = calcular_ingreso_estimado(gen, cmg) if gen and cmg else None

        gen_str  = f"{gen:.1f}"    if gen  is not None else "—"
        fp_str   = f"{fp:.1f}"     if fp   is not None else "—"
        dev_str  = f"{dev['desvio_pct']:+.1f}" if dev["desvio_pct"] is not None else "—"
        ingr_str = f"{ingr:,.0f}"  if ingr is not None else "—"

        filas.append([
            NOMBRE_DISPLAY[p],
            TECNOLOGIA[p],
            f"{PMAX_FP[p]:.1f}",
            gen_str,
            fp_str,
            dev_str,
            ingr_str,
        ])

    col_widths = [4.5*cm, 1.8*cm, 1.8*cm, 1.8*cm, 1.5*cm, 1.8*cm, 2.8*cm]
    t = Table(filas, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Encabezado
        ("BACKGROUND",    (0, 0), (-1, 0), _SLATE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), _AMBER),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        # Filas datos
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
        ("ALIGN",         (0, 1), (0, -1),  "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",    (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ]))
    return t


def _tabla_kpis_globales(
    gen_total: float,
    gen_solar: float,
    gen_eolica: float,
    fp_total: float | None,
    cmg_crucero: float | None,
    n_limitaciones: int,
    desvio_pct: float | None,
) -> Table:
    datos = [
        ["Generación total", f"{gen_total:,.1f} MW"],
        ["Solar FV",         f"{gen_solar:,.1f} MW"],
        ["Eólica",           f"{gen_eolica:,.1f} MW"],
        ["Factor de planta", f"{fp_total:.1f}%" if fp_total else "—"],
        ["CMG CRUCERO",      f"{cmg_crucero:.1f} USD/MWh" if cmg_crucero else "—"],
        ["Desvío vs PCP",    f"{desvio_pct:+.1f}%" if desvio_pct else "—"],
        ["Limitaciones activas", str(n_limitaciones)],
    ]
    t = Table(datos, colWidths=[5*cm, 5*cm])
    t.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#334155")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#0f172a")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    return t


def generar_pdf(
    gen_por_parque: dict[str, float | None],
    prog_por_parque: dict[str, float | None],
    cmg_crucero: float | None,
    cmg_por_parque: dict[str, float | None],
    n_limitaciones: int,
    insights: list,
    ultima_hora: str | None,
) -> bytes:
    """
    Genera el PDF del reporte operacional.
    Retorna bytes del PDF para descarga desde Streamlit.
    """
    from config import PARQUES_SOLAR, PARQUES_EOLICA, PMAX_TOTAL, PMAX_TOTAL_SOLAR, PMAX_TOTAL_EOLICA

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    st = _styles()
    story = []

    ahora = datetime.now().strftime("%d/%m/%Y %H:%M hrs")
    hora_dato = ultima_hora[11:16] if ultima_hora else "—"

    # ── Portada ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("⚡ AES Andes — Dashboard ERNC", st["titulo"]))
    story.append(Paragraph("Reporte Operacional del Portfolio Renovable", st["subtitulo"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"Generado: {ahora}  |  Última lectura SCADA: {hora_dato}", st["subtitulo"]))
    story.append(HRFlowable(width="100%", thickness=1, color=_AMBER, spaceAfter=16))

    # ── KPIs globales ─────────────────────────────────────────────────────────
    story.append(Paragraph("Resumen del Portfolio", st["seccion"]))

    gen_total  = sum(v for v in gen_por_parque.values() if v is not None)
    gen_solar  = sum(gen_por_parque.get(p) or 0 for p in PARQUES_SOLAR)
    gen_eolica = sum(gen_por_parque.get(p) or 0 for p in PARQUES_EOLICA)
    prog_total = sum(v for v in prog_por_parque.values() if v is not None)
    fp_total   = calcular_factor_planta(gen_total, PMAX_FP_TOTAL)
    dev_global = calcular_desvio(gen_total, prog_total)

    story.append(_tabla_kpis_globales(
        gen_total, gen_solar, gen_eolica, fp_total,
        cmg_crucero, n_limitaciones, dev_global["desvio_pct"],
    ))
    story.append(Spacer(1, 0.5*cm))

    # ── Tabla de parques ──────────────────────────────────────────────────────
    story.append(Paragraph("Estado por Parque", st["seccion"]))
    story.append(_tabla_parques(gen_por_parque, prog_por_parque, cmg_por_parque))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        "* Gen. MW = generación real última hora disponible  |  "
        "FP = factor de planta  |  Desvío = (real − PCP) / PCP",
        st["pie"],
    ))

    story.append(PageBreak())

    # ── Insights ──────────────────────────────────────────────────────────────
    story.append(Paragraph("Hallazgos Automáticos", st["seccion"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_MUTED, spaceAfter=8))

    if not insights:
        story.append(Paragraph("Sin alertas activas. Portfolio operando en parámetros normales.", st["normal"]))
    else:
        _sev_style = {
            "critico":  "insight_critico",
            "alerta":   "insight_alerta",
            "positivo": "insight_positivo",
            "info":     "normal",
        }
        _sev_label = {
            "critico": "🔴 CRÍTICO",
            "alerta":  "🟡 ALERTA",
            "positivo": "🟢 OK",
            "info":    "🔵 INFO",
        }
        for ins in insights:
            sev = ins.severidad
            label = _sev_label.get(sev, sev.upper())
            titulo = f"{label}  ·  {ins.nombre_parque}  —  {ins.titulo}"
            story.append(Paragraph(titulo, st[_sev_style.get(sev, "normal")]))
            story.append(Paragraph(ins.detalle, st["insight_detalle"]))

    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_MUTED, spaceAfter=4))
    story.append(Paragraph(
        f"Dashboard ERNC AES Andes  |  Generado automáticamente  |  {ahora}",
        st["pie"],
    ))

    doc.build(story)
    return buf.getvalue()
