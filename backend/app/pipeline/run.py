"""Punto de entrada de línea de comandos del pipeline de corrección. Para
hacer pruebas de la funcionalidad principal por línea de comandos.

Ejecuta el pipeline completo (extracción → transcripción → corrección) sobre una
tanda de exámenes (de una misma sesión) y vuelca el resultado en JSON. 
Es la forma de probar la funcionalidad principal de Korrijo sin frontend.

Ejecutar el script desde backend/, con el entorno activado. Argumentos de programa:

  Obligatorios:
    --exam FICHERO        Examen del alumno (PDF/imagen). Repetible (hasta 3).
    --rubric FICHERO      Rúbrica del profesor (pdf/xlsx/txt/md/csv).
    --model-exam FICHERO  Examen modelo / gold standard (documento nativo).
    --max-score N         Puntuación máxima (> 0).

  Opcionales:
    --context FICHERO     Documento de contexto (apuntes, temario...). Repetible.
    --instructions VALOR  Indicaciones del profesor: texto literal o ruta a fichero.
    --output FICHERO      Ruta donde guardar el resultado completo en JSON.
    --verbose             Logging detallado (DEBUG).

Ejemplo con todos los argumentos:
    python -m app.pipeline.run \\
        --exam alumno1.pdf --exam alumno2.pdf --exam alumno3.pdf \\
        --rubric rubrica.pdf --model-exam modelo.pdf \\
        --context apuntes.pdf --context temario.md \\
        --instructions indicaciones.txt \\
        --max-score 10 \\
        --output result.json --verbose
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.core.config import settings
from app.pipeline.extractors.router import UnsupportedFormatError, extract
from app.pipeline.orchestrator import PipelineError, PipelineRun, run_pipeline

logger = logging.getLogger("app.pipeline")

# Tope de exámenes por tanda en la herramienta de pruebas. La corrección es lenta
# (VLM + LLM por examen); más de esto no se podrá desde la interfaz por cada tanda.
_MAX_EXAMS = 3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.pipeline.run",
        description="Corrige una tanda de exámenes manuscritos de una sesión.",
    )

    parser.add_argument(
        "--exam",
        action="append",
        required=True,
        metavar="FICHERO",
        help=(
            f"Examen del alumno (PDF escaneado o imagen). Repetible "
            f"hasta {_MAX_EXAMS} veces para corregir varios con el mismo material."
        ),
    )

    parser.add_argument(
        "--rubric", required=True, help="Rúbrica del profesor (pdf/xlsx/txt/md/csv)."
    )

    parser.add_argument(
        "--model-exam",
        required=True,
        help="Examen modelo de referencia (documento nativo). Obligatorio.",
    )

    parser.add_argument(
        "--max-score",
        type=float,
        help="Puntuación máxima del examen (> 0).",
    )

    # ------------------------------------------------------------------------------------------

    parser.add_argument(
        "--context",
        action="append",
        default=[],
        metavar="FICHERO",
        help="Fichero de contexto (apuntes, temario...). Repetible. Opcional.",
    )

    parser.add_argument(
        "--instructions",
        help="Indicaciones del profesor: texto literal o ruta a un fichero. Opcional.",
    )
    
    parser.add_argument(
        "--output", help="Ruta donde guardar el resultado completo en JSON. Opcional."
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Activa logging detallado (DEBUG)."
    )

    return parser

def _fail(message: str) -> "int":
    """Imprime un error"""
    print(f"Error: {message}", file=sys.stderr)
    return 1

def _resolve_instructions(value: str | None) -> str | None:
    """Resuelve --instructions: si es una ruta a fichero, lo lee; si no, es texto."""
    if value is None:
        return None
    path = Path(value)
    if path.is_file():
        try:
            return extract(path)
        except UnsupportedFormatError:
            return path.read_text(encoding="utf-8")
    return value

def _validate_inputs(args: argparse.Namespace) -> tuple[str, str] | None:
    """Valida ficheros y argumentos."""
    if len(args.exam) > _MAX_EXAMS:
        return _fail(
            f"demasiados exámenes ({len(args.exam)}); el máximo es {_MAX_EXAMS}."
        ) and None
    for exam in args.exam:
        if not Path(exam).is_file():
            return _fail(f"no existe el examen: {exam}") and None
    if not Path(args.rubric).is_file():
        return _fail(f"no existe la rúbrica: {args.rubric}") and None
    if not Path(args.model_exam).is_file():
        return _fail(f"no existe el examen modelo: {args.model_exam}") and None
    for ctx in args.context:
        if not Path(ctx).is_file():
            return _fail(f"no existe el fichero de contexto: {ctx}") and None
    if args.max_score <= 0:
        return _fail(f"--max-score debe ser > 0 (recibido {args.max_score}).") and None

    vlm_model = args.vlm_model or settings.pipeline_vlm_model
    if not vlm_model:
        return _fail(
            "no hay modelo de visión. Pásalo con --vlm-model o configúralo en "
            "PIPELINE_VLM_MODEL (.env)."
        ) and None
    llm_model = args.llm_model or settings.pipeline_llm_model
    if not llm_model:
        return _fail(
            "no hay modelo textual. Pásalo con --llm-model o configúralo en "
            "PIPELINE_LLM_MODEL (.env)."
        ) and None

    return vlm_model, llm_model

def _render_summary(run: PipelineRun) -> None:
    """Imprime en consola un resumen de la tanda de corrección"""
    max_score = run.max_score

    for exam_run in run.exams:
        print(f"\n=== {exam_run.exam} ===")
        if exam_run.error is not None:
            print(f"  ERROR: {exam_run.error}")
            continue

        result = exam_run.result
        grading = result.grading
        timings = result.metadata.timings

        print(f"  Nota (orientativa): {grading.total_score} / {max_score}")
        print(f"  Rúbrica ({len(grading.rubric_filled)} ítems):")
        for item in grading.rubric_filled:
            print(f"    {item.item_name}: {item.assigned_score} / {item.max_score}")
            if item.comment:
                print(f"        {item.comment}")
        print(
            f"  Tiempos: transcripción {timings.transcription_seconds:.2f}s, "
            f"corrección {timings.grading_seconds:.2f}s"
        )
        if result.metadata.peak_vram_mb is not None:
            print(f"  VRAM en pico: {result.metadata.peak_vram_mb:.0f} MiB")

    corregidos = [e.result for e in run.exams if e.result is not None]
    fallidos = sum(1 for e in run.exams if e.error is not None)

    print("\n=== RESUMEN DE LA TANDA ===")
    print(f"  Exámenes: {len(run.exams)} ({len(corregidos)} corregidos, {fallidos} con error)")
    if corregidos:
        notas = [r.grading.total_score for r in corregidos]
        aprobados = sum(1 for n in notas if n >= max_score / 2)
        print(f"  Aprobados: {aprobados} | Suspensos: {len(corregidos) - aprobados}")
        print(f"  Nota media: {sum(notas) / len(notas):.2f} / {max_score}")
    print(f"  Extracción (1 vez): {run.extraction_seconds:.2f}s")
    print(f"  TOTAL tanda:        {run.total_seconds:.2f}s")


async def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    validated = _validate_inputs(args)
    if validated is None:
        return 1
    vlm_model, llm_model = validated

    instructions = _resolve_instructions(args.instructions)

    try:
        run = await run_pipeline(
            args.exam,
            args.rubric,
            args.max_score,
            model_exam_path=args.model_exam,
            context_paths=args.context,
            teacher_instructions=instructions,
            vlm_model=vlm_model,
            llm_model=llm_model,
        )
    except PipelineError as exc:
        logger.debug("Detalle del fallo del pipeline", exc_info=True)
        return _fail(str(exc))

    _render_summary(run)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        print(f"\nResultado completo guardado en: {output_path}")

    if not any(e.result is not None for e in run.exams):
        return _fail("ningún examen se pudo corregir (ver errores arriba).")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
