# Utilidades compartidas para el pipeline

from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path

"""
Convierte cada página de un PDF en un PNG en memoria,
útil cuando el documento no es un PDF nativo y hay que pasarlo por el
VLMProvider).
"""
def pdf_to_images(pdf_path: str | Path, dpi: int = 200) -> list[bytes]:
    """
    Parámetros:
        pdf_path: ruta al PDF.
        dpi: resolución de renderizado. 200 es un buen balance entre
            legibilidad del manuscrito y tamaño de la imagen.

    Devuelve:
        Una lista de bytes, una entrada por página, codificadas en PNG.
        Apta para pasarse a VLMProvider.transcribe.
    """
    pages = convert_from_path(str(pdf_path), dpi=dpi)
    result: list[bytes] = []
    for page in pages:
        buffer = BytesIO()
        page.save(buffer, format="PNG")
        result.append(buffer.getvalue())
    return result
