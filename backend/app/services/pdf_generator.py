"""Generación de los PDFs de un examen corregido (fase 2).

Dos documentos por examen, ambos a partir del GradingResult ya persistido:

    1. generate_filled_rubric_pdf  -> rúbrica rellenada (tabla de ítems + total).
    2. generate_feedback_report_pdf -> informe de feedback (resumen + detalle).

Se generan al vuelo en cada descarga a partir de los datos de la BD. La salida es
ORIENTATIVA (lo dice el pie del informe): la decisión final es del profesor.
"""

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
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
# Funciones auxiliares
# --------------------------------------------------------------------------- #

def _styles() -> dict:
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            "KTitle", parent=base["Title"], fontSize=18, spaceAfter=6, alignment=TA_CENTER
        )
    )
    base.add(ParagraphStyle("KMeta", parent=base["Normal"], fontSize=10, textColor=colors.grey))
    base.add(ParagraphStyle("KSection", parent=base["Heading2"], fontSize=13, spaceBefore=12))
    base.add(ParagraphStyle("KCell", parent=base["Normal"], fontSize=9, leading=12))
    base.add(
        ParagraphStyle(
            "KDisclaimer",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
        )
    )
    return base


def student_name(filename: str) -> str:
    """Nombre del alumno a partir del filename del examen.

    'Examen_Alejandro Castro.pdf' -> 'Alejandro Castro'.
    """
    stem = Path(filename).stem
    _, sep, tail = stem.partition("_")
    candidate = tail if sep else stem
    return candidate.replace("_", " ").strip() or stem


def _header(session: GradingSession, exam_filename: str, styles: dict) -> list:
    """Cabecera común: nombre de la sesión y del alumno."""
    return [
        Paragraph(session.name, styles["KTitle"]),
        Paragraph(f"Alumno/a: {student_name(exam_filename)}", styles["KMeta"]),
        Spacer(1, 0.4 * cm),
    ]


def _build_pdf(flowables: list) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title="Korrijo",
    )
    doc.build(flowables)
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Rúbrica rellenada
# --------------------------------------------------------------------------- #

def generate_filled_rubric_pdf(
    grading_result: GradingResult, session: GradingSession, exam_filename: str
) -> bytes:
    """PDF de la rúbrica rellenada: tabla de ítems y total destacado."""
    styles = _styles()
    flowables = _header(session, exam_filename, styles)
    flowables.append(Paragraph("Rúbrica de corrección", styles["KSection"]))
    flowables.append(Spacer(1, 0.2 * cm))

    header = ["Ítem", "Asignada", "Máxima", "Comentario"]
    rows = [header]
    for item in grading_result.rubric_filled:
        rows.append(
            [
                Paragraph(str(item.get("item_name", "")), styles["KCell"]),
                f"{item.get('assigned_score', 0):g}",
                f"{item.get('max_score', 0):g}",
                Paragraph(str(item.get("comment", "") or ""), styles["KCell"]),
            ]
        )

    table = Table(rows, colWidths=[5 * cm, 2 * cm, 2 * cm, 8 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (1, 0), (2, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    flowables.append(table)
    flowables.append(Spacer(1, 0.5 * cm))

    total = Table(
        [[
            Paragraph("<b>Nota total</b>", styles["KCell"]),
            Paragraph(
                f"<b>{grading_result.total_score:g} / {session.max_score:g}</b>",
                styles["KCell"],
            ),
        ]],
        colWidths=[9 * cm, 8 * cm],
    )
    total.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eaf2f8")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#2c3e50")),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    flowables.append(total)
    flowables.append(Spacer(1, 0.6 * cm))
    flowables.append(Paragraph(_DISCLAIMER, styles["KDisclaimer"]))

    return _build_pdf(flowables)


# --------------------------------------------------------------------------- #
# Informe de feedback
# --------------------------------------------------------------------------- #

def generate_feedback_report_pdf(
    grading_result: GradingResult, session: GradingSession, exam_filename: str
) -> bytes:
    """PDF del informe: resumen y feedback detallado del modelo."""
    styles = _styles()
    flowables = _header(session, exam_filename, styles)

    flowables.append(Paragraph("Resumen", styles["KSection"]))
    flowables.append(
        Paragraph(
            f"Nota propuesta: <b>{grading_result.total_score:g} / {session.max_score:g}</b>",
            styles["Normal"],
        )
    )
    flowables.append(Spacer(1, 0.3 * cm))

    flowables.append(Paragraph("Feedback detallado", styles["KSection"]))
    report = (grading_result.feedback_report or "").strip()
    if report:
        for block in report.split("\n"):
            text = block.strip()
            flowables.append(
                Paragraph(text, styles["Normal"]) if text else Spacer(1, 0.2 * cm)
            )
    else:
        flowables.append(Paragraph("Sin feedback disponible.", styles["Normal"]))

    flowables.append(Spacer(1, 0.8 * cm))
    flowables.append(Paragraph(_DISCLAIMER, styles["KDisclaimer"]))

    return _build_pdf(flowables)
