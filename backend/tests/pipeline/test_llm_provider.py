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
from app.pipeline.llm.ollama import OllamaLLMProvider


def _chat_response(content: str) -> ChatResponse:
    return ChatResponse(
        model="x",
        created_at="2026-06-06T00:00:00Z",
        done=True,
        done_reason="stop",
        message=Message(role="assistant", content=content),
    )


@pytest.fixture
def provider() -> OllamaLLMProvider:
    return OllamaLLMProvider(model="qwen3:4b")


def test_constructor_lanza_si_no_hay_modelo(monkeypatch):
    monkeypatch.setattr("app.pipeline.llm.ollama.settings.pipeline_llm_model", None)
    with pytest.raises(ProviderError):
        OllamaLLMProvider()


def test_constructor_usa_settings_si_no_se_pasa_modelo(monkeypatch):
    monkeypatch.setattr("app.pipeline.llm.ollama.settings.pipeline_llm_model", "llama3.1")
    assert OllamaLLMProvider().model == "llama3.1"


async def test_generate_devuelve_contenido(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(return_value=_chat_response("hola"))

        result = await provider.generate("Hola")

    assert result == "hola"


async def test_generate_pasa_schema_como_format(provider):
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(return_value=_chat_response("{}"))

        await provider.generate("p", schema=schema)

    assert client.chat.await_args.kwargs["format"] == schema


async def test_generate_sin_schema_envia_format_none(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(return_value=_chat_response("ok"))

        await provider.generate("p")

    assert client.chat.await_args.kwargs["format"] is None


async def test_generate_traduce_connect_error(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(side_effect=httpx.ConnectError("boom"))

        with pytest.raises(OllamaUnavailableError):
            await provider.generate("p")


async def test_generate_traduce_timeout(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(side_effect=httpx.ReadTimeout("slow"))

        with pytest.raises(ProviderTimeoutError):
            await provider.generate("p")


async def test_generate_traduce_404_a_model_not_found(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(side_effect=ResponseError("not found", 404))

        with pytest.raises(ModelNotFoundError, match="ollama pull qwen3:4b"):
            await provider.generate("p")


async def test_generate_traduce_otros_response_error_a_provider_error(provider):
    with patch.object(provider, "_client") as client:
        client.chat = AsyncMock(side_effect=ResponseError("server error", 500))

        with pytest.raises(ProviderError) as exc_info:
            await provider.generate("p")

    assert "500" in str(exc_info.value)
