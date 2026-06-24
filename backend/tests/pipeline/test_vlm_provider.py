import base64
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from ollama import ChatResponse, Message, ResponseError

from app.pipeline.errors import (
    ModelNotFoundError,
    OllamaUnavailableError,
    ProviderError,
    ProviderTimeoutError,
)
from app.pipeline.vlm.ollama import OllamaVLMProvider

# JSON Schema de ejemplo que el provider debe reenviar como `format`.
_SCHEMA = {"type": "object", "properties": {"answers": {"type": "array"}}}


def _chat_response(content: str) -> ChatResponse:
    return ChatResponse(
        model="x",
        created_at="2026-06-06T00:00:00Z",
        done=True,
        done_reason="stop",
        message=Message(role="assistant", content=content),
    )


@pytest.fixture
def provider() -> OllamaVLMProvider:
    return OllamaVLMProvider(model="qwen3-vl:8b")


def test_constructor_lanza_si_no_hay_modelo(monkeypatch):
    monkeypatch.setattr("app.pipeline.vlm.ollama.settings.pipeline_vlm_model", None)
    with pytest.raises(ProviderError):
        OllamaVLMProvider()


def test_constructor_usa_settings_si_no_se_pasa_modelo(monkeypatch):
    monkeypatch.setattr("app.pipeline.vlm.ollama.settings.pipeline_vlm_model", "qwen3-vl:8b")
    assert OllamaVLMProvider().model == "qwen3-vl:8b"


async def test_transcribe_codifica_imagenes_en_base64(provider):
    raw = b"\x89PNG\r\n\x1a\nfake"
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(return_value=_chat_response("transcrito"))

        result = await provider.transcribe([raw], "Describe", _SCHEMA)

    assert result == "transcrito"
    sent_message = client.chat.await_args.kwargs["messages"][0]
    assert sent_message["content"] == "Describe"
    assert sent_message["images"] == [base64.b64encode(raw).decode()]


async def test_transcribe_fuerza_el_schema_como_format(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(return_value=_chat_response("ok"))

        await provider.transcribe([b"x"], "p", _SCHEMA)

    assert client.chat.await_args.kwargs["format"] == _SCHEMA


async def test_transcribe_desactiva_thinking_por_defecto(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(return_value=_chat_response("ok"))

        await provider.transcribe([b"x"], "p", _SCHEMA)

    assert client.chat.await_args.kwargs["think"] is False


async def test_transcribe_traduce_connect_error(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(side_effect=httpx.ConnectError("boom"))

        with pytest.raises(OllamaUnavailableError):
            await provider.transcribe([b"x"], "p", _SCHEMA)


async def test_transcribe_traduce_timeout(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(side_effect=httpx.ReadTimeout("slow"))

        with pytest.raises(ProviderTimeoutError):
            await provider.transcribe([b"x"], "p", _SCHEMA)


async def test_transcribe_traduce_404_a_model_not_found(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(side_effect=ResponseError("not found", 404))

        with pytest.raises(ModelNotFoundError, match="ollama pull qwen3-vl:8b"):
            await provider.transcribe([b"x"], "p", _SCHEMA)


async def test_transcribe_traduce_otros_response_error(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(side_effect=ResponseError("server error", 500))

        with pytest.raises(ProviderError) as exc_info:
            await provider.transcribe([b"x"], "p", _SCHEMA)

    assert "500" in str(exc_info.value)
