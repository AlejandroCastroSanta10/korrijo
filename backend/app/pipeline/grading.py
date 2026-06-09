"""Corrección de pruebas evaluativas manuscritas:

A partir de la transcripción del examen del alumno y del material del profesor
(rúbrica, contexto, examen modelo e indicaciones), pide a un LLM textual una
rúbrica rellenada con calificación propuesta por ítem y un informe de feedback.

La salida es ORIENTATIVA: la decisión final sobre la nota será del profesor.
"""

import logging
import unicodedata

from pydantic import BaseModel, Field, ValidationError

from app.pipeline.llm.base import LLMProvider
from app.pipeline.prompts.grading import GRADING_PROMPT
from app.pipeline.transcription import StructuredTranscription
from app.pipeline.utils import JSONParseError, parse_json_object

logger = logging.getLogger(__name__)

# Número de intentos extra si la salida del LLM no se puede parsear/validar.
_DEFAULT_MAX_RETRIES = 2

# Margen al comparar floats de puntuación (el modelo a veces redondea).
_SCORE_TOLERANCE = 0.01


class GradingError(Exception):
    """No se ha podido obtener una corrección válida del examen."""


# --------------------------------------------------------------------------- #
# Modelo de datos requerido
# --------------------------------------------------------------------------- #

class RubricItemResult(BaseModel):
    """Resultado de un ítem de la rúbrica tras corregir."""

    item_name: str
    assigned_score: float
    max_score: float
    comment: str = ""


class GradingResult(BaseModel):
    """Resultado de corregir un examen contra su rúbrica."""

    total_score: float
    rubric_filled: list[RubricItemResult] = Field(default_factory=list)
    feedback_report: str = ""


def _format_transcription(transcription: StructuredTranscription) -> str:
    """Serializa la transcripción a texto legible para el prompt."""
    lines: list[str] = []

    metadata = transcription.metadata.model_dump()
    cabecera = ", ".join(
        f"{campo}: {valor}" for campo, valor in metadata.items() if valor
    )
    if cabecera:
        lines.append(f"Datos del alumno: {cabecera}")
        lines.append("")

    for answer in transcription.answers:
        texto = answer.answer_text or "(en blanco)"
        lines.append(f"Pregunta {answer.question_number}: {texto}")
        if answer.notes:
            lines.append(f"  [nota: {answer.notes}]")

    return "\n".join(lines)


def _section(title: str, body: str) -> str:
    return f"=== {title} ===\n{body.strip()}"


def _build_prompt(
    transcription: StructuredTranscription,
    rubric_text: str,
    model_exam_text: str,
    max_score: float,
    context_text: str | None,
    teacher_instructions: str | None,
) -> str:
    """Compone el prompt completo que irá al LLM, inyectando las entradas en este orden:
    rúbrica → contexto → examen modelo → indicaciones → transcripción.
    """
    parts = [
        GRADING_PROMPT,
        f"PUNTUACIÓN MÁXIMA DEL EXAMEN: {max_score}",
        _section("RÚBRICA", rubric_text),
    ]
    if context_text and context_text.strip():
        parts.append(_section("CONTEXTO", context_text))
    parts.append(_section("EXAMEN MODELO", model_exam_text))
    if teacher_instructions and teacher_instructions.strip():
        parts.append(_section("INDICACIONES DEL PROFESOR", teacher_instructions))
    parts.append(_section("EXAMEN A CORREGIR", _format_transcription(transcription)))

    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# Punto de entrada
# --------------------------------------------------------------------------- #


async def grade_exam(
    transcription: StructuredTranscription,
    rubric_text: str,
    model_exam_text: str,
    max_score: float,
    llm_provider: LLMProvider,
    *,
    context_text: str | None = None,
    teacher_instructions: str | None = None,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> GradingResult:
    """Corrige un examen y devuelve un GradingResult.

    Parámetros:
        transcription: El examen a corregir (salida de la fase de transcripción).
        rubric_text: Rúbrica del profesor en texto (formato libre).
        model_exam_text: Examen modelo de referencia en texto.
        max_score: Puntuación máxima que puede tener el examen.
        llm_provider: Proveedor textual que hará la inferencia. IMPORTANTE:
            Conviene construirlo con un num_ctx generoso: el prompt es largo.
        context_text: Material de contexto opcional (apuntes, temario...).
        teacher_instructions: Indicaciones libres del profesor tanto para contexto
        como para el examen modelo, opcionales.
        max_retries: Reintentos extra si la salida no se puede parsear/validar.

    Devuelve:
        GradingResult con la rúbrica rellenada, la nota propuesta y el informe de
        feedback de la corrección.

    Lanza:
        GradingError: Si tras agotar los reintentos no se obtiene una corrección
            válida.
        Las excepciones de app.pipeline.errors que propague el LLMProvider
            (OllamaUnavailableError, ProviderTimeoutError...) suben tal cual.
    """
    prompt = _build_prompt(
        transcription,
        rubric_text,
        model_exam_text,
        max_score,
        context_text,
        teacher_instructions,
    )

    last_error: Exception | None = None
    attempts = max_retries + 1
    for attempt in range(1, attempts + 1):
        raw = await llm_provider.generate(prompt)
        try:
            payload = parse_json_object(raw)
            result = GradingResult.model_validate(payload)
        except (JSONParseError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                "Corrección no parseable (intento %d/%d): %s", attempt, attempts, exc
            )
            continue
        return _enforce_constraints(result, rubric_text, max_score)

    raise GradingError(
        f"No se pudo obtener una corrección válida tras {attempts} intentos."
    ) from last_error


# --------------------------------------------------------------------------- #
# Validación blanda de la salida
# --------------------------------------------------------------------------- #


def _enforce_constraints(
    result: GradingResult, rubric_text: str, max_score: float
) -> GradingResult:
    """Aplica las garantías que sí se pueden comprobar y avisa de lo demás.

    - Comprueba que el total_score que devuelve el modelo cuadre con la suma de
      sus assigned_score; avisa si no (incoherencia aritmética del modelo).
    - Recorta cada assigned_score al rango [0, max_score del ítem].
    - Recalcula total_score como la suma de los recortados y lo trunca a
      [0, max_score del examen].
    - Avisa (sin fallar) de los ítems cuyo nombre no parece estar en la rúbrica:
      posibles alucinaciones. Como la rúbrica es texto libre, esta detección es
      orientativa.
    """
    rubric_normalized = _normalize(rubric_text)

    # ¿El total que dice el modelo cuadra con la suma de sus propios ítems?
    reported_sum = sum(item.assigned_score for item in result.rubric_filled)
    if abs(result.total_score - reported_sum) > _SCORE_TOLERANCE:
        logger.warning(
            "total_score del modelo (%.2f) no coincide con la suma de sus ítems "
            "(%.2f); se usará el valor recalculado.",
            result.total_score,
            reported_sum,
        )

    clamped_items: list[RubricItemResult] = []
    for item in result.rubric_filled:
        assigned = item.assigned_score
        if assigned < 0 or assigned > item.max_score:
            ajustado = min(max(assigned, 0.0), item.max_score)
            logger.warning(
                "Ítem '%s': assigned_score %.2f fuera de [0, %.2f]; se recorta a %.2f.",
                item.item_name,
                assigned,
                item.max_score,
                ajustado,
            )
            assigned = ajustado

        if not _item_in_rubric(item.item_name, rubric_normalized):
            logger.warning(
                "Ítem '%s' no parece estar en la rúbrica original (posible alucinación).",
                item.item_name,
            )

        clamped_items.append(item.model_copy(update={"assigned_score": assigned}))

    total = sum(item.assigned_score for item in clamped_items)
    truncated = min(max(total, 0.0), max_score)
    if truncated != total:
        logger.warning(
            "total_score %.2f fuera de [0, %.2f]; se trunca a %.2f.",
            total,
            max_score,
            truncated,
        )

    return result.model_copy(
        update={"rubric_filled": clamped_items, "total_score": truncated}
    )


def _normalize(text: str) -> str:
    """Minúsculas y sin acentos, para comparar de forma tolerante."""
    sin_acentos = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )
    return sin_acentos.lower()


def _item_in_rubric(item_name: str, rubric_normalized: str) -> bool:
    """Heurística tolerante: ¿aparece el ítem en la rúbrica?

    Verdadero si el nombre normalizado es subcadena de la rúbrica, o si al menos
    la mitad de sus palabras significativas (>=4 letras) aparecen en ella.
    """
    name = _normalize(item_name)
    if name and name in rubric_normalized:
        return True

    keywords = [word for word in name.split() if len(word) >= 4]
    if not keywords:
        return name in rubric_normalized

    hits = sum(1 for word in keywords if word in rubric_normalized)
    return hits >= len(keywords) / 2
