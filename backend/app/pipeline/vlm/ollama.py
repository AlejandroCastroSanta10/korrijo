"""Implementación de VLMProvider contra el servidor local de Ollama.

Envía las imágenes en base64 dentro del campo 'images' de un mensaje de
'chat', como espera Ollama para este caso.
"""

import base64

import httpx
from ollama import AsyncClient, ResponseError

from app.core.config import settings
from app.pipeline.errors import (
    ModelNotFoundError,
    OllamaUnavailableError,
    ProviderError,
    ProviderTimeoutError,
)
from app.pipeline.vlm.base import VLMProvider


class OllamaVLMProvider(VLMProvider):
    """
    Parámetros:
        model: nombre del modelo de visión en Ollama (qwen3-vl:8b, etc.).
            Si es None, se lee de settings.pipeline_vlm_model.
        base_url: URL del servidor Ollama.
        temperature, top_p, num_ctx: opciones de inferencia. num_ctx
            debe ser generoso para imágenes grandes y prompts largos.
        timeout: segundos para la llamada HTTP completa. Los VLM son
            MUCHO más lentos que los LLM textuales; por defecto 300s.
    """
    def __init__(
        self,
        model: str | None = None,
        *,
        base_url: str | None = None,
        temperature: float = 0.0,
        top_p: float = 0.9,
        num_ctx: int = 8192,
        timeout: float = 300.0,
    ) -> None:
        resolved_model = model or settings.pipeline_vlm_model
        if not resolved_model:
            raise ProviderError(
                "No se ha indicado un modelo VLM. Pásalo en el constructor o "
                "configura pipeline_vlm_model en las settings."
            )

        self.model = resolved_model
        self.base_url = base_url or settings.ollama_base_url
        self.temperature = temperature
        self.top_p = top_p
        self.num_ctx = num_ctx
        self.timeout = timeout
        self._client = AsyncClient(host=self.base_url, timeout=timeout)

    async def transcribe(self, images: list[bytes], prompt: str) -> str:
        encoded = [base64.b64encode(img).decode() for img in images]

        try:
            response = await self._client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt, "images": encoded}],
                options={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_ctx": self.num_ctx,
                },
            )
        except ResponseError as exc:
            raise self._translate_response_error(exc) from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Ollama tardó más de {self.timeout:.0f}s en responder."
            ) from exc
        except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            raise OllamaUnavailableError(
                f"No se ha podido contactar con Ollama en {self.base_url}. "
                "¿Está corriendo el servidor?"
            ) from exc

        return response.message.content or ""

    def _translate_response_error(self, exc: ResponseError) -> ProviderError:
        if exc.status_code == 404:
            return ModelNotFoundError(
                f"El modelo '{self.model}' no está descargado en Ollama. "
                f"Descárgalo con: ollama pull {self.model}"
            )
        return ProviderError(f"Ollama devolvió un error ({exc.status_code}): {exc.error}")
