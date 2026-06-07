# Utilidades compartidas para el pipeline

import json
import re
from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path

"""
Convierte cada página de un PDF en un PNG en memoria,
útil cuando el documento no es un PDF nativo y hay que pasarlo por el
VLMProvider).
"""
def pdf_to_images(pdf_path: str | Path, dpi: int = 200) -> list[bytes]:
    """
    Parámetros:
        pdf_path: ruta al PDF.
        dpi: resolución de renderizado. 200 es un buen balance entre
            legibilidad del manuscrito y tamaño de la imagen.

    Devuelve:
        Una lista de bytes, una entrada por página, codificadas en PNG.
        Apta para pasarse a VLMProvider.transcribe.
    """
    pages = convert_from_path(str(pdf_path), dpi=dpi)
    result: list[bytes] = []
    for page in pages:
        buffer = BytesIO()
        page.save(buffer, format="PNG")
        result.append(buffer.getvalue())
    return result


# --------------------------------------------------------------------------- #
# Parseo robusto de la salida JSON de un modelo local
# --------------------------------------------------------------------------- #

"""
Los modelos servidos por Ollama (sin `format` nativo) suelen rodear el JSON de
ruido: bloques de razonamiento `<think>`, vallas de código markdown, preámbulos
de cortesía, comas finales o comillas tipográficas. parse_json_object extrae y
repara el primer objeto JSON de esa salida.

Lo comparten las fases del pipeline que piden JSON como salida en el prompt en lugar 
de usar salida estructurada nativa (transcripción y corrección).
"""

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_CODE_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


class JSONParseError(Exception):
    """La salida del modelo no contiene un objeto JSON parseable."""


def parse_json_object(raw: str) -> dict:
    """Extrae y parsea el objeto JSON de la respuesta del modelo.

    Tolera los desvíos típicos de un modelo local: bloques <think>, vallas de
    código markdown, preámbulos de texto, comas finales y comillas tipográficas.

    Lanza:
        JSONParseError: si la respuesta está vacía, no contiene ningún objeto
            JSON, o el objeto encontrado está tan malformado que no se puede
            reparar.
    """
    if not raw or not raw.strip():
        raise JSONParseError("El modelo devolvió una respuesta vacía.")

    text = _THINK_BLOCK.sub("", raw)

    fenced = _CODE_FENCE.search(text)
    if fenced:
        text = fenced.group(1)

    candidate = _extract_first_object(text)
    if candidate is None:
        raise JSONParseError(
            f"No se encontró ningún objeto JSON en la respuesta: {raw!r}"
        )

    for attempt in (candidate, _repair(candidate)):
        try:
            parsed = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
        raise JSONParseError(
            f"El JSON de la respuesta no es un objeto: {attempt!r}"
        )

    raise JSONParseError(
        f"El JSON de la respuesta está malformado y no se pudo reparar: {candidate!r}"
    )


def _extract_first_object(text: str) -> str | None:
    """Devuelve el primer objeto JSON balanceado del texto, o None.

    Recorre desde la primera llave de apertura contando profundidad y
    respetando las cadenas (para no confundir llaves dentro de strings).
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _repair(candidate: str) -> str:
    """Aplica reparaciones suaves a un JSON casi válido."""
    repaired = candidate
    # Comillas tipográficas a comillas rectas
    repaired = repaired.translate(
        str.maketrans({chr(0x201C): '"', chr(0x201D): '"', chr(0x2018): "'", chr(0x2019): "'"})
    )
    # Comas finales antes de } o ].
    repaired = _TRAILING_COMMA.sub(r"\1", repaired)
    return repaired
