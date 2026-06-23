"""Generación de los PDFs de un examen corregido (fase 2).

Dos documentos por examen, ambos a partir del GradingResult ya persistido:

    1. generate_filled_rubric_pdf  -> rúbrica rellenada (tabla de ítems + total).
    2. generate_feedback_report_pdf -> informe de feedback (resumen + detalle).

Se generan al vuelo en cada descarga a partir de los datos de la BD. La salida es
ORIENTATIVA (lo dice el pie de página): la decisión final es del profesor.

Estética de marca Korrijo.
"""

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.db.models.grading_result import GradingResult
from app.db.models.grading_session import GradingSession

_DISCLAIMER = (
    "Calificación orientativa generada por IA. "
    "La decisión final corresponde al profesor."
)

# --------------------------------------------------------------------------- #
# Paleta de marca (zinc, monocromo — coherente con el frontend)
# --------------------------------------------------------------------------- #
BRAND_DARK = colors.HexColor("#18181B")    # near-black (primario)
BRAND_TEXT = colors.HexColor("#27272A")    # texto de cuerpo (zinc-800)
BRAND_MUTED = colors.HexColor("#71717A")   # meta / pie (zinc-500)
BRAND_FAINT = colors.HexColor("#D4D4D8")   # texto sobre banda oscura (zinc-300)
BRAND_BORDER = colors.HexColor("#E4E4E7")  # bordes (zinc-200)
BRAND_ROW = colors.HexColor("#FAFAFA")     # fila alterna (zinc-50)
BRAND_FILL = colors.HexColor("#F4F4F5")    # relleno suave (zinc-100)

_BAND_H = 1.6 * cm


# --------------------------------------------------------------------------- #
# Estilos
# --------------------------------------------------------------------------- #

def _styles() -> dict:
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            "KTitle",
            parent=base["Title"],
            fontSize=20,
            leading=24,
            spaceAfter=2,
            alignment=TA_LEFT,
            textColor=BRAND_DARK,
        )
    )
    base.add(ParagraphStyle("KMeta", parent=base["Normal"], fontSize=10, textColor=BRAND_MUTED))
    base.add(
        ParagraphStyle(
            "KSection",
            parent=base["Heading2"],
            fontSize=13,
            spaceBefore=14,
            spaceAfter=6,
            textColor=BRAND_DARK,
        )
    )
    base.add(
        ParagraphStyle(
            "KBody", parent=base["Normal"], fontSize=10.5, leading=15, textColor=BRAND_TEXT
        )
    )
    base.add(
        ParagraphStyle(
            "KCell", parent=base["Normal"], fontSize=9.5, leading=13, textColor=BRAND_TEXT
        )
    )
    base.add(
        ParagraphStyle(
            "KScore", parent=base["Normal"], fontSize=18, leading=20,
            fontName="Helvetica-Bold", textColor=BRAND_DARK,
        )
    )
    base.add(
        ParagraphStyle(
            "KTotalLabel", parent=base["Normal"], fontSize=12,
            fontName="Helvetica-Bold", textColor=BRAND_DARK,
        )
    )
    base.add(
        ParagraphStyle(
            "KTotalValue", parent=base["Normal"], fontSize=15, alignment=TA_RIGHT,
            fontName="Helvetica-Bold", textColor=BRAND_DARK,
        )
    )
    return base


# --------------------------------------------------------------------------- #
# Funciones auxiliares
# --------------------------------------------------------------------------- #

def student_name(filename: str) -> str:
    """Nombre del alumno a partir del filename del examen.

    'Examen_Alejandro Castro.pdf' -> 'Alejandro Castro'.
    """
    stem = Path(filename).stem
    _, sep, tail = stem.partition("_")
    candidate = tail if sep else stem
    return candidate.replace("_", " ").strip() or stem


def _format_date(value) -> str:
    if value is None:
        return ""
    try:
        return value.strftime("%d/%m/%Y")
    except Exception:  # pragma: no cover - defensivo
        return ""


def _fmt(value) -> str:
    """Puntuación con coma decimal (es-ES) y sin ceros sobrantes: 7.5 -> '7,5'."""
    try:
        return f"{float(value):g}".replace(".", ",")
    except (TypeError, ValueError):  # pragma: no cover - defensivo
        return str(value)


def _draw_furniture(canvas, doc, doc_label: str) -> None:
    """Banda superior con el logo + pie con disclaimer y número de página."""
    canvas.saveState()
    width, height = A4

    # Banda de cabecera
    canvas.setFillColor(BRAND_DARK)
    canvas.rect(0, height - _BAND_H, width, _BAND_H, fill=1, stroke=0)

    # Wordmark "Korrijo" (logo de marca)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-BoldOblique", 17)
    canvas.drawString(2 * cm, height - _BAND_H + 0.52 * cm, "Korrijo")

    # Tipo de documento, alineado a la derecha de la banda
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(BRAND_FAINT)
    canvas.drawRightString(width - 2 * cm, height - _BAND_H + 0.56 * cm, doc_label)

    # Pie: línea + disclaimer + número de página
    canvas.setStrokeColor(BRAND_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.45 * cm, width - 2 * cm, 1.45 * cm)
    canvas.setFillColor(BRAND_MUTED)
    canvas.setFont("Helvetica-Oblique", 7.5)
    canvas.drawString(2 * cm, 1.0 * cm, _DISCLAIMER)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(width - 2 * cm, 1.0 * cm, f"Página {doc.page}")

    canvas.restoreState()


def _title_block(
    session: GradingSession,
    grading_result: GradingResult,
    exam_filename: str,
    styles: dict,
) -> list:
    """Bloque de título: sesión, alumno/a y fecha, con regla inferior."""
    meta = [f"Alumno/a: {student_name(exam_filename)}"]
    return [
        Paragraph(session.name, styles["KTitle"]),
        Paragraph("    ·    ".join(meta), styles["KMeta"]),
        HRFlowable(
            width="100%", thickness=1.2, color=BRAND_DARK,
            spaceBefore=6, spaceAfter=10,
        ),
    ]


def _build_pdf(flowables: list, doc_label: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2.7 * cm,
        bottomMargin=2.2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title="Korrijo",
    )

    def on_page(canvas, doc_):
        _draw_furniture(canvas, doc_, doc_label)

    doc.build(flowables, onFirstPage=on_page, onLaterPages=on_page)
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Rúbrica rellenada
# --------------------------------------------------------------------------- #

def generate_filled_rubric_pdf(
    grading_result: GradingResult, session: GradingSession, exam_filename: str
) -> bytes:
    """PDF de la rúbrica rellenada: tabla de ítems y total destacado."""
    styles = _styles()
    flowables = _title_block(session, grading_result, exam_filename, styles)
    flowables.append(Spacer(1, 0.1 * cm))

    rows = [["Ítem", "Asignada", "Máxima", "Comentario"]]
    for item in grading_result.rubric_filled:
        rows.append(
            [
                Paragraph(str(item.get("item_name", "")), styles["KCell"]),
                _fmt(item.get("assigned_score", 0)),
                _fmt(item.get("max_score", 0)),
                Paragraph(str(item.get("comment", "") or ""), styles["KCell"]),
            ]
        )

    table = Table(rows, colWidths=[5 * cm, 2.2 * cm, 2.2 * cm, 7.6 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9.5),
                ("ALIGN", (1, 0), (2, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, BRAND_BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_ROW]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    flowables.append(table)
    flowables.append(Spacer(1, 1 * cm))

    total = Table(
        [[
            Paragraph("Nota total propuesta", styles["KTotalLabel"]),
            Paragraph(
                f"{_fmt(grading_result.total_score)} / {_fmt(session.max_score)}",
                styles["KTotalValue"],
            ),
        ]],
        colWidths=[12 * cm, 5 * cm],
    )
    total.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_FILL),
                ("BOX", (0, 0), (-1, -1), 0.75, BRAND_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    flowables.append(total)

    return _build_pdf(flowables, "Rúbrica de corrección rellenada")


# --------------------------------------------------------------------------- #
# Informe de feedback
# --------------------------------------------------------------------------- #

def generate_feedback_report_pdf(
    grading_result: GradingResult, session: GradingSession, exam_filename: str
) -> bytes:
    """PDF del informe: resumen con nota destacada y feedback detallado."""
    styles = _styles()
    flowables = _title_block(session, grading_result, exam_filename, styles)

    # Tarjeta de resumen con la nota propuesta destacada
    score_card = Table(
        [[
            Paragraph("Nota propuesta", styles["KMeta"]),
            Paragraph(
                f"{_fmt(grading_result.total_score)} / {_fmt(session.max_score)}",
                styles["KScore"],
            ),
        ]],
        colWidths=[12 * cm, 5 * cm],
    )
    score_card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_FILL),
                ("BOX", (0, 0), (-1, -1), 0.75, BRAND_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    flowables.append(score_card)

    flowables.append(Paragraph("Feedback general", styles["KSection"]))
    report = (grading_result.feedback_report or "").strip()
    if report:
        for block in report.split("\n"):
            text = block.strip()
            flowables.append(
                Paragraph(text, styles["KBody"]) if text else Spacer(1, 0.2 * cm)
            )
    else:
        flowables.append(Paragraph("Sin feedback disponible.", styles["KBody"]))

    return _build_pdf(flowables, "Informe de la corrección")
