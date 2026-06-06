"""Extractor de texto para PDFs nativos.

Usa pypdf para concatenar el texto de todas las páginas. Solo vale para
pdfs con información digital nativa (apuntes del profesor, rúbrica, etc.).

Si el resultado total es demasiado corto se asume que el PDF
es una imagen (escaneado, no sirve aquí) y se lanza ScannedPDFNotSupportedError.

Esta decisión me parece bien para el MVP, es decir, el contexto, gold standard y
rúbrica tienen que ser documentos digitales nativos, porque si no el rendimiento
decaería bastante si hay que pasar al modelo de visión bastantes documentos.

"""

from pathlib import Path

from pypdf import PdfReader

SCANNED_PDF_TEXT_THRESHOLD = 100 # Puede ser que esto haya que cambiarlo
"""Umbral mínimo de caracteres extraídos para considerar el PDF como nativo."""


class ScannedPDFNotSupportedError(Exception):
    """El PDF parece ser un documento escaneado."""


def extract_pdf(path: str | Path) -> str:
    """Extrae texto plano de un PDF nativo.

    Concatena el texto de cada página separándolas con un marcador legible
    para que el modelo textual identifique los saltos de página.

    Cada página va precedida de `\\n\\n--- Página N ---\\n\\n`.

    Lanza:
        ScannedPDFNotSupportedError: si el texto total extraído es menor que
            SCANNED_PDF_TEXT_THRESHOLD. Indica que es un PDF escaneado
            (imagen) y no se acepta aquí
    """
    reader = PdfReader(str(path))

    parts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if page_text:
            parts.append(f"--- Página {index} ---\n\n{page_text}")

    text = "\n\n".join(parts)

    if len(text) < SCANNED_PDF_TEXT_THRESHOLD:
        raise ScannedPDFNotSupportedError(
            "El PDF parece estar escaneado (texto extraído por debajo del límite). "
            "En esta versión, aquí solo se admiten PDFs nativos."
        )

    return text
