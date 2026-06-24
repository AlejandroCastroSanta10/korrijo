"""Extractor de texto para PDFs nativos.

Usa pdfplumber porque, a diferencia de una extracción de texto plana, detecta las
tablas de la página y reconstruye cada celda (incluidas las que ocupan varias
líneas). Esto es clave para las rúbricas en formato tabla con niveles de
puntuación: una extracción lineal mezcla y trunca las celdas y el modelo textual
acaba asociando cada descripción al nivel equivocado.

Cada página se vuelca así:
    - El texto que queda FUERA de las tablas (títulos, prosa) como texto plano.
    - Cada tabla detectada como tabla Markdown con pipes (mismo formato que el
      extractor de .xlsx), para que el modelo asocie cada celda con su columna.

Solo vale para PDFs con texto digital nativo. Si apenas se extrae texto se asume
que el PDF es una imagen (escaneado, no sirve aquí) y se lanza
ScannedPDFNotSupportedError.
"""

from pathlib import Path

import pdfplumber

SCANNED_PDF_TEXT_THRESHOLD = 100  # Puede ser que esto haya que cambiarlo
"""Umbral mínimo de caracteres extraídos para considerar el PDF como nativo."""


class ScannedPDFNotSupportedError(Exception):
    """El PDF parece ser un documento escaneado."""


def extract_pdf(path: str | Path) -> str:
    """Extrae texto de un PDF nativo preservando la estructura de sus tablas.

    Cada página va precedida de `--- Página N ---` y combina el texto narrativo
    con las tablas detectadas, renderizadas como tablas Markdown con pipes.

    Lanza:
        ScannedPDFNotSupportedError: si el texto total extraído es menor que
            SCANNED_PDF_TEXT_THRESHOLD. Indica que es un PDF escaneado
            (imagen) y no se acepta aquí.
    """
    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            page_content = _extract_page(page)
            if page_content:
                parts.append(f"--- Página {index} ---\n\n{page_content}")

    text = "\n\n".join(parts)

    if len(text) < SCANNED_PDF_TEXT_THRESHOLD:
        raise ScannedPDFNotSupportedError(
            "El PDF parece estar escaneado (texto extraído por debajo del límite). "
            "En esta versión, aquí solo se admiten PDFs nativos."
        )

    return text


def _extract_page(page) -> str:
    """Devuelve el texto narrativo de la página seguido de sus tablas."""
    tables = page.find_tables()

    # El texto narrativo es lo que queda fuera de las tablas detectadas.
    prose_page = page
    for table in tables:
        prose_page = prose_page.outside_bbox(table.bbox)
    prose = (prose_page.extract_text() or "").strip()

    blocks: list[str] = []
    if prose:
        blocks.append(prose)
    for table in tables:
        rendered = _format_table(table.extract())
        if rendered:
            blocks.append(rendered)

    return "\n\n".join(blocks)


def _format_table(rows) -> str:
    """Renderiza las filas de una tabla como tabla Markdown con pipes."""
    formatted: list[str] = []
    for row in rows:
        cells = [_format_cell(cell) for cell in row]
        if not any(cells):
            continue
        formatted.append("| " + " | ".join(cells) + " |")
    return "\n".join(formatted)


def _format_cell(value: object) -> str:
    """Colapsa los saltos de línea internos para que la celda ocupe una sola fila."""
    if value is None:
        return ""
    return " ".join(str(value).split())
