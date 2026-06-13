"""Corrección de exámenes de alumnos (fase 2).

Cubre la parte que no es propia del endpoint: validar el fichero del examen y,
sobre todo, ejecutar el pipeline de corrección en segundo plano.

process_exam es la función importante, run_exam_in_background es el envoltorio
para correrlo en background.
"""

import contextlib
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models.exam import Exam, ExamStatus
from app.db.models.grading_result import GradingResult
from app.db.models.grading_session import GradingSession
from app.db.models.session_document import DocumentKind, SessionDocument
from app.db.session import AsyncSessionLocal
from app.pipeline.errors import ProviderError
from app.pipeline.llm.base import LLMProvider
from app.pipeline.llm.ollama import OllamaLLMProvider
from app.pipeline.orchestrator import (
    CorrectionSession,
    PipelineError,
    correct_exam,
)
from app.pipeline.vlm.base import VLMProvider
from app.pipeline.vlm.ollama import OllamaVLMProvider
from app.services.storage import LocalFileStorage
from app.services.storage.base import FileStorage, StorageError

logger = logging.getLogger(__name__)

# Formatos admitidos para el examen del alumno: PDF escaneado o imagen suelta.
EXAM_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

_CONTEXT_SEPARATOR = "\n\n---\n\n"


# --------------------------------------------------------------------------- #
# Helpers para la construcción de la CorrectionSession
# --------------------------------------------------------------------------- #

def _serialize_rubric(items: list[dict]) -> str:
    """Convierte la rúbrica estructurada y validada por el profesor a texto.

    Es la rúbrica que el pipeline de corrección consume (rubric_text).
    """
    lines: list[str] = []
    for item in items:
        name = item.get("name", "")
        max_score = item.get("max_score", 0)
        description = item.get("description", "")
        head = f"- {name} ({max_score:g} puntos)"
        lines.append(f"{head}: {description}" if description else head)
    return "\n".join(lines)


def _combine_instructions(context: str | None, model_exam: str | None) -> str | None:
    """Une las dos indicaciones del profesor en el bloque que espera el pipeline."""
    parts: list[str] = []
    if context and context.strip():
        parts.append(f"Sobre el contexto: {context.strip()}")
    if model_exam and model_exam.strip():
        parts.append(f"Sobre el examen modelo: {model_exam.strip()}")
    return "\n\n".join(parts) or None


def _build_correction_session(grading_session: GradingSession) -> CorrectionSession:
    docs: list[SessionDocument] = grading_session.documents
    rubric_doc = next((d for d in docs if d.kind == DocumentKind.RUBRIC), None)
    model_doc = next((d for d in docs if d.kind == DocumentKind.MODEL_EXAM), None)
    context_parts = [
        d.extracted_text
        for d in docs
        if d.kind == DocumentKind.CONTEXT and d.extracted_text
    ]

    if grading_session.rubric_structured:
        rubric_text = _serialize_rubric(grading_session.rubric_structured)
    else:
        rubric_text = (rubric_doc.extracted_text if rubric_doc else "") or ""

    return CorrectionSession(
        rubric_text=rubric_text,
        model_exam_text=(model_doc.extracted_text if model_doc else "") or "",
        context_text=_CONTEXT_SEPARATOR.join(context_parts) if context_parts else None,
        teacher_instructions=_combine_instructions(
            grading_session.context_instructions,
            grading_session.model_exam_instructions,
        ),
        max_score=grading_session.max_score,
    )


# --------------------------------------------------------------------------- #
# Procesamiento de un examen
# --------------------------------------------------------------------------- #

async def process_exam(
    exam_id: UUID,
    session: AsyncSession,
    storage: FileStorage,
    vlm: VLMProvider,
    llm: LLMProvider,
) -> None:
    """Corrige un examen y persiste el resultado, registrando cada paso."""
    exam = await session.get(Exam, exam_id)
    if exam is None:
        logger.error("process_exam: el examen %s no existe.", exam_id)
        return

    grading_session = (
        await session.execute(
            select(GradingSession)
            .options(selectinload(GradingSession.documents))
            .where(GradingSession.id == exam.session_id)
        )
    ).scalar_one()

    exam.status = ExamStatus.PROCESSING
    exam.started_at = datetime.now(UTC)
    await session.commit()
    logger.info("Examen %s (%s): PROCESSING.", exam_id, exam.filename)

    tmp_path: str | None = None
    try:
        correction = _build_correction_session(grading_session)

        content = await storage.read(exam.storage_path)
        with tempfile.NamedTemporaryFile(
            suffix=Path(exam.filename).suffix.lower(), delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        logger.info("Examen %s: lanzando el pipeline de corrección.", exam_id)
        result = await correct_exam(
            correction, tmp_path, vlm_provider=vlm, llm_provider=llm
        )
    except PipelineError as exc:
        await _mark_error(session, exam, str(exc))
        return
    except (StorageError, ValueError) as exc:
        await _mark_error(session, exam, f"No se pudo procesar el examen: {exc}")
        return
    except Exception as exc:  # red de seguridad: nunca dejar el examen colgado
        logger.exception("Examen %s: error inesperado durante la corrección.", exam_id)
        await _mark_error(session, exam, f"Error inesperado durante la corrección: {exc}")
        return
    finally:
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)

    session.add(
        GradingResult(
            exam_id=exam.id,
            total_score=result.grading.total_score,
            rubric_filled=[item.model_dump() for item in result.grading.rubric_filled],
            feedback_report=result.grading.feedback_report,
            transcription=result.transcription.model_dump(),
            pipeline_metadata=result.metadata.model_dump(),
        )
    )
    exam.status = ExamStatus.COMPLETED
    exam.completed_at = datetime.now(UTC)
    await session.commit()
    logger.info(
        "Examen %s: COMPLETED (nota %.2f/%.2f).",
        exam_id,
        result.grading.total_score,
        correction.max_score,
    )


async def _mark_error(session: AsyncSession, exam: Exam, message: str) -> None:
    """Marca el examen como error con un mensaje legible."""
    exam.status = ExamStatus.ERROR
    exam.error_message = message
    exam.completed_at = datetime.now(UTC)
    await session.commit()
    logger.warning("Examen %s: ERROR — %s", exam.id, message)


# --------------------------------------------------------------------------- #
# Envoltorio para el BackgroundTask
# --------------------------------------------------------------------------- #

async def run_exam_in_background(exam_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        try:
            storage = LocalFileStorage(settings.storage_root)
            vlm = OllamaVLMProvider(
                num_ctx=settings.pipeline_vlm_num_ctx,
                timeout=settings.pipeline_vlm_timeout,
            )
            llm = OllamaLLMProvider(
                num_ctx=settings.pipeline_llm_num_ctx,
                timeout=settings.pipeline_llm_timeout,
            )
        except ProviderError as exc:
            logger.error("Pipeline mal configurado para el examen %s: %s", exam_id, exc)
            exam = await session.get(Exam, exam_id)
            if exam is not None:
                await _mark_error(session, exam, f"Pipeline mal configurado: {exc}")
            return

        await process_exam(exam_id, session, storage, vlm, llm)
