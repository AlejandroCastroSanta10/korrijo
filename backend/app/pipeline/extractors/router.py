"""Punto de entrada único del módulo de extracción en documentos nativos.

Detecta el formato del fichero por su extensión y delega en el extractor
correspondiente.

La única función que deben usar los consumidores
de este módulo es extract (from app.pipeline.extractors.router import extract).
"""

from pathlib import Path

from app.pipeline.extractors.pdf import ScannedPDFNotSupportedError, extract_pdf
from app.pipeline.extractors.text import extract_text
from app.pipeline.extractors.xlsx import extract_xlsx

_TEXT_EXTENSIONS = {".txt", ".md", ".csv"} # Formatos de texto que se soportan


class UnsupportedFormatError(Exception):
    """La extensión del fichero no está soportada por ningún extractor."""


def extract(path: str | Path) -> str:
    """Extrae texto plano de un fichero según su extensión.

    Soporta:
        - .pdf → extract_pdf
        - .xlsx → extract_xlsx
        - .txt, .md, .csv → extract_text

    Lanza:
        UnsupportedFormatError: si la extensión no coincide con ninguno de
            los formatos soportados.
        ScannedPDFNotSupportedError: si el fichero es un PDF escaneado. Se
            re-eleva tal cual desde `extract_pdf`.
    """
    suffix = Path(path).suffix.lower()

    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".xlsx":
        return extract_xlsx(path)
    if suffix in _TEXT_EXTENSIONS:
        return extract_text(path)

    raise UnsupportedFormatError(
        f"Formato no soportado: '{suffix or path}'. "
        "Formatos admitidos: .pdf, .xlsx, .txt, .md, .csv."
    )


__all__ = ["ScannedPDFNotSupportedError", "UnsupportedFormatError", "extract"]
