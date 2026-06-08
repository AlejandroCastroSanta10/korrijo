"""Orquestador del pipeline completo de corrección.

Korrijo (ver los wireframes) trabaja en dos fases que NO se mezclan:

    A. SESIÓN — el profesor aporta una sola vez su material (rúbrica, examen
       modelo, contexto e indicaciones) y se fija la puntuación máxima. Ese
       material se PASA a texto una única vez: es común a todos los exámenes
       de la sesión.
    B. CORRECCIÓN POR EXAMEN — dentro de la sesión se van subiendo exámenes
       manuscritos; cada uno se TRANSCRIBE (VLM) y se CORRIGE (LLM textual)
       reutilizando el material ya extraído de la sesión.

De ahí la división de este módulo:

    * prepare_session(...) -> CorrectionSession   (fase 1, extracción una vez)
    * correct_exam(session, exam, ...) -> PipelineResult   (fase 2, por cada examen)

run_pipeline(...) es auxiliar para pruebas y encadena ambas para corregir VARIOS
exámenes de principio a fin; la usa el script app/pipeline/run.py (v0.3.0, sin
frontend) para poder probar la funcionalidad principal desde línea de comandos.

En v0.4.0 se llamará (desde endpoints) a prepare_session al crear la sesión y
a correct_exam por cada examen subido :). Estas son las funciones IMPORTANTES.
"""

import asyncio
import contextlib
import logging
import time
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, Field

from app.pipeline.errors import ProviderError
from app.pipeline.extractors.router import (
    ScannedPDFNotSupportedError,
    UnsupportedFormatError,
    extract,
)
from app.pipeline.grading import GradingError, GradingResult, grade_exam
from app.pipeline.llm.base import LLMProvider
from app.pipeline.llm.ollama import OllamaLLMProvider
from app.pipeline.transcription import (
    StructuredTranscription,
    TranscriptionError,
    transcribe_exam,
)
from app.pipeline.vlm.base import VLMProvider
from app.pipeline.vlm.ollama import OllamaVLMProvider

logger = logging.getLogger(__name__)

# num_ctx generoso por defecto para el LLM ya que es largo el prompt.
_DEFAULT_LLM_NUM_CTX = 16384

# Separador con el que se concatenan varios ficheros de contexto extraídos.
_CONTEXT_SEPARATOR = "\n\n---\n\n"


class PipelineError(Exception):
    """Una fase del pipeline ha fallado."""

    def __init__(self, phase: str, message: str) -> None:
        self.phase = phase
        super().__init__(f"[{phase}] {message}")


# --------------------------------------------------------------------------- #
# Modelo de datos
# --------------------------------------------------------------------------- #

class CorrectionSession(BaseModel):
    """Material del profesor ya extraído a texto, común a toda una sesión."""

    rubric_text: str
    model_exam_text: str = ""
    context_text: str | None = None
    teacher_instructions: str | None = None
    max_score: float


class PhaseTimings(BaseModel):
    """Tiempos de cada fase, en segundos."""

    extraction_seconds: float = 0.0
    transcription_seconds: float
    grading_seconds: float
    total_seconds: float


class PipelineMetadata(BaseModel):
    """Metadatos de ejecución de la corrección de un examen."""

    vlm_model: str
    llm_model: str
    timings: PhaseTimings
    # VRAM en pico (MiB) medida con nvidia-smi durante las fases con GPU.
    # None si no hay GPU NVIDIA o nvidia-smi no está disponible.
    peak_vram_mb: float | None = None


class PipelineResult(BaseModel):
    """Resultado de corregir un examen: transcripción, corrección y metadatos."""

    transcription: StructuredTranscription
    grading: GradingResult
    metadata: PipelineMetadata


class ExamRun(BaseModel):
    """Un examen dentro de una tanda: su resultado, o el error si falló."""

    exam: str
    result: PipelineResult | None = None
    error: str | None = None


class PipelineRun(BaseModel):
    """Resultado de corregir una tanda de exámenes con un mismo material."""
    max_score: float
    extraction_seconds: float
    exams: list[ExamRun] = Field(default_factory=list)
    total_seconds: float


# --------------------------------------------------------------------------- #
# Fase 1: creación de la sesión
# --------------------------------------------------------------------------- #

def prepare_session(
    rubric_path: str | Path,
    max_score: float,
    *,
    model_exam_path: str | Path,
    context_paths: Sequence[str | Path] = (),
    teacher_instructions: str | None = None,
) -> CorrectionSession:
    """Extrae el material del profesor a texto y arma una CorrectionSession.

    Es la fase 1: se ejecuta UNA vez por sesión. El resultado se reutiliza luego
    en correct_exam para cada examen, sin volver a extraer.

    Parámetros:
        rubric_path: Rúbrica (documento nativo: pdf/xlsx/txt/md/csv). Obligatoria.
        max_score: puntuación máxima del examen. Debe ser > 0.
        model_exam_path: Examen modelo de referencia (documento nativo). Obligatorio.
        context_paths: Ficheros de contexto opcionales (apuntes, temario...).
            Se extraen y concatenan en el orden dado.
        teacher_instructions: Indicaciones del profesor (opcionales) sobre contexto y/o examen modelo.

    Lanza:
        ValueError: si max_score <= 0.
        PipelineError(phase="extracción"): si algún documento no se puede leer
            o tiene un formato no soportado (el mensaje dice qué fichero falló).
    """
    if max_score <= 0:
        raise ValueError(f"max_score debe ser > 0, recibido {max_score}.")

    # 1. Extraemos la info de la rúbrica
    rubric_text = _extract_one(rubric_path, "la rúbrica")

    # 2. Extraemos la info de del examen modelo
    model_exam_text = _extract_one(model_exam_path, "el examen modelo")

    # 3. Si hay contexto, extraemos la info de cada uno de los ficheros
    context_parts = [
        _extract_one(path, "un fichero de contexto") for path in context_paths
    ]
    context_text = _CONTEXT_SEPARATOR.join(context_parts) if context_parts else None

    logger.info(
        "Sesión preparada | rúbrica=%d chars | modelo=%d chars | contexto=%s",
        len(rubric_text),
        len(model_exam_text),
        f"{len(context_text)} chars" if context_text else "—",
    )
    # TODO (pendiente): avisar si la suma de los ítems de la rúbrica no cuadra con
    # max_score. Requiere estructurar la rúbrica (texto libre) a ítems+puntos —no
    # se puede sumar de forma fiable con regex por los niveles por ítem—, así que
    # se aborda más adelante. Es una comprobación de sesión: su sitio es aquí.
    return CorrectionSession(
        rubric_text=rubric_text,
        model_exam_text=model_exam_text,
        context_text=context_text,
        teacher_instructions=teacher_instructions,  # Las instrucciones del profe van tal cual.
        max_score=max_score,
    )


def _extract_one(path: str | Path, label: str) -> str:
    """Extrae el texto de un fichero del profesor, contextualizando los errores."""
    try:
        return extract(path)
    except (UnsupportedFormatError, ScannedPDFNotSupportedError) as exc:
        raise PipelineError(
            "extracción", f"no se pudo procesar {label} ('{path}'): {exc}"
        ) from exc
    except (OSError, ValueError) as exc:
        raise PipelineError(
            "extracción", f"no se pudo leer {label} ('{path}'): {exc}"
        ) from exc


# --------------------------------------------------------------------------- #
# Fase 2: corrección de un examen (transcripción + corrección)
# --------------------------------------------------------------------------- #

async def correct_exam(
    session: CorrectionSession,
    exam_path: str | Path,
    *,
    vlm_provider: VLMProvider,
    llm_provider: LLMProvider,
) -> PipelineResult:
    """Transcribe y corrige UN examen con todo el material de la sesión.

    Parámetros:
        session: Material del profesor extraído (de la fase 1).
        exam_path: Examen manuscrito del alumno (PDF escaneado o imagen).
        vlm_provider: Proveedor de visión para la transcripción.
        llm_provider: Proveedor textual para la corrección.

    Devuelve:
        PipelineResult con la transcripción, la corrección y los metadatos de
        ejecución.

    Lanza:
        PipelineError: si falla la transcripción o la corrección. El atributo
            '.phase' indica cuál ("transcripción" o "corrección").
    """
    logger.info(
        "Corrigiendo %s | VLM=%s | LLM=%s",
        Path(exam_path).name,
        _model_name(vlm_provider),
        _model_name(llm_provider),
    )

    async with _VramSampler() as vram:
        # 1. Transcripción del examen del alumno (VLM).
        transcription_started = time.perf_counter()
        transcription = await _transcribe(exam_path, vlm_provider)
        transcription_seconds = time.perf_counter() - transcription_started
        logger.info(
            "Transcripción completada en %.2fs (%d respuestas)",
            transcription_seconds,
            len(transcription.answers),
        )

        # 2. Corrección contra el material de la sesión (LLM textual).
        grading_started = time.perf_counter()
        grading = await _grade(transcription, session, llm_provider)
        grading_seconds = time.perf_counter() - grading_started
        logger.info(
            "Corrección completada en %.2fs (nota %.2f/%.2f)",
            grading_seconds,
            grading.total_score,
            session.max_score,
        )

    metadata = PipelineMetadata(
        vlm_model=_model_name(vlm_provider),
        llm_model=_model_name(llm_provider),
        timings=PhaseTimings(
            transcription_seconds=transcription_seconds,
            grading_seconds=grading_seconds,
            total_seconds=transcription_seconds + grading_seconds,
        ),
        peak_vram_mb=vram.peak_mb,
    )
    return PipelineResult(
        transcription=transcription, grading=grading, metadata=metadata
    )


async def _transcribe(
    exam_path: str | Path, vlm: VLMProvider
) -> StructuredTranscription:
    """Transcribe el examen del alumno, contextualizando los errores."""
    try:
        return await transcribe_exam(exam_path, vlm)
    except TranscriptionError as exc:
        raise PipelineError(
            "transcripción", f"no se pudo transcribir el examen '{exam_path}': {exc}"
        ) from exc
    except ProviderError as exc:
        raise PipelineError(
            "transcripción", f"el proveedor de visión (VLM) falló: {exc}"
        ) from exc


async def _grade(
    transcription: StructuredTranscription,
    session: CorrectionSession,
    llm: LLMProvider,
) -> GradingResult:
    """Corrige el examen contra la info de la sesión, contextualizando los errores."""
    try:
        return await grade_exam(
            transcription,
            session.rubric_text,
            session.model_exam_text,
            session.max_score,
            llm,
            context_text=session.context_text,
            teacher_instructions=session.teacher_instructions,
        )
    except GradingError as exc:
        raise PipelineError("corrección", str(exc)) from exc
    except ProviderError as exc:
        raise PipelineError(
            "corrección", f"el proveedor textual (LLM) falló: {exc}"
        ) from exc


def _model_name(provider: object) -> str:
    """Nombre del modelo de un proveedor, tolerante con fakes sin atributo."""
    return getattr(provider, "model", None) or "desconocido"


# ----------------------------------------------------------------------------------------------------- #
# AUXILIAR: Corregir una tanda de exámenes con un mismo material (fase 1 + fase 2). Para probar el pipeline
# ----------------------------------------------------------------------------------------------------- #

async def run_pipeline(
    exam_paths: Sequence[str | Path],
    rubric_path: str | Path,
    max_score: float,
    *,
    model_exam_path: str | Path,
    context_paths: Sequence[str | Path] = (),
    teacher_instructions: str | None = None,
    vlm_model: str | None = None,
    llm_model: str | None = None,
    vlm_provider: VLMProvider | None = None,
    llm_provider: LLMProvider | None = None,
) -> PipelineRun:
    """Prepara la sesión una vez y corrige una tanda de exámenes con ese material.

    Replica el flujo de una sesión de corrección: el material del profesor se
    extrae una sola vez (fase 1) y se reutiliza para cada examen (fase 2), igual
    que harán los endpoints en v0.4.0.

    Un examen que falla NO aborta la tanda: su error se recoge en su ExamRun y
    se sigue con el resto. En cambio, un fallo al preparar la sesión (extracción)
    sí se propaga, porque afecta a todos.

    Devuelve:
        Un PipelineRun

    Lanza:
        ValueError: si max_score <= 0
        PipelineError: si falla alguna fase
    """
    started = time.perf_counter()

    # Fase 1: material del profesor, una sola vez para toda la tanda.
    extraction_started = time.perf_counter()
    session = prepare_session(
        rubric_path,
        max_score,
        model_exam_path=model_exam_path,
        context_paths=context_paths,
        teacher_instructions=teacher_instructions,
    )
    extraction_seconds = time.perf_counter() - extraction_started

    vlm = vlm_provider or OllamaVLMProvider(model=vlm_model)
    llm = llm_provider or OllamaLLMProvider(model=llm_model, num_ctx=_DEFAULT_LLM_NUM_CTX)

    # Fase 2: corregir cada examen
    exams: list[ExamRun] = []
    for exam_path in exam_paths:
        name = Path(exam_path).name
        try:
            result = await correct_exam(
                session, exam_path, vlm_provider=vlm, llm_provider=llm
            )
        except PipelineError as exc:
            logger.warning("Examen '%s' falló: %s", name, exc)
            exams.append(ExamRun(exam=name, error=str(exc)))
            continue
        exams.append(ExamRun(exam=name, result=result))

    total_seconds = time.perf_counter() - started
    logger.info(
        "Tanda completa en %.2fs (%d exámenes, %d con error)",
        total_seconds,
        len(exams),
        sum(1 for e in exams if e.error is not None),
    )
    return PipelineRun(
        max_score=max_score,
        extraction_seconds=extraction_seconds,
        exams=exams,
        total_seconds=total_seconds,
    )


# --------------------------------------------------------------------------- #
# Medición de VRAM en pico (best-effort vía nvidia-smi)
# --------------------------------------------------------------------------- #

class _VramSampler:
    """Muestrea la VRAM usada (vía nvidia-smi) en segundo plano y guarda el pico.

    Se usa como context manager async: arranca una tarea que consulta nvidia-smi
    cada 'interval' segundos y registra el máximo de 'memory.used' entre las GPUs.
    Es best-effort: si nvidia-smi no está disponible o falla, peak_mb queda None
    y no se interrumpe el pipeline.
    """

    def __init__(self, interval: float = 1.0) -> None:
        self.interval = interval
        self.peak_mb: float | None = None
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def __aenter__(self) -> "_VramSampler":
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task

    async def _run(self) -> None:
        while not self._stop.is_set():
            used = await _query_vram_mb()
            if used is None:
                # Sin tooling de GPU: no tiene sentido seguir muestreando.
                return
            self.peak_mb = used if self.peak_mb is None else max(self.peak_mb, used)
            # Espera hasta el próximo muestreo, o corta antes si nos paran.
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval)

async def _query_vram_mb() -> float | None:
    """VRAM usada (MiB) según nvidia-smi: el máximo entre las GPUs. None si falla."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "nvidia-smi",
            "--query-gpu=memory.used",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
    except (FileNotFoundError, OSError):
        return None

    if proc.returncode != 0:
        return None

    values = [float(line) for line in stdout.decode().splitlines() if line.strip()]
    return max(values) if values else None
