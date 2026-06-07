"""Ejecuta la fase de corrección sobre inputs reales y muestra el resultado.

Encadena transcripción (VLM) + corrección (LLM) para iterar el prompt de
GRADING_PROMPT contra material real.

Requiere:
    - Ollama corriendo en OLLAMA_BASE_URL.
    - Modelo de visión en PIPELINE_VLM_MODEL y modelo textual en PIPELINE_LLM_MODEL:
        ollama pull <PIPELINE_VLM_MODEL>
        ollama pull <PIPELINE_LLM_MODEL>

Uso (desde backend/, con el entorno activado). Valores por defecto vs personalizarlos:
    python scripts/grade_exam.py
    python scripts/grade_exam.py --exam <img/pdf> --rubric <fichero> --model-exam <fichero>
    --context <fichero> --instructions "..." --max-score 10
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.extractors.router import extract
from app.pipeline.grading import GradingResult, grade_exam
from app.pipeline.llm.ollama import OllamaLLMProvider
from app.pipeline.transcription import transcribe_exam
from app.pipeline.vlm.ollama import OllamaVLMProvider

POC = Path(__file__).parent / "pipeline_poc"
DEFAULT_EXAM = POC / "examen_prueba.jpeg"
DEFAULT_RUBRIC = POC / "rubrica.md"
DEFAULT_MODEL_EXAM = POC / "examen_modelo.md"
DEFAULT_CONTEXT = POC / "contexto.md"
DEFAULT_INSTRUCTIONS = POC / "indicaciones.txt"


def render(result: GradingResult, max_score: float) -> None:
    print(f"\n=== NOTA TOTAL: {result.total_score} / {max_score} ===")

    print(f"\n=== RÚBRICA ({len(result.rubric_filled)} ítems) ===")
    for item in result.rubric_filled:
        print(f"\n  {item.item_name}: {item.assigned_score} / {item.max_score}")
        if item.comment:
            print(f"  {item.comment}")

    print("\n=== INFORME ===")
    print(result.feedback_report)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exam", default=str(DEFAULT_EXAM), help="Examen del alumno (PDF/imagen).")
    parser.add_argument("--rubric", default=str(DEFAULT_RUBRIC), help="Fichero de rúbrica.")
    parser.add_argument("--model-exam", default=str(DEFAULT_MODEL_EXAM), help="Examen modelo.")
    parser.add_argument("--context", default=str(DEFAULT_CONTEXT), help="Contexto (opcional).")
    parser.add_argument(
        "--instructions",
        default=None,
        help="Indicaciones del profesor (texto). Por defecto se leen de indicaciones.txt.",
    )
    parser.add_argument("--max-score", type=float, default=10.0, help="Puntuación máxima.")
    args = parser.parse_args()

    exam_path = Path(args.exam)
    if not exam_path.exists():
        print(f"No existe el examen: {exam_path}", file=sys.stderr)
        return 1

    rubric_text = extract(args.rubric)
    model_exam_text = extract(args.model_exam)
    context_text = extract(args.context) if Path(args.context).exists() else None

    instructions = args.instructions
    if instructions is None and DEFAULT_INSTRUCTIONS.exists():
        instructions = DEFAULT_INSTRUCTIONS.read_text(encoding="utf-8")

    vlm = OllamaVLMProvider()
    # num_ctx generoso: el prompt de corrección (rúbrica + contexto + modelo +
    # transcripción) es largo.
    llm = OllamaLLMProvider(num_ctx=16384)

    print(f"Examen: {exam_path}")
    print(f"VLM: {vlm.model} | LLM: {llm.model} @ {llm.base_url}")
    print("Transcribiendo el examen del alumno... (lento)")
    transcription = await transcribe_exam(exam_path, vlm)

    print("Corrigiendo... (lento)")
    result = await grade_exam(
        transcription,
        rubric_text,
        model_exam_text,
        args.max_score,
        llm,
        context_text=context_text,
        teacher_instructions=instructions,
    )
    render(result, args.max_score)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
