# Implementación de LLMProvider contra el servidor local de Ollama.

import httpx
from ollama import AsyncClient, ResponseError

from app.core.config import settings
from app.pipeline.errors import (
    ModelNotFoundError,
    OllamaUnavailableError,
    ProviderError,
    ProviderTimeoutError,
)
from app.pipeline.llm.base import LLMProvider


class OllamaLLMProvider(LLMProvider):
    """
    Parámetros:
        model: nombre del modelo en Ollama (qwen3:14b, etc.).
            Si es None, se lee de settings.pipeline_llm_model y se
            lanza ProviderError si tampoco está definido.
        base_url: URL del servidor Ollama. Por defecto el valor de settings.
        temperature, top_p, num_ctx: opciones de inferencia. num_ctx
            controla la ventana de contexto; conviene subirlo cuando el
            prompt sea largo (rúbrica + examen, por ejemplo).
        timeout: segundos para la llamada HTTP completa.
        think: controla el modo razonamiento de modelos híbridos (ej. qwen3).
            Por defecto True: el modelo razona la corrección para mejorarla Ponerlo a False
            para desactivar el razonamiento y ganar tiempo, pero empeorará la corrección.
    """
    def __init__(
        self,
        model: str | None = None,
        *,
        base_url: str | None = None,
        temperature: float = 0.0,
        top_p: float = 0.9,
        num_ctx: int = 8192,
        timeout: float = 120.0,
        think: bool | None = True,
    ) -> None:
        resolved_model = model or settings.pipeline_llm_model
        if not resolved_model:
            raise ProviderError(
                "No se ha indicado un modelo LLM. Pásalo en el constructor o "
                "configura pipeline_llm_model en las settings."
            )

        self.model = resolved_model
        self.base_url = base_url or settings.ollama_base_url
        self.temperature = temperature
        self.top_p = top_p
        self.num_ctx = num_ctx
        self.timeout = timeout
        self.think = think
        self._client = AsyncClient(host=self.base_url, timeout=timeout)

    async def generate(self, prompt: str, schema: dict | None = None) -> str:
        try:
            response = await self._client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_ctx": self.num_ctx,
                },
                format=schema if schema else None,
                think=self.think,
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
