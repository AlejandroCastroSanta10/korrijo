"""Transcripción y estructuración del pipeline de corrección:

Convierte un examen manuscrito (PDF escaneado o imagen suelta) en una
transcripción estructurada: por cada pregunta, la respuesta literal del
alumno asociada a su número, más los metadatos de cabecera del examen.

Se hace en dos pasos con dos modelos distintos:

    1. transcribe_exam: el VLM (o modelo de OCR) vuelca a TEXTO todo lo que ve
       en las páginas (cabecera, enunciados y respuestas manuscritas).
    2. structure_transcription: el LLM textual reorganiza ese texto en bruto en
       un StructuredTranscription (metadatos + respuestas por pregunta).
"""

import logging
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.pipeline.llm.base import LLMProvider
from app.pipeline.prompts.structuring import STRUCTURING_PROMPT
from app.pipeline.prompts.transcription import TRANSCRIPTION_PROMPT
from app.pipeline.utils import JSONParseError, parse_json_object, pdf_to_images
from app.pipeline.vlm.base import VLMProvider

logger = logging.getLogger(__name__)

# Extensiones de imagen que se aceptan directamente (una sola página).
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# Número de intentos extra si la salida del LLM no se puede parsear.
_DEFAULT_MAX_RETRIES = 2


class TranscriptionError(Exception):
    """No se ha podido obtener una transcripción del examen."""


class UnsupportedExamFormatError(TranscriptionError):
    """El fichero del examen no es un PDF ni una imagen de un tipo soportado."""


class StructuringError(Exception):
    """No se ha podido estructurar la transcripción en bruto."""


# --------------------------------------------------------------------------- #
# Modelo de datos requerido
# --------------------------------------------------------------------------- #


class ExamMetadata(BaseModel):
    """Datos de cabecera del examen.

    Todos son opcionales: un examen real puede no incluirlos todos (o que el
    modelo no consiga leerlos). Un campo ausente se queda en None.
    """

    # De momento se supondrán estos:
    nombre: str | None = None
    apellidos: str | None = None
    grupo: str | None = None
    fecha: str | None = None
    dni: str | None = None


class TranscribedAnswer(BaseModel):
    """Transcripción de una pregunta concreta."""

    question_number: int
    answer_text: str
    notes: str | None = Field(
        default=None,
        description=(
            "Anotaciones sobre casos límite: respuesta en "
            "blanco, ilegible, tachada, partida entre páginas, etc. None si "
            "no hay nada que señalar."
        ),
    )


class StructuredTranscription(BaseModel):
    """Resultado de transcribir una instancia de prueba evaluativa manuscrita completa."""

    metadata: ExamMetadata = Field(default_factory=ExamMetadata)
    answers: list[TranscribedAnswer] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Paso 1: transcripción a texto en bruto (VLM / OCR)
# --------------------------------------------------------------------------- #


async def transcribe_exam(
    file_path: str | Path,
    vlm_provider: VLMProvider,
) -> str:
    """Transcribe un examen manuscrito a texto en bruto.

    Rasteriza el PDF a una imagen por página (o usa la imagen tal cual) y
    transcribe cada página con una llamada al VLM, concatenando el texto. Una
    página por llamada va mejor en VLM/OCR pequeños que mandarlas todas juntas.
    El modelo solo transcribe; la estructuración se hace después con
    structure_transcription.

    Parámetros:
        file_path: ruta al examen. PDF (escaneado o no) o imagen suelta
            (.jpg, .jpeg, .png).
        vlm_provider: proveedor de visión que hará la inferencia.

    Devuelve:
        El texto transcrito del examen (páginas concatenadas).

    Lanza:
        UnsupportedExamFormatError: si la extensión no es PDF ni imagen soportada.
        TranscriptionError: si el modelo no devuelve texto en ninguna página.
        Las excepciones de app.pipeline.errors que propague el VLMProvider
            (OllamaUnavailableError, ProviderTimeoutError...) suben tal cual.
    """
    path = Path(file_path)
    images = _load_images(path)
    multipage = len(images) > 1

    parts: list[str] = []
    for index, image in enumerate(images, start=1):
        raw = await vlm_provider.transcribe([image], TRANSCRIPTION_PROMPT)
        if raw and raw.strip():
            page = raw.strip()
            parts.append(f"--- Página {index} ---\n{page}" if multipage else page)

    if not parts:
        raise TranscriptionError(
            f"El modelo devolvió una transcripción vacía de '{path.name}'."
        )
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# Paso 2: estructuración del texto en bruto (LLM textual)
# --------------------------------------------------------------------------- #


async def structure_transcription(
    raw_text: str,
    llm_provider: LLMProvider,
    *,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> StructuredTranscription:
    """Estructura la transcripción en bruto en un StructuredTranscription.

    Parámetros:
        raw_text: transcripción en bruto del examen (salida de transcribe_exam).
        llm_provider: proveedor textual que hará la inferencia.
        max_retries: reintentos extra si la salida del modelo no se puede
            parsear/validar.

    Devuelve:
        StructuredTranscription con metadatos y la lista de respuestas.

    Lanza:
        StructuringError: si tras agotar los reintentos no se obtiene una
            estructura válida.
        Las excepciones de app.pipeline.errors que propague el LLMProvider
            suben tal cual.
    """
    prompt = f"{STRUCTURING_PROMPT}\n\n=== TRANSCRIPCIÓN EN BRUTO ===\n{raw_text.strip()}"
    schema = StructuredTranscription.model_json_schema()

    last_error: Exception | None = None
    attempts = max_retries + 1
    for attempt in range(1, attempts + 1):
        raw = await llm_provider.generate(prompt, schema)
        try:
            payload = parse_json_object(raw)
            return StructuredTranscription.model_validate(payload)
        except (JSONParseError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                "Estructuración no parseable (intento %d/%d): %s",
                attempt,
                attempts,
                exc,
            )

    raise StructuringError(
        f"No se pudo estructurar la transcripción tras {attempts} intentos."
    ) from last_error


# --------------------------------------------------------------------------- #
# Carga de imágenes
# --------------------------------------------------------------------------- #


def _load_images(path: Path) -> list[bytes]:
    """Devuelve la lista de imágenes (bytes) a enviar al VLM.

    Un PDF se rasteriza a una imagen por página; una imagen se manda tal cual.
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return pdf_to_images(path)
    if suffix in _IMAGE_EXTENSIONS:
        return [path.read_bytes()]

    raise UnsupportedExamFormatError(
        f"Formato de examen no soportado: '{suffix or path}'. "
        "Admitidos: PDF e imágenes (.jpg, .jpeg, .png)."
    )
