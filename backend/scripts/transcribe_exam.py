"""Ejecuta la fase de transcripción sobre un examen real y muestra el resultado.

Requiere:
    - Ollama corriendo en OLLAMA_BASE_URL.
    - El modelo de visión descargado y configurado en PIPELINE_VLM_MODEL:
        ollama pull <PIPELINE_VLM_MODEL>

Uso (desde backend/, con el entorno activado):
    python scripts/transcribe_exam.py <ruta_al_examen>
    python scripts/transcribe_exam.py            # usa el examen de prueba por defecto

Admite PDF (escaneado o no) e imágenes .jpg/.jpeg/.png.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.transcription import StructuredTranscription, transcribe_exam
from app.pipeline.vlm.ollama import OllamaVLMProvider

DEFAULT_EXAM = Path(__file__).parent / "pipeline_poc" / "examen_prueba.jpeg"


def render(result: StructuredTranscription) -> None:
    print("\n=== METADATOS ===")
    for campo, valor in result.metadata.model_dump().items():
        print(f"  {campo}: {valor if valor is not None else '—'}")

    print(f"\n=== RESPUESTAS ({len(result.answers)}) ===")
    for ans in result.answers:
        print(f"\n  Pregunta {ans.question_number}:")
        print(f"  {ans.answer_text or '(en blanco)'}")
        if ans.notes:
            print(f"  [nota: {ans.notes}]")


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "exam",
        nargs="?",
        default=str(DEFAULT_EXAM),
        help="Ruta al examen (PDF o imagen). Por defecto, el examen de prueba.",
    )
    args = parser.parse_args()

    exam_path = Path(args.exam)
    if not exam_path.exists():
        print(f"No existe el fichero: {exam_path}", file=sys.stderr)
        return 1

    provider = OllamaVLMProvider()
    print(f"Examen: {exam_path}")
    print(f"Modelo: {provider.model} @ {provider.base_url}")
    print("Transcribiendo... (el VLM es lento, puede tardar un par de minutos)")

    result = await transcribe_exam(exam_path, provider)
    render(result)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
