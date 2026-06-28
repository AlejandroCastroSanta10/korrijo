from pathlib import Path

import pytest

from app.pipeline.errors import OllamaUnavailableError, ProviderError
from app.pipeline.orchestrator import (
    CorrectionSession,
    PipelineError,
    PipelineResult,
    PipelineRun,
    correct_exam,
    prepare_session,
    run_pipeline,
)

FIXTURES = Path(__file__).parent / "fixtures"
EXAM = FIXTURES / "examen_prueba.jpeg"

# Salida válida del LLM de corrección, con ítems que existen en la rúbrica real
# de los fixtures (criterios.csv) para no disparar la detección de alucinaciones.
_GRADING_JSON = """\
{
  "total_score": 3.0,
  "rubric_filled": [
    {"item_name": "Definición", "assigned_score": 2.0, "max_score": 2.0,
     "comment": "Correcta."},
    {"item_name": "Ejemplo", "assigned_score": 1.0, "max_score": 3.0,
     "comment": "Mejorable."}
  ],
  "feedback_report": "Informe orientativo para el profesor."
}
"""

# Estructura válida que devuelve el LLM al estructurar la transcripción en bruto.
_STRUCTURE_JSON = """\
{
  "metadata": {"nombre": "Ana", "apellidos": "Pérez"},
  "answers": [
    {"question_number": 1, "answer_text": "Una pila es LIFO", "notes": null}
  ]
}
"""

# Texto en bruto que devuelve el VLM (su contenido es indiferente para los fakes).
_RAW = "1. Una pila es LIFO"


def _is_structuring(schema: dict | None) -> bool:
    """La estructuración pasa el schema de StructuredTranscription."""
    return bool(schema) and schema.get("title") == "StructuredTranscription"


class FakeVLM:
    """VLMProvider falso: devuelve una transcripción en bruto predefinida."""

    model = "fake-vlm"

    def __init__(self, response: str = _RAW) -> None:
        self.response = response
        self.calls = 0

    async def transcribe(self, images: list[bytes], prompt: str) -> str:
        self.calls += 1
        return self.response


class FlakyVLM:
    """VLMProvider falso que falla en las llamadas indicadas (1-based)."""

    model = "flaky-vlm"

    def __init__(self, fail_on: set[int]) -> None:
        self.fail_on = fail_on
        self.calls = 0

    async def transcribe(self, images: list[bytes], prompt: str) -> str:
        self.calls += 1
        if self.calls in self.fail_on:
            raise OllamaUnavailableError("Ollama caído")
        return _RAW


class FakeLLM:
    """LLMProvider falso: sirve estructuración y corrección según el schema."""

    model = "fake-llm"

    def __init__(
        self, structure: str = _STRUCTURE_JSON, grading: str = _GRADING_JSON
    ) -> None:
        self.structure = structure
        self.grading = grading
        self.calls = 0
        self.last_prompt: str | None = None

    async def generate(self, prompt: str, schema: dict | None = None) -> str:
        self.last_prompt = prompt
        self.calls += 1
        return self.structure if _is_structuring(schema) else self.grading


def _session() -> CorrectionSession:
    return CorrectionSession(
        rubric_text="Definición (2 p). Ejemplo (3 p).",
        model_exam_text="Una pila es LIFO.",
        max_score=5.0,
    )


# --------------------------------------------------------------------------- #
# Fase 1: prepare_session (extracción una sola vez)
# --------------------------------------------------------------------------- #


def test_prepare_session_extrae_el_material():
    session = prepare_session(
        FIXTURES / "criterios.csv",
        5.0,
        model_exam_path=FIXTURES / "apuntes.md",
        context_paths=[FIXTURES / "contexto.txt"],
        teacher_instructions="Valora el razonamiento.",
    )

    assert isinstance(session, CorrectionSession)
    assert session.rubric_text
    assert session.model_exam_text
    assert session.context_text
    assert session.teacher_instructions == "Valora el razonamiento."
    assert session.max_score == 5.0


def test_prepare_session_concatena_varios_contextos():
    session = prepare_session(
        FIXTURES / "criterios.csv",
        5.0,
        model_exam_path=FIXTURES / "apuntes.md",
        context_paths=[FIXTURES / "contexto.txt", FIXTURES / "apuntes.md"],
    )

    assert "---" in session.context_text


def test_prepare_session_sin_contexto_deja_none():
    session = prepare_session(
        FIXTURES / "criterios.csv", 5.0, model_exam_path=FIXTURES / "apuntes.md"
    )

    assert session.context_text is None


def test_prepare_session_max_score_invalido():
    with pytest.raises(ValueError):
        prepare_session(
            FIXTURES / "criterios.csv", 0, model_exam_path=FIXTURES / "apuntes.md"
        )


def test_prepare_session_rubrica_inexistente_es_pipeline_error():
    with pytest.raises(PipelineError) as exc_info:
        prepare_session(
            FIXTURES / "no_existe.pdf", 5.0, model_exam_path=FIXTURES / "apuntes.md"
        )

    assert exc_info.value.phase == "extracción"


def test_prepare_session_formato_no_soportado_es_pipeline_error():
    # Una imagen no es un documento nativo: la extracción de la rúbrica debe fallar.
    with pytest.raises(PipelineError) as exc_info:
        prepare_session(EXAM, 5.0, model_exam_path=FIXTURES / "apuntes.md")

    assert exc_info.value.phase == "extracción"


# --------------------------------------------------------------------------- #
# Fase 2: correct_exam (no re-extrae; reutiliza la sesión y sus proveedores)
# --------------------------------------------------------------------------- #


async def test_correct_exam_devuelve_resultado_completo():
    result = await correct_exam(
        _session(), EXAM, vlm_provider=FakeVLM(), llm_provider=FakeLLM()
    )

    assert isinstance(result, PipelineResult)
    assert result.transcription.metadata.nombre == "Ana"
    assert len(result.grading.rubric_filled) == 2
    assert result.metadata.vlm_model == "fake-vlm"
    assert result.metadata.llm_model == "fake-llm"


async def test_correct_exam_no_imputa_tiempo_de_extraccion():
    result = await correct_exam(
        _session(), EXAM, vlm_provider=FakeVLM(), llm_provider=FakeLLM()
    )

    timings = result.metadata.timings
    # correct_exam no extrae: ese tiempo es 0 y el total es la suma de las fases.
    assert timings.extraction_seconds == 0.0
    assert timings.total_seconds == pytest.approx(
        timings.transcription_seconds
        + timings.structuring_seconds
        + timings.grading_seconds
    )


async def test_correct_exam_usa_el_material_de_la_sesion():
    llm = FakeLLM()
    session = CorrectionSession(
        rubric_text="RUBRICA-MARCADOR",
        model_exam_text="MODELO-MARCADOR",
        context_text="CONTEXTO-MARCADOR",
        teacher_instructions="INDICACIONES-MARCADOR",
        max_score=5.0,
    )

    await correct_exam(session, EXAM, vlm_provider=FakeVLM(), llm_provider=llm)

    # La corrección es la última llamada al LLM: su prompt lleva todo el material.
    assert "RUBRICA-MARCADOR" in llm.last_prompt
    assert "MODELO-MARCADOR" in llm.last_prompt
    assert "CONTEXTO-MARCADOR" in llm.last_prompt
    assert "INDICACIONES-MARCADOR" in llm.last_prompt


async def test_correct_exam_error_del_vlm_es_transcripcion():
    class BoomVLM:
        model = "boom-vlm"

        async def transcribe(self, images, prompt):
            raise OllamaUnavailableError("Ollama caído")

    with pytest.raises(PipelineError) as exc_info:
        await correct_exam(
            _session(), EXAM, vlm_provider=BoomVLM(), llm_provider=FakeLLM()
        )

    assert exc_info.value.phase == "transcripción"
    assert isinstance(exc_info.value.__cause__, ProviderError)


async def test_correct_exam_error_de_estructuracion_es_estructuracion():
    class BoomStructureLLM:
        model = "boom-llm"

        async def generate(self, prompt, schema=None):
            if _is_structuring(schema):
                raise OllamaUnavailableError("Ollama caído")
            return _GRADING_JSON

    with pytest.raises(PipelineError) as exc_info:
        await correct_exam(
            _session(), EXAM, vlm_provider=FakeVLM(), llm_provider=BoomStructureLLM()
        )

    assert exc_info.value.phase == "estructuración"


async def test_correct_exam_estructuracion_no_parseable_es_estructuracion():
    with pytest.raises(PipelineError) as exc_info:
        await correct_exam(
            _session(),
            EXAM,
            vlm_provider=FakeVLM(),
            llm_provider=FakeLLM(structure="esto no es json"),
        )

    assert exc_info.value.phase == "estructuración"


async def test_correct_exam_error_del_llm_es_correccion():
    class BoomGradingLLM:
        model = "boom-llm"

        async def generate(self, prompt, schema=None):
            if _is_structuring(schema):
                return _STRUCTURE_JSON
            raise OllamaUnavailableError("Ollama caído")

    with pytest.raises(PipelineError) as exc_info:
        await correct_exam(
            _session(), EXAM, vlm_provider=FakeVLM(), llm_provider=BoomGradingLLM()
        )

    assert exc_info.value.phase == "corrección"


# --------------------------------------------------------------------------- #
# run_pipeline: prepara la sesión una vez y corrige una tanda de exámenes
# --------------------------------------------------------------------------- #


async def _run(exam_paths, **kwargs):
    return await run_pipeline(
        exam_paths,
        FIXTURES / "criterios.csv",
        kwargs.pop("max_score", 5.0),
        model_exam_path=FIXTURES / "apuntes.md",
        vlm_provider=kwargs.pop("vlm_provider", FakeVLM()),
        llm_provider=kwargs.pop("llm_provider", FakeLLM()),
        **kwargs,
    )


async def test_run_pipeline_corrige_un_examen():
    run = await _run([EXAM])

    assert isinstance(run, PipelineRun)
    assert len(run.exams) == 1
    assert run.exams[0].result is not None
    assert run.exams[0].error is None
    assert run.exams[0].result.grading.rubric_filled


async def test_run_pipeline_corrige_tanda_reutilizando_material():
    # Tres exámenes, una sola extracción y un solo par de proveedores.
    vlm = FakeVLM()
    llm = FakeLLM()
    run = await _run([EXAM, EXAM, EXAM], vlm_provider=vlm, llm_provider=llm)

    assert len(run.exams) == 3
    assert all(e.result is not None for e in run.exams)
    # La extracción se pagó una vez; cada examen pasó por VLM (1) y LLM (2:
    # estructuración + corrección).
    assert vlm.calls == 3
    assert llm.calls == 6


async def test_run_pipeline_imputa_tiempo_de_extraccion_a_la_tanda():
    run = await _run([EXAM])

    # La extracción es de la tanda; el total la cubre.
    assert run.extraction_seconds >= 0
    assert run.total_seconds >= run.extraction_seconds


async def test_run_pipeline_un_examen_que_falla_no_aborta_la_tanda():
    # El VLM falla en la 2ª llamada: el examen del medio queda en error, los otros no.
    run = await _run(
        [EXAM, EXAM, EXAM],
        vlm_provider=FlakyVLM(fail_on={2}),
        llm_provider=FakeLLM(),
    )

    assert run.exams[0].result is not None
    assert run.exams[1].result is None
    assert run.exams[1].error is not None
    assert "transcripción" in run.exams[1].error
    assert run.exams[2].result is not None


async def test_run_pipeline_max_score_invalido():
    with pytest.raises(ValueError):
        await _run([EXAM], max_score=0)


async def test_run_pipeline_error_de_extraccion_se_propaga():
    # Un fallo de sesión (rúbrica inexistente) sí aborta toda la tanda.
    with pytest.raises(PipelineError) as exc_info:
        await run_pipeline(
            [EXAM],
            FIXTURES / "no_existe.pdf",
            5.0,
            model_exam_path=FIXTURES / "apuntes.md",
            vlm_provider=FakeVLM(),
            llm_provider=FakeLLM(),
        )

    assert exc_info.value.phase == "extracción"
