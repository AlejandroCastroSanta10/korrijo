"""Interfaz abstracta de los proveedores de modelos de lenguaje (LLM).

Korrijo no debe atarse a un proveedor concreto. Toda la lógica del pipeline
de corrección consume LLMProvider y no sabe si por debajo hay un Ollama
local, un vLLM, un servidor remoto o un mock para tests.

Para añadir un nuevo proveedor basta con implementar esta interfaz en una nueva clase:

    class MiProvider(LLMProvider):
        def __init__(self, model: str, ...): ...

        async def generate(
            self, prompt: str, schema: dict | None = None
        ) -> str:
            # Llamar al servicio remoto, devolver el texto.
            ...
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Proveedor de inferencia textual.

    Toda implementación debe ser segura para usarse desde código async y
    debe traducir los errores del transporte (conexión caída, modelo
    inexistente, timeout) a las excepciones de app.pipeline.errors.
    """

    @abstractmethod
    async def generate(self, prompt: str, schema: dict | None = None) -> str:
        """Genera una respuesta textual a partir del prompt.

        Parámetros:
            prompt: texto completo enviado al modelo
            schema: JSON Schema opcional. Si se pasa, el proveedor pedirá
                al modelo que devuelva una respuesta que valide contra él
                (modo "JSON estructurado"). Cada implementación decide cómo
                comunicárselo al modelo (en Ollama, vía `format=schema`).

        Devuelve:
            La respuesta del modelo como string. Si schema no es None,
            el string contendrá JSON válido según ese schema.
        """
