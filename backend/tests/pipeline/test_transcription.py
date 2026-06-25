from pathlib import Path

import pytest

from app.pipeline.errors import OllamaUnavailableError, ProviderError
from app.pipeline.transcription import (
    StructuredTranscription,
    TranscriptionError,
    UnsupportedExamFormatError,
    transcribe_exam,
)

FIXTURES = Path(__file__).parent / "fixtures"

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
    """VLMProvider falso que devuelve respuestas predefinidas en orden."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)
        self.calls = 0
        self.last_images: list[bytes] | None = None

    async def transcribe(
        self, images: list[bytes], prompt: str, schema: dict | None = None
    ) -> str:
        self.last_images = images
        index = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return self._responses[index]


@pytest.fixture
def imagen_examen(tmp_path) -> Path:
    archivo = tmp_path / "examen.png"
    archivo.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return archivo


async def test_transcribe_devuelve_estructura(imagen_examen):
    vlm = FakeVLM(_VALID_JSON)

    result = await transcribe_exam(imagen_examen, vlm)

    assert isinstance(result, StructuredTranscription)
    assert result.metadata.nombre == "Ana"
    assert result.metadata.dni == "12345678Z"
    assert len(result.answers) == 2
    assert result.answers[0].question_number == 1
    assert result.answers[0].answer_text == "Una pila es LIFO"


async def test_respuesta_en_blanco_es_valida(imagen_examen):
    vlm = FakeVLM(_VALID_JSON)

    result = await transcribe_exam(imagen_examen, vlm)

    blanco = result.answers[1]
    assert blanco.answer_text == ""
    assert blanco.notes == "en blanco"


async def test_metadatos_ausentes_quedan_en_none(imagen_examen):
    vlm = FakeVLM('{"answers": [{"question_number": 1, "answer_text": "x"}]}')

    result = await transcribe_exam(imagen_examen, vlm)

    assert result.metadata.nombre is None
    assert result.metadata.dni is None
    assert result.answers[0].notes is None


async def test_parsea_json_con_preambulo(imagen_examen):
    vlm = FakeVLM("Claro, aquí tienes el JSON:\n" + _VALID_JSON + "\nEspero que sirva.")

    result = await transcribe_exam(imagen_examen, vlm)

    assert len(result.answers) == 2


async def test_parsea_json_en_valla_de_codigo(imagen_examen):
    vlm = FakeVLM("```json\n" + _VALID_JSON + "\n```")

    result = await transcribe_exam(imagen_examen, vlm)

    assert result.metadata.grupo == "2A"


async def test_elimina_bloque_think(imagen_examen):
    vlm = FakeVLM("<think>déjame pensar...</think>\n" + _VALID_JSON)

    result = await transcribe_exam(imagen_examen, vlm)

    assert len(result.answers) == 2


async def test_repara_comas_finales_y_comillas_tipograficas(imagen_examen):
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
    vlm = FakeVLM(roto)

    result = await transcribe_exam(imagen_examen, vlm)

    assert result.metadata.nombre == "Ana"
    assert result.answers[0].answer_text == "hola"


async def test_reintenta_y_acaba_acertando(imagen_examen):
    vlm = FakeVLM("esto no es json", _VALID_JSON)

    result = await transcribe_exam(imagen_examen, vlm)

    assert vlm.calls == 2
    assert len(result.answers) == 2


async def test_falla_tras_agotar_reintentos(imagen_examen):
    vlm = FakeVLM("nada de json aquí")

    with pytest.raises(TranscriptionError):
        await transcribe_exam(imagen_examen, vlm, max_retries=2)

    assert vlm.calls == 3  # intento inicial + 2 reintentos


async def test_respuesta_vacia_del_vlm_falla(imagen_examen):
    vlm = FakeVLM("")

    with pytest.raises(TranscriptionError):
        await transcribe_exam(imagen_examen, vlm, max_retries=0)


async def test_formato_no_soportado(tmp_path):
    archivo = tmp_path / "examen.docx"
    archivo.write_bytes(b"PK\x03\x04")

    with pytest.raises(UnsupportedExamFormatError):
        await transcribe_exam(archivo, FakeVLM(_VALID_JSON))


async def test_pdf_se_rasteriza_a_imagenes(tmp_path, monkeypatch):
    pdf = tmp_path / "examen.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    paginas = [b"img-pagina-1", b"img-pagina-2"]
    monkeypatch.setattr(
        "app.pipeline.transcription.pdf_to_images", lambda _path: paginas
    )
    vlm = FakeVLM(_VALID_JSON)

    await transcribe_exam(pdf, vlm)

    assert vlm.last_images == paginas


async def test_imagen_se_envia_tal_cual(imagen_examen):
    vlm = FakeVLM(_VALID_JSON)

    await transcribe_exam(imagen_examen, vlm)

    assert vlm.last_images == [imagen_examen.read_bytes()]


async def test_propaga_errores_del_provider(imagen_examen):
    class BoomVLM:
        async def transcribe(self, images, prompt, schema=None):
            raise OllamaUnavailableError("Ollama caído")

    with pytest.raises(ProviderError):
        await transcribe_exam(imagen_examen, BoomVLM())


# --------------------------------------------------------------------------- #
# Integración con un VLM real (skippable). Requiere Ollama + modelo de visión.
# --------------------------------------------------------------------------- #


@pytest.mark.integration
async def test_transcripcion_examen_real():
    """Transcribe el examen real de fixtures contra un Ollama de verdad.

    Se salta si no hay modelo de visión configurado o si Ollama no responde,
    para que la suite normal (y la CI) no dependan de la infraestructura.
    """
    from app.core.config import settings
    from app.pipeline.vlm.ollama import OllamaVLMProvider

    if not settings.pipeline_vlm_model:
        pytest.skip("pipeline_vlm_model no configurado")

    provider = OllamaVLMProvider()
    try:
        result = await transcribe_exam(FIXTURES / "examen_prueba.jpeg", provider)
    except ProviderError as exc:
        pytest.skip(f"VLM no disponible: {exc}")

    assert len(result.answers) >= 1
    assert all(isinstance(a.question_number, int) for a in result.answers)
    # Al menos una respuesta con texto: el examen de prueba no está en blanco.
    assert any(a.answer_text.strip() for a in result.answers)
