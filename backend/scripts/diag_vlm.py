"""Diagnóstico de rendimiento del VLM de transcripción.

Llama a Ollama EXACTAMENTE como lo hace el provider (format="json",
think=False, mismas opciones) y desglosa dónde se va el tiempo:

    - prefill (procesar la imagen del examen)
    - generación (tokens de salida) y tokens/s
    - si el modelo está volcando razonamiento en el canal `thinking`
      (la causa nº1 de que un VLM "rápido" pase a tardar minutos).

Uso (desde backend/, con el entorno activado):
    python scripts/diag_vlm.py <ruta_al_examen>        # como en producción
    python scripts/diag_vlm.py <ruta> --think           # fuerza thinking ON
    python scripts/diag_vlm.py <ruta> --no-format        # sin format="json"
    python scripts/diag_vlm.py                           # examen de prueba

Admite PDF (escaneado o no) e imágenes .jpg/.jpeg/.png.
"""

import argparse
import asyncio
import base64
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ollama import AsyncClient

from app.core.config import settings
from app.pipeline.prompts.transcription import TRANSCRIPTION_PROMPT
from app.pipeline.utils import pdf_to_images

DEFAULT_EXAM = Path(__file__).parent / "pipeline_poc" / "examen_prueba.jpeg"
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_NS = 1_000_000_000


def _load_images(path: Path) -> list[bytes]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return pdf_to_images(path)
    if suffix in _IMAGE_EXTENSIONS:
        return [path.read_bytes()]
    raise SystemExit(f"Formato no soportado: {suffix or path}")


def _fmt(ns: int | None) -> str:
    return f"{ns / _NS:.1f}s" if ns else "—"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exam", nargs="?", default=str(DEFAULT_EXAM))
    parser.add_argument("--think", action="store_true", help="Razonamiento ON")
    parser.add_argument("--no-format", action="store_true", help="Sin format=json")
    args = parser.parse_args()

    exam_path = Path(args.exam)
    if not exam_path.exists():
        print(f"No existe el fichero: {exam_path}", file=sys.stderr)
        return 1

    model = settings.pipeline_vlm_model
    images = _load_images(exam_path)
    encoded = [base64.b64encode(img).decode() for img in images]
    think = True if args.think else False
    fmt = None if args.no_format else "json"

    print(f"Examen:   {exam_path}  ({len(images)} pág., {len(images[0]) // 1024} KB/pág aprox.)")
    print(f"Modelo:   {model} @ {settings.ollama_base_url}")
    print(f"num_ctx:  {settings.pipeline_vlm_num_ctx}   think={think}   format={fmt!r}")
    print("Lanzando... (mide tiempos reales, sé paciente)\n")

    client = AsyncClient(host=settings.ollama_base_url, timeout=600.0)
    started = time.perf_counter()
    response = await client.chat(
        model=model,
        messages=[{"role": "user", "content": TRANSCRIPTION_PROMPT, "images": encoded}],
        options={
            "temperature": 0.0,
            "top_p": 0.9,
            "num_ctx": settings.pipeline_vlm_num_ctx,
        },
        format=fmt,
        think=think,
    )
    wall = time.perf_counter() - started

    prompt_tokens = response.prompt_eval_count or 0
    gen_tokens = response.eval_count or 0
    gen_ns = response.eval_duration or 0
    tok_s = gen_tokens / (gen_ns / _NS) if gen_ns else 0
    thinking = (response.message.thinking or "").strip()
    content = response.message.content or ""

    print("=== TIEMPOS ===")
    print(f"  Total (wall):     {wall:.1f}s")
    print(f"  Carga modelo:     {_fmt(response.load_duration)}")
    print(f"  Prefill imagen:   {_fmt(response.prompt_eval_duration)}  ({prompt_tokens} tok)")
    print(f"  Generación:       {_fmt(gen_ns)}  ({gen_tokens} tok, {tok_s:.1f} tok/s)")

    print("\n=== ¿ESTÁ PENSANDO? ===")
    if thinking:
        print(f"  ⚠️  SÍ: {len(thinking)} chars en el canal `thinking`.")
        print("      => think=False NO se respeta en tu Ollama/modelo. Ahí está el tiempo.")
        print(f"      Primeras líneas:\n      {thinking[:300]!r}")
    else:
        print("  ✔  No hay contenido en `thinking`.")

    print(f"\n=== CONTENT ({len(content)} chars) ===")
    print(content if content else "  (VACÍO)")

    try:
        import json

        answers = json.loads(content).get("answers", [])
        print(f"\n=== RESPUESTAS PARSEADAS: {len(answers)} ===")
        for a in answers:
            txt = (a.get("answer_text") or "").strip()
            print(f"  P{a.get('question_number')}: {len(txt)} chars  {txt[:80]!r}")
    except (ValueError, AttributeError, TypeError):
        print("\n(no se pudo parsear el JSON para contar respuestas)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
