"""Transcripción del pipeline de corrección:

Convierte un examen manuscrito (PDF escaneado o imagen suelta) en una
transcripción estructurada: por cada pregunta, la respuesta literal del
alumno asociada a su número, más los metadatos de cabecera del examen.
"""

import json
import logging
import re
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.pipeline.utils import pdf_to_images
from app.pipeline.vlm.base import VLMProvider

logger = logging.getLogger(__name__)

# Extensiones de imagen que se aceptan directamente (una sola página).
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# Número de intentos extra si la salida del VLM no se puede parsear.
_DEFAULT_MAX_RETRIES = 2


class TranscriptionError(Exception):
    """No se ha podido obtener una transcripción válida del examen."""


class UnsupportedExamFormatError(TranscriptionError):
    """El fichero del examen no es un PDF ni una imagen de un tipo soportado."""


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
# Prompt
# --------------------------------------------------------------------------- #

# El prompt final está documentado y justificado en docs/pipeline-prompts.md.
TRANSCRIPTION_PROMPT = """\
Eres un asistente que transcribe respuestas de exámenes manuscritos en español.

Tu tarea es leer las páginas de un examen escrito a mano y devolver su contenido
de forma estructurada. NO corrijas: transcribe el texto literal del alumno,
respetando sus errores ortográficos y gramaticales.

Instrucciones:
- Al principio del examen suele haber una cabecera con los datos del alumno.
  Extrae lo que encuentres: nombre, apellidos, grupo, fecha y DNI. Si algún
  dato no aparece, déjalo como null.
- Identifica el número de cada pregunta (1, 2, 3...) y transcribe la respuesta
  que el alumno escribió para ella.
- El alumno puede tachar palabras y reescribir la versión correcta cerca. En ese
  caso transcribe la versión final que quería dejar, no la tachada.

Casos límite (usa el campo "notes" de cada respuesta para señalarlos):
- Pregunta sin responder o en blanco: "answer_text" vacío ("") y notes "en blanco".
- Respuesta ilegible: transcribe lo que puedas y deja notes "parcialmente ilegible".
- Varias preguntas en una misma página: sepáralas en respuestas distintas.
- Una respuesta partida entre varias páginas: únela en un solo "answer_text" y
  deja notes "respuesta continúa entre páginas".

Devuelve ÚNICAMENTE un objeto JSON con esta forma exacta, sin texto alrededor:

{
  "metadata": {
    "nombre": "<o null>",
    "apellidos": "<o null>",
    "grupo": "<o null>",
    "fecha": "<o null>",
    "dni": "<o null>"
  },
  "answers": [
    { "question_number": 1, "answer_text": "<respuesta literal>", "notes": < o null> }
  ]
}

/no_think
Responde solo con el JSON, sin explicaciones ni bloques de razonamiento.
"""


# --------------------------------------------------------------------------- #
# Punto de entrada
# --------------------------------------------------------------------------- #

"""
Este es el punto de entrada. Internamente:

    1. Rasteriza el PDF a una imagen por página (o usa la imagen tal cual).
    2. Manda las imágenes al VLMProvider con un prompt cuidado.
    3. Parsea la salida del modelo de forma robusta a un StructuredTranscription.
"""
async def transcribe_exam(
    file_path: str | Path,
    vlm_provider: VLMProvider,
    *,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> StructuredTranscription:
    """Transcribe un examen manuscrito a una estructura de datos JSON.

    Parámetros:
        file_path: ruta al examen. PDF (escaneado o no) o imagen suelta
            (.jpg, .jpeg, .png).
        vlm_provider: proveedor de visión que hará la inferencia.
        max_retries: reintentos extra si la salida del modelo no se puede
            parsear. Cada reintento vuelve a llamar al VLM.

    Devuelve:
        StructuredTranscription con metadatos y la lista de respuestas.

    Lanza:
        UnsupportedExamFormatError: si la extensión no es PDF ni imagen soportada.
        TranscriptionError: si tras agotar los reintentos no se obtiene una
            transcripción válida.
        Las excepciones de app.pipeline.errors que propague el VLMProvider
            (OllamaUnavailableError, ProviderTimeoutError...) suben tal cual.
    """
    path = Path(file_path)
    images = _load_images(path)

    last_error: Exception | None = None
    attempts = max_retries + 1
    for attempt in range(1, attempts + 1):
        raw = await vlm_provider.transcribe(images, TRANSCRIPTION_PROMPT)
        try:
            payload = _parse_json_object(raw)
            return StructuredTranscription.model_validate(payload)
        except (TranscriptionParseError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                "Transcripción no parseable (intento %d/%d) para %s: %s",
                attempt,
                attempts,
                path.name,
                exc,
            )

    raise TranscriptionError(
        f"No se pudo obtener una transcripción válida de '{path.name}' tras "
        f"{attempts} intentos."
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


# --------------------------------------------------------------------------- #
# Parsing robusto de la salida del modelo
# --------------------------------------------------------------------------- #


class TranscriptionParseError(TranscriptionError):
    """La salida del VLM no contiene un JSON parseable."""


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_CODE_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


def _parse_json_object(raw: str) -> dict:
    """Extrae y parsea el objeto JSON de la respuesta del modelo.

    Tolera los desvíos típicos de un modelo local: bloques <think>, vallas de
    código markdown, preámbulos de texto, comas finales y comillas tipográficas.
    """
    if not raw or not raw.strip():
        raise TranscriptionParseError("El VLM devolvió una respuesta vacía.")

    text = _THINK_BLOCK.sub("", raw)

    fenced = _CODE_FENCE.search(text)
    if fenced:
        text = fenced.group(1)

    candidate = _extract_first_object(text)
    if candidate is None:
        raise TranscriptionParseError(
            f"No se encontró ningún objeto JSON en la respuesta: {raw!r}"
        )

    for attempt in (candidate, _repair(candidate)):
        try:
            parsed = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
        raise TranscriptionParseError(
            f"El JSON de la respuesta no es un objeto: {attempt!r}"
        )

    raise TranscriptionParseError(
        f"El JSON de la respuesta está malformado y no se pudo reparar: {candidate!r}"
    )


def _extract_first_object(text: str) -> str | None:
    """Devuelve el primer objeto JSON balanceado del texto, o None.

    Recorre desde la primera llave de apertura contando profundidad y
    respetando las cadenas (para no confundir llaves dentro de strings).
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _repair(candidate: str) -> str:
    """Aplica reparaciones suaves a un JSON casi válido."""
    repaired = candidate
    # Comillas tipográficas a comillas rectas.
    repaired = repaired.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"}))
    # Comas finales antes de } o ].
    repaired = _TRAILING_COMMA.sub(r"\1", repaired)
    return repaired
