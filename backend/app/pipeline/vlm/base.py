"""Interfaz abstracta de los proveedores de modelos de visión (VLM).

Mismo razonamiento que con LLMProvider: el pipeline de transcripción de
exámenes manuscritos consume VLMProvider y no sabe quién lo implementa.

Para añadir un nuevo proveedor de visión:

    class MiVLM(VLMProvider):
        def __init__(self, model: str, ...): ...

        async def transcribe(
            self, images: list[bytes], prompt: str, schema: dict
        ) -> str:
            # Subir imágenes al servicio, devolver la transcripción.
            ...
"""

from abc import ABC, abstractmethod


class VLMProvider(ABC):
    """Proveedor de inferencia de visión.

    Toda implementación debe traducir errores de transporte a las
    excepciones de app.pipeline.errors.
    """

    @abstractmethod
    async def transcribe(
        self, images: list[bytes], prompt: str, schema: dict
    ) -> str:
        """Transcribe las imágenes según las instrucciones del prompt.

        Parámetros:
            images: lista de imágenes en bytes. Una imagen
                por página de examen.
            prompt: instrucciones para el modelo.
            schema: JSON Schema de la estructura que debe devolver el modelo.
                La transcripción SIEMPRE se fuerza a esta forma (salida
                estructurada); no es opcional.

        Devuelve:
            La respuesta del modelo como string (JSON conforme a schema).
        """
