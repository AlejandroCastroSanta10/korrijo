"""Pre-genera las transcripciones estructuradas del dataset (una sola vez).

Estructura cada transcripción de referencia (transcripcion_<persona>.txt) con el
mismo paso que Korrijo (structure_transcription) y guarda el resultado como JSON
junto al .txt. Así, en la evaluación textual (eval_llm.py) la corrección parte de
una transcripción ya estructurada e IDÉNTICA para todos los modelos, sin que el
modelo candidato tenga que estructurarla: se aísla el paso de corrección.

La estructuración se hace SIN razonamiento (think=False), coherente con
PIPELINE_LLM_THINK=false. Es una tarea sencilla y el modelo empleado aquí no
influye en la comparación posterior (la estructura resultante es la misma para
ambos candidatos).

Requiere Ollama corriendo con el modelo descargado.

Uso (desde backend/, con el entorno activado):
    python scripts/gen_transcripciones_estructuradas.py
    python scripts/gen_transcripciones_estructuradas.py --model gemma4:12b
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.llm.ollama import OllamaLLMProvider
from app.pipeline.transcription import structure_transcription

DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "docs" / "dataset-korrijo"
DEFAULT_MODEL = "qwen3:8b"
NUM_CTX = 16384
TIMEOUT = 300.0


def descubrir(dataset: Path) -> list[Path]:
    return sorted(dataset.glob("prueba_*/a_corregir/transcripciones/transcripcion_*.txt"))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Raíz del dataset.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo que estructura (una sola vez, sin thinking).")
    parser.add_argument("--force", action="store_true", help="Regenera aunque ya exista el JSON.")
    args = parser.parse_args()

    dataset = Path(args.dataset).resolve()
    textos = descubrir(dataset)
    if not textos:
        print(f"No se encontraron transcripciones en {dataset}", file=sys.stderr)
        return 1

    llm = OllamaLLMProvider(model=args.model, num_ctx=NUM_CTX, timeout=TIMEOUT, think=False)
    print(f"Estructurando {len(textos)} transcripciones con {args.model} (think=False)\n")

    for txt in textos:
        destino = txt.with_suffix(".json")
        if destino.exists() and not args.force:
            print(f"  {txt.name:<32} ya existe (usa --force para regenerar)")
            continue
        transcription = await structure_transcription(txt.read_text(encoding="utf-8"), llm)
        destino.write_text(
            json.dumps(transcription.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  {txt.name:<32} -> {destino.name} ({len(transcription.answers)} respuestas)")

    print(f"\nListo. Transcripciones estructuradas junto a cada .txt.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
