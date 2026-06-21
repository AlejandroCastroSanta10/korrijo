"""Lógica para la subida de documentos iniciales de una sesión.

Reúne lo que no es trivial ni propio del endpoint: los límites por tipo de
documento y la extracción de texto agnóstica del backend de storage (escribiendo
el contenido a un temporal para poder pasarlo a los extractores del pipeline).
"""

import asyncio
import tempfile
from pathlib import Path

from app.core.config import settings
from app.db.models.session_document import DocumentKind
from app.pipeline.extractors import extract

# Extensiones admitidas por tipo de documento (subconjunto de lo que soportan los
# extractores del pipeline). El contexto y el examen modelo son texto narrativo; la
# rúbrica puede venir además como hoja de cálculo (.xlsx/.csv).
_TEXT_EXTENSIONS = {".pdf", ".txt", ".md"}
ALLOWED_EXTENSIONS_BY_KIND: dict[DocumentKind, set[str]] = {
    DocumentKind.CONTEXT: _TEXT_EXTENSIONS,
    DocumentKind.MODEL_EXAM: _TEXT_EXTENSIONS,
    DocumentKind.RUBRIC: {".pdf", ".xlsx", ".csv", ".md"},
}


def allowed_extensions_for(kind: DocumentKind) -> set[str]:
    """Extensiones admitidas según el tipo de documento."""
    return ALLOWED_EXTENSIONS_BY_KIND[kind]


def size_limit_for(kind: DocumentKind) -> int:
    """Tamaño máximo (bytes) permitido según el tipo de documento."""
    if kind == DocumentKind.CONTEXT:
        return settings.max_context_upload_bytes
    return settings.max_document_upload_bytes


async def extract_document_text(content: bytes, filename: str) -> str:
    """Extrae el texto de un documento ya leído en memoria.

    Vuelca el contenido a un fichero temporal con el sufijo del original (los
    extractores trabajan con rutas) y delega en app.pipeline.extractors.extract.
    """
    suffix = Path(filename).suffix.lower()

    def _extract() -> str:
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
            tmp.write(content)
            tmp.flush()
            return extract(tmp.name)

    return await asyncio.to_thread(_extract)
