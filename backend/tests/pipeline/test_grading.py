import logging
from pathlib import Path

import pytest

from app.pipeline.errors import OllamaUnavailableError, ProviderError
from app.pipeline.grading import (
    GradingError,
    GradingResult,
    grade_exam,
)
from app.pipeline.transcription import (
    ExamMetadata,
    StructuredTranscription,
    TranscribedAnswer,
)

FIXTURES = Path(__file__).parent / "fixtures"

# Rúbrica de texto libre que contiene los nombres de ítem usados en _VALID_JSON,
# para que la detección de alucinaciones no salte en el camino feliz.
_RUBRIC_TEXT = """\
Criterios de corrección:
- Definición de pila: Mal (0 p), Regular (1 p), Bien (2 p).
- Ejemplo LIFO: Mal (0 p), Bien (3 p).
"""

_VALID_JSON = """\
{
  "total_score": 3.5,
  "rubric_filled": [
    {"item_name": "Definición de pila", "assigned_score": 2.0, "max_score": 2.0,
     "comment": "Correcta y completa."},
    {"item_name": "Ejemplo LIFO", "assigned_score": 1.5, "max_score": 3.0,
     "comment": "Ejemplo parcialmente correcto."}
  ],
  "feedback_report": "El alumno define bien la pila; el ejemplo es mejorable."
}
"""


def _transcription() -> StructuredTranscription:
    return StructuredTranscription(
        metadata=ExamMetadata(nombre="Ana", apellidos="Pérez"),
        answers=[
            TranscribedAnswer(question_number=1, answer_text="Una pila es LIFO"),
            TranscribedAnswer(question_number=2, answer_text="Ejemplo: platos"),
        ],
    )


class FakeLLM:
    """LLMProvider falso que devuelve respuestas predefinidas en orden."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self.calls = 0
        self.last_prompt: str | None = None

    async def generate(self, prompt: str, schema: dict | None = None) -> str:
        self.last_prompt = prompt
        index = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return self._responses[index]


async def _grade(llm, *, rubric_text=_RUBRIC_TEXT, max_score=5.0, **kwargs):
    return await grade_exam(
        _transcription(),
        rubric_text,
        "Examen modelo: una pila es una estructura LIFO.",
        max_score,
        llm,
        **kwargs,
    )


async def test_devuelve_grading_result_valido():
    result = await _grade(FakeLLM(_VALID_JSON))

    assert isinstance(result, GradingResult)
    assert len(result.rubric_filled) == 2
    assert result.rubric_filled[0].item_name == "Definición de pila"
    assert result.feedback_report


async def test_total_se_recalcula_de_los_items():
    # El JSON dice total_score 3.5; coincide con la suma de assigned (2.0 + 1.5).
    result = await _grade(FakeLLM(_VALID_JSON))

    assert result.total_score == pytest.approx(3.5)


async def test_avisa_si_total_del_modelo_no_cuadra_con_la_suma(caplog):
    # El modelo declara total_score 5.0 pero sus ítems suman 3.5 (ambos en rango).
    descuadrado = """\
    {"total_score": 5.0, "rubric_filled": [
      {"item_name": "Definición de pila", "assigned_score": 2.0, "max_score": 2.0, "comment": ""},
      {"item_name": "Ejemplo LIFO", "assigned_score": 1.5, "max_score": 3.0, "comment": ""}
    ], "feedback_report": "x"}
    """
    with caplog.at_level(logging.WARNING):
        result = await _grade(FakeLLM(descuadrado))

    assert any("no coincide" in r.message for r in caplog.records)
    # Se usa el valor recalculado a partir de los ítems, no el del modelo.
    assert result.total_score == pytest.approx(3.5)


async def test_no_avisa_si_total_del_modelo_cuadra(caplog):
    with caplog.at_level(logging.WARNING):
        await _grade(FakeLLM(_VALID_JSON))

    assert not any("no coincide" in r.message for r in caplog.records)


async def test_total_se_trunca_a_max_score(caplog):
    roto = """\
    {"total_score": 99, "rubric_filled": [
      {"item_name": "Definición de pila", "assigned_score": 4, "max_score": 4, "comment": ""},
      {"item_name": "Ejemplo LIFO", "assigned_score": 4, "max_score": 4, "comment": ""}
    ], "feedback_report": "x"}
    """
    with caplog.at_level(logging.WARNING):
        result = await _grade(FakeLLM(roto), max_score=5.0)

    assert result.total_score == pytest.approx(5.0)
    assert any("trunca" in r.message for r in caplog.records)


async def test_assigned_score_se_recorta_al_maximo_del_item(caplog):
    roto = """\
    {"total_score": 0, "rubric_filled": [
      {"item_name": "Definición de pila", "assigned_score": 9, "max_score": 2, "comment": ""}
    ], "feedback_report": "x"}
    """
    with caplog.at_level(logging.WARNING):
        result = await _grade(FakeLLM(roto))

    assert result.rubric_filled[0].assigned_score == pytest.approx(2.0)
    assert result.total_score == pytest.approx(2.0)
    assert any("recorta" in r.message for r in caplog.records)


async def test_assigned_score_negativo_se_recorta_a_cero():
    roto = """\
    {"total_score": 0, "rubric_filled": [
      {"item_name": "Definición de pila", "assigned_score": -3, "max_score": 2, "comment": ""}
    ], "feedback_report": "x"}
    """
    result = await _grade(FakeLLM(roto))

    assert result.rubric_filled[0].assigned_score == pytest.approx(0.0)


async def test_avisa_de_item_que_no_esta_en_la_rubrica(caplog):
    inventado = """\
    {"total_score": 1, "rubric_filled": [
      {"item_name": "Caligrafía impecable", "assigned_score": 1, "max_score": 1, "comment": ""}
    ], "feedback_report": "x"}
    """
    with caplog.at_level(logging.WARNING):
        result = await _grade(FakeLLM(inventado))

    assert any("alucinación" in r.message for r in caplog.records)
    # No falla: la validación de ítems es blanda.
    assert isinstance(result, GradingResult)


async def test_parsea_json_con_ruido():
    sucio = "<think>déjame ver</think>\n```json\n" + _VALID_JSON + "\n```\nlisto"
    result = await _grade(FakeLLM(sucio))

    assert len(result.rubric_filled) == 2


async def test_reintenta_y_acaba_acertando():
    llm = FakeLLM("esto no es json", _VALID_JSON)

    result = await _grade(llm)

    assert llm.calls == 2
    assert len(result.rubric_filled) == 2


async def test_falla_tras_agotar_reintentos():
    llm = FakeLLM("nada de json")

    with pytest.raises(GradingError):
        await _grade(llm, max_score=5.0, max_retries=2)

    assert llm.calls == 3


async def test_respuesta_vacia_falla():
    with pytest.raises(GradingError):
        await _grade(FakeLLM(""), max_retries=0)


async def test_propaga_errores_del_provider():
    class BoomLLM:
        async def generate(self, prompt, schema=None):
            raise OllamaUnavailableError("Ollama caído")

    with pytest.raises(ProviderError):
        await _grade(BoomLLM())


async def test_el_prompt_incluye_las_secciones():
    llm = FakeLLM(_VALID_JSON)

    await _grade(
        llm,
        context_text="Tema 3: estructuras de datos.",
        teacher_instructions="Valora el razonamiento.",
    )

    prompt = llm.last_prompt
    assert "RÚBRICA" in prompt
    assert "CONTEXTO" in prompt
    assert "EXAMEN MODELO" in prompt
    assert "INDICACIONES DEL PROFESOR" in prompt
    # La transcripción del alumno se serializa dentro del prompt.
    assert "Una pila es LIFO" in prompt


# --------------------------------------------------------------------------- #
# Integración con un LLM real (skippable). Requiere Ollama + modelo textual.
# --------------------------------------------------------------------------- #


@pytest.mark.integration
async def test_grading_examen_real():
    """Corrige una transcripción de prueba con rúbrica real contra un Ollama de verdad.

    Se salta si no hay modelo textual configurado o si Ollama no responde.
    """
    from app.core.config import settings
    from app.pipeline.extractors.router import extract
    from app.pipeline.llm.ollama import OllamaLLMProvider

    if not settings.pipeline_llm_model:
        pytest.skip("pipeline_llm_model no configurado")

    rubric_text = extract(FIXTURES / "rubrica.xlsx")
    model_exam_text = extract(FIXTURES / "apuntes.md")
    max_score = 10.0

    provider = OllamaLLMProvider(num_ctx=16384)
    try:
        result = await grade_exam(
            _transcription(),
            rubric_text,
            model_exam_text,
            max_score,
            provider,
        )
    except ProviderError as exc:
        pytest.skip(f"LLM no disponible: {exc}")

    assert isinstance(result, GradingResult)
    assert 0 <= result.total_score <= max_score
    assert result.rubric_filled
    assert result.feedback_report.strip()
