"""Extractor de texto para formatos ya planos (.txt, .md, .csv).

No interpreta el contenido: lo lee tal cual lo recibe asumiendo UTF-8 y
sustituyendo caracteres mal codificados antes que fallar.

La normalización semántica (separar columnas de CSV, parsear Markdown, etc.) la hará la
capa que consuma este texto.

"""

from pathlib import Path


def extract_text(path: str | Path) -> str:
    """Lee un fichero de texto plano y devuelve su contenido."""

    return Path(path).read_text(encoding="utf-8", errors="replace")
