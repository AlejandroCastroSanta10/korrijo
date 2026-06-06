"""Excepciones comunes a los proveedores de LLM y VLM.

Se centralizan aquí para que tanto el módulo llm como vlm puedan
reutilizarlas.
"""


class ProviderError(Exception):
    """Error genérico de un proveedor de inferencia."""


class OllamaUnavailableError(ProviderError):
    """No se ha podido contactar con el servidor de Ollama.

    Normalmente significa que Ollama no está corriendo en ollama_base_url.
    """


class ModelNotFoundError(ProviderError):
    """El modelo solicitado no está descargado en el servidor de Ollama.

    El mensaje incluye el comando ollama pull <modelo> para que se sepa 
    cómo resolverlo.
    """


class ProviderTimeoutError(ProviderError):
    """La inferencia ha tardado más que el timeout configurado."""
