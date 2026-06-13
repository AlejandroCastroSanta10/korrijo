"""Estructuración de la rúbrica del profesor (LLM textual).

A partir de la rúbrica en texto libre, pide al LLM una lista de ítems puntuables.
Sirve para que el profesor valide la rúbrica antes de corregir y para comprobar que
la suma de puntos cuadra con la puntuación máxima del examen.
"""

import logging

from pydantic import BaseModel, Field, ValidationError

from app.pipeline.llm.base import LLMProvider
from app.pipeline.prompts.rubric import RUBRIC_PARSE_PROMPT
from app.pipeline.utils import JSONParseError, parse_json_object

logger = logging.getLogger(__name__)

# Número de intentos extra si la salida del LLM no se puede parsear/validar.
_DEFAULT_MAX_RETRIES = 2


class RubricParseError(Exception):
    """No se ha podido estructurar la rúbrica a partir de su texto."""


class RubricItem(BaseModel):
    """Un ítem puntuable de la rúbrica del profesor."""

    name: str
    max_score: float
    description: str = ""


class _ParsedRubric(BaseModel):
    """Lo que devuelve el LLM al estructurar la rúbrica."""

    items: list[RubricItem] = Field(default_factory=list)


async def parse_rubric(
    rubric_text: str,
    llm_provider: LLMProvider,
    *,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> list[RubricItem]:
    """Estructura la rúbrica en una lista de ítems puntuables.

    Parámetros:
        rubric_text: Rúbrica del profesor en texto (formato libre).
        llm_provider: Proveedor textual que hará la inferencia.
        max_retries: Reintentos extra si la salida no se puede parsear/validar.

    Devuelve:
        La lista de ítems que representa a la rúbrica estructurada

    Lanza:
        RubricParseError: si tras agotar los reintentos no se obtiene una
            estructura válida.
        Las excepciones de app.pipeline.errors que propague el LLMProvider
            (OllamaUnavailableError, ProviderTimeoutError...) suben tal cual.
    """
    prompt = f"{RUBRIC_PARSE_PROMPT}\n\n=== RÚBRICA ===\n{rubric_text.strip()}"

    last_error: Exception | None = None
    attempts = max_retries + 1
    for attempt in range(1, attempts + 1):
        raw = await llm_provider.generate(prompt)
        try:
            payload = parse_json_object(raw)
            parsed = _ParsedRubric.model_validate(payload)
        except (JSONParseError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                "Rúbrica no parseable (intento %d/%d): %s", attempt, attempts, exc
            )
            continue
        if not parsed.items:
            last_error = RubricParseError("La rúbrica estructurada no tiene ítems.")
            logger.warning("Rúbrica sin ítems (intento %d/%d).", attempt, attempts)
            continue
        return parsed.items

    raise RubricParseError(
        f"No se pudo estructurar la rúbrica tras {attempts} intentos."
    ) from last_error
