"""Helpers compartidos por los routers de sesiones y de documentos."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.exam import Exam, ExamStatus
from app.db.models.grading_session import GradingSession
from app.db.models.user import User
from app.schemas.session import (
    ExamRead,
    SessionDetail,
    SessionDocumentRead,
    SessionRead,
)


async def load_session(session: AsyncSession, session_id: UUID) -> GradingSession | None:
    """Carga una sesión con sus documentos y exámenes (+resultado) eager."""
    result = await session.execute(
        select(GradingSession)
        .options(
            selectinload(GradingSession.documents),
            selectinload(GradingSession.exams).selectinload(Exam.result),
        )
        .where(GradingSession.id == session_id)
    )
    return result.scalar_one_or_none()


def owned_or_error(grading_session: GradingSession | None, user: User) -> GradingSession:
    """Devuelve la sesión si pertenece al usuario; si no, 404 (no existe) o 403."""
    if grading_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if grading_session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return grading_session


def _counters(grading_session: GradingSession) -> dict:
    """Contadores derivados a partir de los exámenes corregidos de la sesión."""
    scores = [
        exam.result.total_score
        for exam in grading_session.exams
        if exam.status == ExamStatus.COMPLETED and exam.result is not None
    ]
    passed = sum(1 for s in scores if s >= grading_session.max_score / 2)
    return {
        "graded_count": len(scores),
        "passed_count": passed,
        "failed_count": len(scores) - passed,
        "average_score": sum(scores) / len(scores) if scores else None,
    }


def to_session_read(grading_session: GradingSession) -> SessionRead:
    return SessionRead(
        id=grading_session.id,
        name=grading_session.name,
        max_score=grading_session.max_score,
        status=grading_session.status,
        context_instructions=grading_session.context_instructions,
        model_exam_instructions=grading_session.model_exam_instructions,
        created_at=grading_session.created_at,
        updated_at=grading_session.updated_at,
        **_counters(grading_session),
    )


def to_session_detail(grading_session: GradingSession) -> SessionDetail:
    base = to_session_read(grading_session)
    return SessionDetail(
        **base.model_dump(),
        documents=[SessionDocumentRead.model_validate(d) for d in grading_session.documents],
        exams=[
            ExamRead(
                id=exam.id,
                filename=exam.filename,
                status=exam.status,
                total_score=exam.result.total_score if exam.result is not None else None,
                error_message=exam.error_message,
                created_at=exam.created_at,
            )
            for exam in grading_session.exams
        ],
    )
