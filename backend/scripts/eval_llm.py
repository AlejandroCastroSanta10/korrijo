"""Evalúa y compara modelos textuales (corrección) del pipeline de Korrijo.

Para cada modelo candidato y cada examen del dataset:
  - corrige el examen (grade_exam) con el mismo proceso que Korrijo en producción,
  - mide el tiempo de corrección y la VRAM pico,
  - compara la nota total propuesta con la nota de referencia.

Se aísla el paso de CORRECCIÓN: todas las entradas se fijan e igualan entre
modelos, de modo que el candidato solo corrige (no estructura nada):
  - la transcripción se toma ya estructurada (transcripcion_<persona>.json,
    generada una vez con scripts/gen_transcripciones_estructuradas.py),
  - la rúbrica es la estructurada y validada (prueba_X/rubrica_estructurada.json),
    serializada igual que en producción (services/exams.py::_serialize_rubric).

Métricas de salida (por modelo): MAE de la nota (base 10), cumplimiento del
contraste (pares fuerte/flojo) y coste (tiempo de corrección y VRAM pico).

Requiere:
    - Haber ejecutado antes scripts/gen_transcripciones_estructuradas.py.
    - Ollama corriendo con los modelos descargados:
        ollama pull qwen3:8b
        ollama pull gemma4:12b
    - nvidia-smi para la VRAM (si no está, se omite ese dato).

Los resultados se ACUMULAN entre ejecuciones (por (modelo, examen)), así que la
evaluación puede lanzarse examen a examen —recomendable, porque hacerlo todo de
una vez con el razonamiento activado puede bloquear/saturar el servidor—:

Uso (desde backend/, con el entorno activado):
    python scripts/eval_llm.py                                   # todo de una vez
    python scripts/eval_llm.py --models qwen3:8b --examenes prueba_1_maria
    # o en bucle, un examen por invocación (el CSV se va completando):
    for e in prueba_1_maria prueba_1_aitana prueba_2_isabel ...; do \
        python scripts/eval_llm.py --examenes "$e"; done
"""

import argparse
import asyncio
import csv
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.errors import OllamaUnavailableError, ProviderTimeoutError
from app.pipeline.extractors.router import extract
from app.pipeline.grading import grade_exam
from app.pipeline.llm.ollama import OllamaLLMProvider
from app.pipeline.transcription import StructuredTranscription

DEFAULT_MODELS = ["qwen3:8b", "gemma4:12b"]
# Razonamiento (thinking) por modelo: qwen3 razona; gemma4 se ejecuta sin razonar.
THINK = {"qwen3:8b": True, "gemma4:12b": False}
NUM_CTX = 16384      # el prompt de corrección es largo (rúbrica + contexto + modelo + examen)
TIMEOUT = 900.0      # el razonamiento es lento; margen amplio para no cortar
DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "docs" / "dataset-korrijo"

_CONTEXT_SEPARATOR = "\n\n---\n\n"
_ERRORES_TRANSITORIOS = (OllamaUnavailableError, ProviderTimeoutError)


# --------------------------------------------------------------------------- #
# Réplica exacta de la construcción de la sesión en producción
# (services/exams.py::_serialize_rubric y ::_combine_instructions)
# --------------------------------------------------------------------------- #


def serialize_rubric(items: list[dict]) -> str:
    lines: list[str] = []
    for item in items:
        name = item.get("name", "")
        max_score = item.get("max_score", 0)
        description = item.get("description", "")
        head = f"- {name} ({max_score:g} puntos)"
        lines.append(f"{head}: {description}" if description else head)
    return "\n".join(lines)


def combine_instructions(context: str | None, model_exam: str | None) -> str | None:
    parts: list[str] = []
    if context and context.strip():
        parts.append(f"Sobre el contexto: {context.strip()}")
    if model_exam and model_exam.strip():
        parts.append(f"Sobre el examen modelo: {model_exam.strip()}")
    return "\n\n".join(parts) or None


def construir_material(prueba_dir: Path) -> dict:
    """Arma el material del profesor de una prueba, como haría la fase 1."""
    items = json.loads((prueba_dir / "rubrica_estructurada.json").read_text(encoding="utf-8"))
    rubric_text = serialize_rubric(items)
    model_exam_text = extract(prueba_dir / "gold_standard" / "gold_standard.pdf")

    context_parts: list[str] = []
    for f in sorted((prueba_dir / "contexto").glob("*")):
        if not f.is_file() or f.name == "indicaciones.txt":
            continue
        try:
            context_parts.append(extract(f))
        except Exception as exc:  # noqa: BLE001 - el contexto es opcional
            print(f"    AVISO: no se pudo extraer contexto '{f.name}': {exc}", file=sys.stderr)
    context_text = _CONTEXT_SEPARATOR.join(context_parts) if context_parts else None

    ctx_instr = _leer_si_existe(prueba_dir / "contexto" / "indicaciones.txt")
    model_instr = _leer_si_existe(prueba_dir / "gold_standard" / "indicaciones.txt")

    max_score = _leer_max_score(prueba_dir) or sum(i["max_score"] for i in items)

    return {
        "rubric_text": rubric_text,
        "model_exam_text": model_exam_text,
        "context_text": context_text,
        "teacher_instructions": combine_instructions(ctx_instr, model_instr),
        "max_score": float(max_score),
    }


def _leer_si_existe(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def _leer_max_score(prueba_dir: Path) -> float | None:
    for f in sorted(prueba_dir.glob("puntuacion*.txt")):
        token = f.read_text(encoding="utf-8").split()[0].replace(",", ".")
        return float(token)
    return None


# --------------------------------------------------------------------------- #
# Medición de VRAM pico
# --------------------------------------------------------------------------- #


class MuestreadorVRAM:
    """Muestrea la VRAM usada (MiB) en un hilo y guarda el pico."""

    def __init__(self, intervalo: float = 0.25) -> None:
        self.intervalo = intervalo
        self.pico_mb: float | None = None
        self._parar = threading.Event()
        self._hilo: threading.Thread | None = None

    @staticmethod
    def _leer() -> float | None:
        try:
            salida = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        valores = [float(x) for x in salida.split() if x.strip().isdigit()]
        return max(valores) if valores else None

    def _bucle(self) -> None:
        while not self._parar.is_set():
            valor = self._leer()
            if valor is not None and (self.pico_mb is None or valor > self.pico_mb):
                self.pico_mb = valor
            self._parar.wait(self.intervalo)

    def __enter__(self) -> "MuestreadorVRAM":
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._parar.set()
        if self._hilo:
            self._hilo.join()


def descargar_modelo(model: str) -> None:
    try:
        subprocess.run(
            ["ollama", "stop", model], check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Descubrimiento y corrección
# --------------------------------------------------------------------------- #


def sanear(nombre: str) -> str:
    return re.sub(r"[^\w.-]", "_", nombre)


def descubrir_examenes(dataset: Path) -> list[tuple[str, Path, Path]]:
    """(examen_id, prueba_dir, ruta_transcripcion_referencia) por cada examen."""
    examenes: list[tuple[str, Path, Path]] = []
    for prueba_dir in sorted(dataset.glob("prueba_*")):
        trans_dir = prueba_dir / "a_corregir" / "transcripciones"
        for txt in sorted(trans_dir.glob("transcripcion_*.txt")):
            persona = txt.stem.replace("transcripcion_", "")
            examenes.append((f"{prueba_dir.name}_{persona}", prueba_dir, txt))
    return examenes


def cargar_referencias(dataset: Path) -> dict[str, dict]:
    ref: dict[str, dict] = {}
    with (dataset / "notas_referencia.csv").open(encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            ref[fila["examen"]] = {
                "perfil": fila["perfil"],
                "nota": float(fila["nota_referencia"]),
            }
    return ref


async def corregir_con_reintentos(llm, material, transcription, reintentos=2, espera=20.0):
    """Corrige (solo grade_exam), reintentando ante caídas transitorias del servidor."""
    for intento in range(1, reintentos + 2):
        try:
            with MuestreadorVRAM() as vram:
                t0 = time.perf_counter()
                grading = await grade_exam(
                    transcription,
                    material["rubric_text"],
                    material["model_exam_text"],
                    material["max_score"],
                    llm,
                    context_text=material["context_text"],
                    teacher_instructions=material["teacher_instructions"],
                )
                t_correccion = time.perf_counter() - t0
            return grading, t_correccion, vram.pico_mb
        except _ERRORES_TRANSITORIOS as exc:
            if intento > reintentos:
                raise
            print(f"    (aviso: {type(exc).__name__}; reintento {intento}/{reintentos} en {espera:.0f}s)")
            await asyncio.sleep(espera)
    raise RuntimeError("inalcanzable")  # pragma: no cover


def cargar_transcripcion(ref_path: Path) -> StructuredTranscription:
    """Carga la transcripción estructurada (JSON) generada previamente."""
    return StructuredTranscription.model_validate(
        json.loads(ref_path.with_suffix(".json").read_text(encoding="utf-8"))
    )


async def evaluar_modelo(model, examenes, materiales, referencias, out_dir, acumulado, persistir) -> None:
    """Corrige cada examen con 'model' y va guardando cada resultado en 'acumulado'.

    Persiste tras cada examen (idempotente por (modelo, examen)), de modo que la
    evaluación se puede lanzar examen a examen sin perder ni pisar lo ya hecho.
    """
    think = THINK.get(model)
    llm = OllamaLLMProvider(model=model, num_ctx=NUM_CTX, timeout=TIMEOUT, think=think)
    dir_inf = out_dir / "informes" / sanear(model)
    dir_inf.mkdir(parents=True, exist_ok=True)

    print(f"  Calentando {model} (think={think})...")
    try:
        await llm.generate("Responde únicamente: ok", None)
    except Exception as exc:  # noqa: BLE001
        print(f"    (aviso: falló el calentamiento: {exc})")

    for examen_id, prueba_dir, ref_path in examenes:
        material = materiales[prueba_dir.name]
        ref = referencias.get(examen_id)
        if ref is None:
            print(f"    {examen_id:<22} SIN nota de referencia, se omite.", file=sys.stderr)
            continue

        try:
            transcription = cargar_transcripcion(ref_path)
            grading, t_corr, vram = await corregir_con_reintentos(llm, material, transcription)
        except Exception as exc:  # noqa: BLE001 - un examen no debe tirar la evaluación
            print(f"    {examen_id:<22} ERROR: {exc}")
            acumulado[(model, examen_id)] = {
                "modelo": model, "examen": examen_id, "perfil": ref["perfil"],
                "nota_ref": ref["nota"], "nota_10": "", "nota_bruta": "",
                "max_score": material["max_score"], "error_abs": "",
                "seg_correccion": "", "vram_pico_mb": "", "error": str(exc)}
            persistir()
            continue

        nota_10 = grading.total_score / material["max_score"] * 10
        error_abs = abs(nota_10 - ref["nota"])
        _guardar_informe(dir_inf / f"{examen_id}.txt", examen_id, model, grading,
                         material["max_score"], nota_10, ref["nota"])

        fila = {
            "modelo": model, "examen": examen_id, "perfil": ref["perfil"],
            "nota_ref": ref["nota"], "nota_10": round(nota_10, 3),
            "nota_bruta": round(grading.total_score, 3), "max_score": material["max_score"],
            "error_abs": round(error_abs, 3), "seg_correccion": round(t_corr, 2),
            "vram_pico_mb": round(vram) if vram is not None else "", "error": "",
        }
        acumulado[(model, examen_id)] = fila
        persistir()
        print(f"    {examen_id:<22} nota={nota_10:5.2f} (ref {ref['nota']:.2f})  "
              f"|err|={error_abs:.2f}  t={t_corr:6.1f}s  VRAM={fila['vram_pico_mb']}MiB")

    descargar_modelo(model)


def _guardar_informe(ruta, examen_id, model, grading, max_score, nota_10, ref) -> None:
    lineas = [
        f"Examen: {examen_id}", f"Modelo: {model}",
        f"Nota propuesta: {grading.total_score:g}/{max_score:g} ({nota_10:.2f}/10)",
        f"Nota de referencia: {ref}/10", "", "=== RÚBRICA RELLENADA ===",
    ]
    for item in grading.rubric_filled:
        lineas.append(f"- {item.item_name}: {item.assigned_score:g}/{item.max_score:g}")
        if item.comment:
            lineas.append(f"    {item.comment}")
    lineas += ["", "=== INFORME ===", grading.feedback_report or "(vacío)"]
    ruta.write_text("\n".join(lineas), encoding="utf-8")


def resumir(model: str, filas: list[dict]) -> dict:
    ok = [f for f in filas if f["nota_10"] != ""]
    vram = [f["vram_pico_mb"] for f in ok if f["vram_pico_mb"] != ""]

    # Contraste: por prueba, ¿el modelo puntuó más alto al perfil fuerte?
    pares: dict[str, dict[str, float]] = {}
    for f in ok:
        prueba = f["examen"].rsplit("_", 1)[0]
        pares.setdefault(prueba, {})[f["perfil"]] = f["nota_10"]
    completos = [p for p in pares.values() if "fuerte" in p and "flojo" in p]
    satisfechos = sum(1 for p in completos if p["fuerte"] > p["flojo"])

    mae = round(sum(f["error_abs"] for f in ok) / len(ok), 3) if ok else ""
    return {
        "modelo": model,
        "examenes_ok": f"{len(ok)}/{len(filas)}",
        "mae": mae,
        "contraste": f"{satisfechos}/{len(completos)}" if completos else "—",
        "seg_correccion_medio": round(sum(f["seg_correccion"] for f in ok) / len(ok), 2) if ok else "",
        "vram_pico_medio_mb": round(sum(vram) / len(vram)) if vram else "",
    }


def _volcar_csv(ruta: Path, campos: list[str], filas: list[dict]) -> None:
    with ruta.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(filas)


def _num(valor: str):
    return float(valor) if valor not in (None, "") else ""


def cargar_detalle(ruta: Path) -> dict:
    """Carga el detalle ya existente (para acumular entre ejecuciones)."""
    acumulado: dict = {}
    if not ruta.exists():
        return acumulado
    with ruta.open(encoding="utf-8") as f:
        for d in csv.DictReader(f):
            fila = {
                "modelo": d["modelo"], "examen": d["examen"], "perfil": d.get("perfil", ""),
                "nota_ref": _num(d.get("nota_ref", "")), "nota_10": _num(d.get("nota_10", "")),
                "nota_bruta": _num(d.get("nota_bruta", "")), "max_score": _num(d.get("max_score", "")),
                "error_abs": _num(d.get("error_abs", "")), "seg_correccion": _num(d.get("seg_correccion", "")),
                "vram_pico_mb": int(float(d["vram_pico_mb"])) if d.get("vram_pico_mb") else "",
                "error": d.get("error", ""),
            }
            acumulado[(fila["modelo"], fila["examen"])] = fila
    return acumulado


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="Modelos textuales a comparar.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Raíz del dataset.")
    parser.add_argument("--out", default=None, help="Carpeta de salida (por defecto <dataset>/resultados_llm).")
    parser.add_argument("--examenes", nargs="+", default=None, help="IDs de examen a evaluar. Por defecto, todos.")
    args = parser.parse_args()

    dataset = Path(args.dataset).resolve()
    out_dir = Path(args.out).resolve() if args.out else dataset / "resultados_llm"
    out_dir.mkdir(parents=True, exist_ok=True)

    examenes = descubrir_examenes(dataset)
    if args.examenes:
        pedidos = set(args.examenes)
        examenes = [e for e in examenes if e[0] in pedidos]
    if not examenes:
        print(f"No se encontraron exámenes en {dataset}", file=sys.stderr)
        return 1

    faltan = [eid for eid, _, ref in examenes if not ref.with_suffix(".json").exists()]
    if faltan:
        print(
            "Faltan transcripciones estructuradas para: " + ", ".join(faltan) + ".\n"
            "Ejecuta antes: python scripts/gen_transcripciones_estructuradas.py",
            file=sys.stderr,
        )
        return 1

    referencias = cargar_referencias(dataset)
    # El material del profesor es común a cada prueba: se arma una sola vez.
    materiales = {d.name: construir_material(d) for d in {e[1] for e in examenes}}

    detalle_csv = out_dir / "resultados_llm_detalle.csv"
    resumen_csv = out_dir / "resultados_llm_resumen.csv"
    campos_detalle = ["modelo", "examen", "perfil", "nota_ref", "nota_10", "nota_bruta",
                      "max_score", "error_abs", "seg_correccion", "vram_pico_mb", "error"]
    campos_resumen = ["modelo", "examenes_ok", "mae", "contraste", "seg_correccion_medio", "vram_pico_medio_mb"]

    # Se acumulan resultados de ejecuciones anteriores (permite lanzar examen a examen).
    acumulado = cargar_detalle(detalle_csv)

    def persistir() -> list[dict]:
        filas = [acumulado[k] for k in sorted(acumulado)]
        _volcar_csv(detalle_csv, campos_detalle, filas)
        modelos_orden: list[str] = []
        for r in filas:
            if r["modelo"] not in modelos_orden:
                modelos_orden.append(r["modelo"])
        resumen = [resumir(m, [r for r in filas if r["modelo"] == m]) for m in modelos_orden]
        _volcar_csv(resumen_csv, campos_resumen, resumen)
        return resumen

    print(f"Exámenes: {len(examenes)} | Modelos: {', '.join(args.models)}")
    print(f"Salida: {out_dir}\n")

    for model in args.models:
        print(f"=== Modelo: {model} ({len(examenes)} exámenes) ===")
        await evaluar_modelo(model, examenes, materiales, referencias, out_dir, acumulado, persistir)
        print()

    resumen = persistir()
    print("=== RESUMEN (por modelo, acumulado) ===")
    print(f"{'modelo':<16}{'OK':>6}{'MAE':>8}{'contraste':>11}{'t(s)':>9}{'VRAM(MiB)':>12}")
    for r in resumen:
        print(f"{r['modelo']:<16}{r['examenes_ok']:>6}{str(r['mae']):>8}{r['contraste']:>11}"
              f"{str(r['seg_correccion_medio']):>9}{str(r['vram_pico_medio_mb']):>12}")
    print(f"\nDetalle: {detalle_csv}\nResumen: {resumen_csv}\nInformes: {out_dir / 'informes'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
