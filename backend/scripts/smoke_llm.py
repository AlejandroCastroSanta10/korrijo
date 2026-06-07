"""Smoke test de los proveedores LLM y VLM contra un Ollama real.

Requiere:
    - Ollama corriendo en OLLAMA_BASE_URL.
    - Los modelos descargados:
        ollama pull <PIPELINE_LLM_MODEL>
        ollama pull <PIPELINE_VLM_MODEL>

Uso:
    Ejecutar este archivo individualmente

Si no se quiere probar el VLM (más lento), poner como argumento --skip-vlm.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.llm.ollama import OllamaLLMProvider
from app.pipeline.vlm.ollama import OllamaVLMProvider

SAMPLE_IMAGE = Path(__file__).parent / "pipeline_poc" / "examen_prueba.jpeg"


async def smoke_llm() -> int:
    provider = OllamaLLMProvider()
    print(f"[LLM] modelo: {provider.model} @ {provider.base_url}")
    response = await provider.generate("Responde 'OK' y nada más.")
    print(f"[LLM] respuesta: {response!r}")
    if not response.strip():
        print("[LLM] ERROR: respuesta vacía", file=sys.stderr)
        return 1
    return 0


async def smoke_vlm() -> int:
    provider = OllamaVLMProvider()
    print(f"[VLM] modelo: {provider.model} @ {provider.base_url}")
    response = await provider.transcribe(
        [SAMPLE_IMAGE.read_bytes()], "Describe la imagen brevemente." # Nos sirve para probar
    )
    print(f"[VLM] respuesta: {response!r}")
    if not response.strip():
        print("[VLM] ERROR: respuesta vacía", file=sys.stderr)
        return 1
    return 0


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-vlm", action="store_true", help="No probar el VLM")
    args = parser.parse_args()

    rc = await smoke_llm()
    if rc != 0:
        return rc

    if args.skip_vlm:
        return 0
    return await smoke_vlm()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(asyncio.run(main()))
