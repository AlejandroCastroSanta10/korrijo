"""Endpoints de la fase 2: subida de exámenes y consulta de su corrección + Descarga de PDFs

La subida es asíncrona: se crea el examen en pending, se agenda la background
task y el resultado se consulta por polling.
"""

import logging
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response, UploadFile, status

from app.api.deps import CurrentUserDep, ExamRunnerDep, SessionDep, StorageDep
from app.api.sessions_common import load_session, owned_or_error, to_exam_detail
from app.core.config import settings
from app.db.models.exam import Exam, ExamStatus
from app.db.models.grading_session import GradingSession, SessionStatus
from app.schemas.session import ExamDetail, ExamRead
from app.services.exams import EXAM_ALLOWED_EXTENSIONS
from app.services.pdf_generator import (
    generate_feedback_report_pdf,
    generate_filled_rubric_pdf,
)
from app.services.storage.base import FileStorage, InvalidKey, StorageError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["exams"])

# Funciones auxiliares:
def _require_ready(grading_session: GradingSession) -> None:
    """Solo se corrigen exámenes cuando la sesión está en ready."""
    if grading_session.status != SessionStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La sesión no está en ready. No se pueden subir exámenes.",
        )


def _validate_exam(filename: str, content: bytes) -> None:
    """Valida extensión y tamaño del examen."""
    if Path(filename).suffix.lower() not in EXAM_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Formato no admitido para '{filename}'. "
                f"Admitidos: {', '.join(sorted(EXAM_ALLOWED_EXTENSIONS))}."
            ),
        )
    if len(content) > settings.max_exam_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "El examen supera el tamaño máximo permitido "
                f"({settings.max_exam_upload_bytes // (1024 * 1024)} MB)."
            ),
        )


# Endpoints de exámenes:
@router.post(
    "/{session_id}/exams",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=list[ExamRead],
)
async def upload_exams(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    storage: StorageDep,
    run_exam: ExamRunnerDep,
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
) -> list[ExamRead]:
    """Recibe hasta N exámenes, los guarda en pending y agenda su corrección."""
    grading_session = owned_or_error(await load_session(session, session_id), current_user)
    _require_ready(grading_session)

    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No se ha adjuntado ningún examen.",
        )
    if len(files) > settings.max_exams_per_upload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Máximo {settings.max_exams_per_upload} exámenes por subida.",
        )

    # Se validan todos antes de tocar el storage
    payloads: list[tuple[str, bytes]] = []
    for file in files:
        filename = file.filename or ""
        content = await file.read()
        _validate_exam(filename, content)
        payloads.append((filename, content))

    created: list[Exam] = []
    saved_keys: list[str] = []
    try:
        for filename, content in payloads:
            exam = Exam(
                session_id=grading_session.id,
                filename=filename,
                storage_path="",
                status=ExamStatus.PENDING,
            )
            session.add(exam)
            await session.flush()

            key = _exam_key(current_user.id, grading_session.id, exam.id, filename)
            await storage.save(content, key)
            saved_keys.append(key)
            exam.storage_path = key
            created.append(exam)
    except StorageError as exc:
        await session.rollback()
        await _cleanup(storage, saved_keys)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No se pudo guardar el examen: {exc}",
        ) from exc

    await session.commit()
    for exam in created:
        await session.refresh(exam)
        background_tasks.add_task(run_exam, exam.id)

    logger.info(
        "Sesión %s: %d examen(es) en cola de corrección.", session_id, len(created)
    )
    return [
        ExamRead(
            id=exam.id,
            filename=exam.filename,
            status=exam.status,
            created_at=exam.created_at,
        )
        for exam in created
    ]


@router.get("/{session_id}/exams/{exam_id}", response_model=ExamDetail)
async def get_exam_detail(
    session_id: UUID,
    exam_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ExamDetail:
    """Detalle del examen, con su resultado si la corrección ha terminado."""
    grading_session = owned_or_error(await load_session(session, session_id), current_user)
    exam = next((e for e in grading_session.exams if e.id == exam_id), None)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return to_exam_detail(exam)


@router.get("/{session_id}/exams/{exam_id}/rubric.pdf")
async def download_rubric_pdf(
    session_id: UUID,
    exam_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> Response:
    """Descarga el PDF de la rúbrica rellenada del examen."""
    grading_session, exam = await _graded_exam_or_error(
        session, session_id, exam_id, current_user
    )
    pdf = generate_filled_rubric_pdf(exam.result, grading_session, exam.filename)
    return _pdf_response(pdf, f"rubrica_{Path(exam.filename).stem}.pdf")


@router.get("/{session_id}/exams/{exam_id}/feedback.pdf")
async def download_feedback_pdf(
    session_id: UUID,
    exam_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> Response:
    """Descarga el PDF del informe de feedback del examen."""
    grading_session, exam = await _graded_exam_or_error(
        session, session_id, exam_id, current_user
    )
    pdf = generate_feedback_report_pdf(exam.result, grading_session, exam.filename)
    return _pdf_response(pdf, f"informe_{Path(exam.filename).stem}.pdf")


# ----------------------


async def _graded_exam_or_error(
    session: SessionDep, session_id: UUID, exam_id: UUID, current_user: CurrentUserDep
) -> tuple[GradingSession, Exam]:
    """Carga la sesión y el examen ya corregido, o lanza el error correspondiente."""
    grading_session = owned_or_error(await load_session(session, session_id), current_user)
    exam = next((e for e in grading_session.exams if e.id == exam_id), None)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if exam.status != ExamStatus.COMPLETED or exam.result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El examen aún no está corregido; no hay PDF que descargar.",
        )
    return grading_session, exam


def _pdf_response(content: bytes, download_name: str) -> Response:
    """Respuesta PDF con los headers de descarga."""
    ascii_name = download_name.encode("ascii", "ignore").decode() or "documento.pdf"
    disposition = (
        f"attachment; filename=\"{ascii_name}\"; "
        f"filename*=UTF-8''{quote(download_name)}"
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": disposition},
    )


def _exam_key(user_id: UUID, session_id: UUID, exam_id: UUID, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"{user_id}/{session_id}/exams/{exam_id}{suffix}"


async def _cleanup(storage: FileStorage, keys: list[str]) -> None:
    """Borra los ficheros ya guardados cuando la subida falla."""
    for key in keys:
        try:
            await storage.delete(key)
        except (StorageError, InvalidKey) as exc:
            logger.warning("No se pudo limpiar el fichero huérfano '%s': %s", key, exc)
