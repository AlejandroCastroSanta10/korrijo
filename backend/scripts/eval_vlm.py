"""Evalúa y compara modelos de visión (OCR) del pipeline de Korrijo.

Para cada modelo candidato y cada examen del dataset:
  - transcribe el examen con transcribe_exam (el mismo camino que en producción),
  - mide el tiempo de transcripción y la VRAM pico durante el proceso,
  - calcula CER y WER contra la transcripción de referencia manual.

La comparación normaliza ambos textos para NO penalizar diferencias de
mayúsculas, tildes, puntuación, espacios ni saltos de línea: solo cuenta el
contenido. El CER se calcula sobre el texto sin espacios y el WER sobre las
palabras del texto normalizado.

Requiere:
    - Ollama corriendo en OLLAMA_BASE_URL con los modelos descargados, p. ej.:
        ollama pull qwen2.5vl:7b
        ollama pull qwen3-vl:8b-instruct
        ollama pull minicpm-v4.5:8b
    - jiwer instalado (está en requirements-dev.txt).
    - nvidia-smi disponible para medir la VRAM (si no está, se omite ese dato).

Uso (desde backend/, con el entorno activado):
    python scripts/eval_vlm.py
    python scripts/eval_vlm.py --models qwen2.5vl:7b minicpm-v4.5:8b
    python scripts/eval_vlm.py --dataset ../docs/dataset-korrijo --out ./salida_ocr
    # Un solo modelo sobre un solo examen (p. ej. para repetir uno que falló):
    python scripts/eval_vlm.py --models qwen3-vl:8b-instruct --examenes prueba_3_alejandro --out ./salida_ocr
"""

import argparse
import asyncio
import csv
import re
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jiwer

from app.pipeline.errors import OllamaUnavailableError, ProviderTimeoutError
from app.pipeline.transcription import transcribe_exam
from app.pipeline.vlm.ollama import OllamaVLMProvider

# Errores que suelen ser transitorios (el servidor se recupera solo): se reintenta.
_ERRORES_TRANSITORIOS = (OllamaUnavailableError, ProviderTimeoutError)

DEFAULT_MODELS = ["qwen2.5vl:7b", "qwen3-vl:8b-instruct", "minicpm-v4.5:8b"]
DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "docs" / "dataset-korrijo"

_EXTENSIONES_EXAMEN = {".pdf", ".jpg", ".jpeg", ".png"}
_MARCADOR_PAGINA = re.compile(r"---\s*p[aá]gina\s*\d+\s*---", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# Normalización y métricas
# --------------------------------------------------------------------------- #


def normalizar(texto: str) -> str:
    """Deja solo el contenido: sin mayúsculas, tildes, puntuación ni espacios extra."""
    texto = _MARCADOR_PAGINA.sub(" ", texto)           # quita "--- Página N ---"
    texto = texto.lower()                              # ignora mayúsculas/minúsculas
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))  # quita tildes
    texto = re.sub(r"[^\w\s]", " ", texto)             # quita puntuación (mantiene letras y dígitos)
    return re.sub(r"\s+", " ", texto).strip()          # colapsa espacios y saltos de línea


def calcular_metricas(referencia: str, hipotesis: str) -> tuple[float, float]:
    """Devuelve (CER, WER) entre la referencia y la hipótesis ya normalizadas."""
    ref = normalizar(referencia)
    hyp = normalizar(hipotesis)
    wer = jiwer.wer(ref, hyp)
    cer = jiwer.cer(ref.replace(" ", ""), hyp.replace(" ", ""))
    return cer, wer


# --------------------------------------------------------------------------- #
# Medición de coste (VRAM pico)
# --------------------------------------------------------------------------- #


class MuestreadorVRAM:
    """Muestrea la VRAM usada (MiB) en un hilo y guarda el pico.

    Mide el total de la GPU, así que conviene tener solo Ollama usándola para
    que la medida sea representativa del modelo.
    """

    def __init__(self, intervalo: float = 0.1) -> None:
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
    """Saca el modelo de la VRAM para que la medición del siguiente sea limpia."""
    try:
        subprocess.run(
            ["ollama", "stop", model],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Descubrimiento del dataset y evaluación
# --------------------------------------------------------------------------- #


def sanear(nombre: str) -> str:
    """Convierte un nombre de modelo en algo válido para una carpeta."""
    return re.sub(r"[^\w.-]", "_", nombre)


def descubrir_examenes(dataset: Path) -> list[tuple[Path, Path, str]]:
    """Localiza (examen, referencia, id) para cada examen del dataset.

    Empareja prueba_X/a_corregir/examen_<persona>.* con su transcripción de
    referencia prueba_X/a_corregir/transcripciones/transcripcion_<persona>.txt.
    """
    examenes: list[tuple[Path, Path, str]] = []
    for exam_path in sorted(dataset.glob("prueba_*/a_corregir/examen_*")):
        if exam_path.suffix.lower() not in _EXTENSIONES_EXAMEN:
            continue
        persona = exam_path.stem.replace("examen_", "")
        ref_path = exam_path.parent / "transcripciones" / f"transcripcion_{persona}.txt"
        if not ref_path.exists():
            print(f"  AVISO: sin referencia para {exam_path.name}, se omite.", file=sys.stderr)
            continue
        prueba = exam_path.parent.parent.name
        examenes.append((exam_path, ref_path, f"{prueba}_{persona}"))
    return examenes


async def transcribir_con_reintentos(
    exam_path: Path,
    provider: OllamaVLMProvider,
    reintentos: int = 2,
    espera: float = 20.0,
) -> str:
    """Transcribe reintentando ante caídas transitorias del servidor."""
    for intento in range(1, reintentos + 2):
        try:
            return await transcribe_exam(exam_path, provider)
        except _ERRORES_TRANSITORIOS as exc:
            if intento > reintentos:
                raise
            print(
                f"    (aviso: {type(exc).__name__}; reintento {intento}/{reintentos} "
                f"en {espera:.0f}s. Si Ollama se cayó, dale tiempo a reiniciarse.)"
            )
            await asyncio.sleep(espera)
    raise RuntimeError("inalcanzable")  # pragma: no cover


async def evaluar_modelo(
    model: str,
    examenes: list[tuple[Path, Path, str]],
    out_dir: Path,
) -> list[dict]:
    """Transcribe todos los exámenes con un modelo y devuelve una fila por examen.

    Es tolerante a fallos: si un examen falla (incluso tras reintentar), se
    registra con error y se continúa con el resto.
    """
    provider = OllamaVLMProvider(model=model)
    dir_trans = out_dir / "transcripciones_generadas" / sanear(model)
    dir_trans.mkdir(parents=True, exist_ok=True)

    # Calentamiento: la primera transcripción carga el modelo en VRAM y no se
    # mide, para que los tiempos reflejen la inferencia y no la carga.
    print(f"  Calentando {model}...")
    try:
        await transcribir_con_reintentos(examenes[0][0], provider)
    except Exception as exc:  # noqa: BLE001 - queremos seguir con el resto
        print(f"    (aviso: falló el calentamiento: {exc})")

    filas: list[dict] = []
    for exam_path, ref_path, examen_id in examenes:
        try:
            with MuestreadorVRAM() as vram:
                inicio = time.perf_counter()
                hipotesis = await transcribir_con_reintentos(exam_path, provider)
                segundos = time.perf_counter() - inicio
        except Exception as exc:  # noqa: BLE001 - un examen no debe tirar la evaluación
            print(f"    {examen_id:<22} ERROR: {exc}")
            filas.append(
                {"modelo": model, "examen": examen_id, "cer": "", "wer": "",
                 "segundos": "", "vram_pico_mb": "", "error": str(exc)}
            )
            continue

        (dir_trans / f"{examen_id}.txt").write_text(hipotesis, encoding="utf-8")
        cer, wer = calcular_metricas(ref_path.read_text(encoding="utf-8"), hipotesis)

        fila = {
            "modelo": model,
            "examen": examen_id,
            "cer": round(cer, 4),
            "wer": round(wer, 4),
            "segundos": round(segundos, 2),
            "vram_pico_mb": round(vram.pico_mb) if vram.pico_mb is not None else "",
            "error": "",
        }
        filas.append(fila)
        print(
            f"    {examen_id:<22} CER={cer:6.4f}  WER={wer:6.4f}  "
            f"t={segundos:6.1f}s  VRAM={fila['vram_pico_mb']}MiB"
        )

    descargar_modelo(model)
    return filas


def _media(valores: list[float]) -> float | str:
    return round(sum(valores) / len(valores), 4) if valores else ""


def resumir(model: str, filas: list[dict]) -> dict:
    ok = [f for f in filas if f["cer"] != ""]  # solo exámenes bien transcritos
    vram = [f["vram_pico_mb"] for f in ok if f["vram_pico_mb"] != ""]
    return {
        "modelo": model,
        "examenes_ok": f"{len(ok)}/{len(filas)}",
        "cer_medio": _media([f["cer"] for f in ok]),
        "wer_medio": _media([f["wer"] for f in ok]),
        "segundos_medio": round(sum(f["segundos"] for f in ok) / len(ok), 2) if ok else "",
        "vram_pico_medio_mb": round(sum(vram) / len(vram)) if vram else "",
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="Modelos de visión a comparar.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Raíz del dataset.")
    parser.add_argument("--out", default=None, help="Carpeta de salida (por defecto <dataset>/resultados_ocr).")
    parser.add_argument(
        "--examenes",
        nargs="+",
        default=None,
        help="IDs de examen a evaluar (p. ej. prueba_3_alejandro). Por defecto, todos.",
    )
    args = parser.parse_args()

    dataset = Path(args.dataset).resolve()
    out_dir = Path(args.out).resolve() if args.out else dataset / "resultados_ocr"
    out_dir.mkdir(parents=True, exist_ok=True)

    examenes = descubrir_examenes(dataset)
    if not examenes:
        print(f"No se encontraron exámenes con referencia en {dataset}", file=sys.stderr)
        return 1

    if args.examenes:
        pedidos = set(args.examenes)
        disponibles = {e[2] for e in examenes}
        for falta in sorted(pedidos - disponibles):
            print(f"AVISO: no existe el examen '{falta}'.", file=sys.stderr)
        examenes = [e for e in examenes if e[2] in pedidos]
        if not examenes:
            print(f"Exámenes disponibles: {', '.join(sorted(disponibles))}", file=sys.stderr)
            return 1

    print(f"Exámenes: {len(examenes)} | Modelos: {', '.join(args.models)}")
    print(f"Salida: {out_dir}\n")

    detalle_csv = out_dir / "resultados_ocr_detalle.csv"
    resumen_csv = out_dir / "resultados_ocr_resumen.csv"
    campos_detalle = ["modelo", "examen", "cer", "wer", "segundos", "vram_pico_mb", "error"]
    campos_resumen = ["modelo", "examenes_ok", "cer_medio", "wer_medio", "segundos_medio", "vram_pico_medio_mb"]

    todas_filas: list[dict] = []
    resumen: list[dict] = []
    for model in args.models:
        print(f"=== Modelo: {model} ({len(examenes)} exámenes) ===")
        filas = await evaluar_modelo(model, examenes, out_dir)
        todas_filas.extend(filas)
        resumen.append(resumir(model, filas))
        # Se escribe tras cada modelo para no perder el progreso si algo falla.
        _volcar_csv(detalle_csv, campos_detalle, todas_filas)
        _volcar_csv(resumen_csv, campos_resumen, resumen)
        print()

    print("=== RESUMEN (medias por modelo, solo exámenes OK) ===")
    print(f"{'modelo':<24}{'OK':>6}{'CER':>8}{'WER':>8}{'t(s)':>9}{'VRAM(MiB)':>12}")
    for r in resumen:
        print(
            f"{r['modelo']:<24}{r['examenes_ok']:>6}{str(r['cer_medio']):>8}"
            f"{str(r['wer_medio']):>8}{str(r['segundos_medio']):>9}{str(r['vram_pico_medio_mb']):>12}"
        )
    print(f"\nDetalle: {detalle_csv}\nResumen: {resumen_csv}")
    return 0


def _volcar_csv(ruta: Path, campos: list[str], filas: list[dict]) -> None:
    with ruta.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
