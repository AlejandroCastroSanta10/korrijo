from pathlib import Path

import pytest

from app.pipeline.errors import OllamaUnavailableError, ProviderError
from app.pipeline.transcription import (
    StructuredTranscription,
    StructuringError,
    TranscriptionError,
    UnsupportedExamFormatError,
    structure_transcription,
    transcribe_exam,
)

FIXTURES = Path(__file__).parent / "fixtures"

_RAW = """\
Nombre: Ana Pérez  Grupo: 2A
1. ¿Qué es una pila?
Una pila es LIFO
2. Define cola
"""

_VALID_JSON = """\
{
  "metadata": {
    "nombre": "Ana", "apellidos": "Pérez", "grupo": "2A",
    "fecha": "2026-06-01", "dni": "12345678Z"
  },
  "answers": [
    { "question_number": 1, "answer_text": "Una pila es LIFO", "notes": null },
    { "question_number": 2, "answer_text": "", "notes": "en blanco" }
  ]
}
"""


class FakeVLM:
    """VLMProvider falso que devuelve una transcripción en bruto predefinida."""

    def __init__(self, response: str = _RAW) -> None:
        self.response = response
        self.calls = 0
        self.last_images: list[bytes] | None = None
        self.images_per_call: list[list[bytes]] = []

    async def transcribe(self, images: list[bytes], prompt: str) -> str:
        self.last_images = images
        self.images_per_call.append(images)
        self.calls += 1
        return self.response


class FakeLLM:
    """LLMProvider falso que devuelve respuestas predefinidas en orden."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def generate(self, prompt: str, schema: dict | None = None) -> str:
        index = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return self._responses[index]


@pytest.fixture
def imagen_examen(tmp_path) -> Path:
    archivo = tmp_path / "examen.png"
    archivo.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return archivo


# --------------------------------------------------------------------------- #
# transcribe_exam: VLM a texto en bruto
# --------------------------------------------------------------------------- #


async def test_transcribe_devuelve_texto_en_bruto(imagen_examen):
    vlm = FakeVLM(_RAW)

    raw = await transcribe_exam(imagen_examen, vlm)

    assert "Una pila es LIFO" in raw
    assert vlm.calls == 1


async def test_transcripcion_vacia_falla(imagen_examen):
    vlm = FakeVLM("   ")

    with pytest.raises(TranscriptionError):
        await transcribe_exam(imagen_examen, vlm)


async def test_formato_no_soportado(tmp_path):
    archivo = tmp_path / "examen.docx"
    archivo.write_bytes(b"PK\x03\x04")

    with pytest.raises(UnsupportedExamFormatError):
        await transcribe_exam(archivo, FakeVLM())


async def test_pdf_se_rasteriza_a_imagenes(tmp_path, monkeypatch):
    pdf = tmp_path / "examen.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    paginas = [b"img-pagina-1", b"img-pagina-2"]
    monkeypatch.setattr(
        "app.pipeline.transcription.pdf_to_images", lambda _path: paginas
    )
    vlm = FakeVLM()

    raw = await transcribe_exam(pdf, vlm)

    # Una llamada por página, cada una con su imagen, y marcas de página.
    assert vlm.calls == 2
    assert vlm.images_per_call == [[paginas[0]], [paginas[1]]]
    assert "--- Página 1 ---" in raw
    assert "--- Página 2 ---" in raw


async def test_imagen_se_envia_tal_cual(imagen_examen):
    vlm = FakeVLM()

    await transcribe_exam(imagen_examen, vlm)

    assert vlm.last_images == [imagen_examen.read_bytes()]


async def test_propaga_errores_del_provider(imagen_examen):
    class BoomVLM:
        async def transcribe(self, images, prompt):
            raise OllamaUnavailableError("Ollama caído")

    with pytest.raises(ProviderError):
        await transcribe_exam(imagen_examen, BoomVLM())


# --------------------------------------------------------------------------- #
# structure_transcription: texto en bruto a estructura (LLM)
# --------------------------------------------------------------------------- #


async def test_estructura_devuelve_modelo():
    result = await structure_transcription(_RAW, FakeLLM(_VALID_JSON))

    assert isinstance(result, StructuredTranscription)
    assert result.metadata.nombre == "Ana"
    assert result.metadata.dni == "12345678Z"
    assert len(result.answers) == 2
    assert result.answers[0].question_number == 1
    assert result.answers[0].answer_text == "Una pila es LIFO"


async def test_respuesta_en_blanco_es_valida():
    result = await structure_transcription(_RAW, FakeLLM(_VALID_JSON))

    blanco = result.answers[1]
    assert blanco.answer_text == ""
    assert blanco.notes == "en blanco"


async def test_metadatos_ausentes_quedan_en_none():
    llm = FakeLLM('{"answers": [{"question_number": 1, "answer_text": "x"}]}')

    result = await structure_transcription(_RAW, llm)

    assert result.metadata.nombre is None
    assert result.metadata.dni is None
    assert result.answers[0].notes is None


async def test_parsea_json_con_preambulo():
    llm = FakeLLM("Claro, aquí tienes el JSON:\n" + _VALID_JSON + "\nEspero que sirva.")

    result = await structure_transcription(_RAW, llm)

    assert len(result.answers) == 2


async def test_parsea_json_en_valla_de_codigo():
    llm = FakeLLM("```json\n" + _VALID_JSON + "\n```")

    result = await structure_transcription(_RAW, llm)

    assert result.metadata.grupo == "2A"


async def test_elimina_bloque_think():
    llm = FakeLLM("<think>déjame pensar...</think>\n" + _VALID_JSON)

    result = await structure_transcription(_RAW, llm)

    assert len(result.answers) == 2


async def test_repara_comas_finales_y_comillas_tipograficas():
    # El modelo usa comillas tipográficas como delimitadores y deja comas
    # finales: ambos desvíos los repara el parser antes de json.loads.
    abre, cierra = chr(0x201C), chr(0x201D)  # “ ”
    roto = (
        '{"metadata": {"nombre": "Ana",}, '
        '"answers": [{"question_number": 1, "answer_text": '
        + abre
        + "hola"
        + cierra
        + ",},]}"
    )

    result = await structure_transcription(_RAW, FakeLLM(roto))

    assert result.metadata.nombre == "Ana"
    assert result.answers[0].answer_text == "hola"


async def test_reintenta_y_acaba_acertando():
    llm = FakeLLM("esto no es json", _VALID_JSON)

    result = await structure_transcription(_RAW, llm)

    assert llm.calls == 2
    assert len(result.answers) == 2


async def test_falla_tras_agotar_reintentos():
    llm = FakeLLM("nada de json aquí")

    with pytest.raises(StructuringError):
        await structure_transcription(_RAW, llm, max_retries=2)

    assert llm.calls == 3  # intento inicial + 2 reintentos


async def test_respuesta_vacia_del_llm_falla():
    llm = FakeLLM("")

    with pytest.raises(StructuringError):
        await structure_transcription(_RAW, llm, max_retries=0)


async def test_estructura_propaga_errores_del_provider():
    class BoomLLM:
        async def generate(self, prompt, schema=None):
            raise OllamaUnavailableError("Ollama caído")

    with pytest.raises(ProviderError):
        await structure_transcription(_RAW, BoomLLM())


# --------------------------------------------------------------------------- #
# Integración con modelos reales (skippable). Requiere Ollama + modelos.
# --------------------------------------------------------------------------- #


@pytest.mark.integration
async def test_transcripcion_examen_real():
    """Transcribe y estructura el examen real de fixtures contra Ollama.

    Se salta si no hay modelos configurados o si Ollama no responde, para que la
    suite normal (y la CI) no dependan de la infraestructura.
    """
    from app.core.config import settings
    from app.pipeline.llm.ollama import OllamaLLMProvider
    from app.pipeline.vlm.ollama import OllamaVLMProvider

    if not settings.pipeline_vlm_model or not settings.pipeline_llm_model:
        pytest.skip("pipeline_vlm_model o pipeline_llm_model no configurados")

    try:
        raw = await transcribe_exam(FIXTURES / "examen_prueba.jpeg", OllamaVLMProvider())
        result = await structure_transcription(raw, OllamaLLMProvider())
    except ProviderError as exc:
        pytest.skip(f"Modelos no disponibles: {exc}")

    assert len(result.answers) >= 1
    assert all(isinstance(a.question_number, int) for a in result.answers)
    # Al menos una respuesta con texto: el examen de prueba no está en blanco.
    assert any(a.answer_text.strip() for a in result.answers)
