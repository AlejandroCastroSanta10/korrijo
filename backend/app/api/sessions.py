import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_file_storage
from app.core.config import settings
from app.db.models.exam import Exam, ExamStatus
from app.db.models.grading_session import GradingSession, SessionStatus
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.session import (
    ExamRead,
    SessionCreate,
    SessionDetail,
    SessionDocumentRead,
    SessionRead,
)
from app.services.storage.base import FileStorage, StorageError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
StorageDep = Annotated[FileStorage, Depends(get_file_storage)]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

async def _load_session(session: AsyncSession, session_id: UUID) -> GradingSession | None:
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


def _owned_or_error(grading_session: GradingSession | None, user: User) -> GradingSession:
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


def _to_session_read(grading_session: GradingSession) -> SessionRead:
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


def _to_session_detail(grading_session: GradingSession) -> SessionDetail:
    base = _to_session_read(grading_session)
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


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.post("", status_code=status.HTTP_201_CREATED, response_model=SessionDetail)
async def create_session(
    body: SessionCreate,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> SessionDetail:
    active = (
        await session.execute(
            select(func.count())
            .select_from(GradingSession)
            .where(
                GradingSession.user_id == current_user.id,
                GradingSession.status != SessionStatus.ARCHIVED,
            )
        )
    ).scalar_one()
    if active >= settings.max_active_sessions_per_user:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Has alcanzado el máximo de {settings.max_active_sessions_per_user} "
                "sesiones activas. Elimina alguna para crear una nueva."
            ),
        )

    grading_session = GradingSession(
        user_id=current_user.id,
        name=body.name,
        max_score=body.max_score,
        context_instructions=body.context_instructions,
        model_exam_instructions=body.model_exam_instructions,
    )
    session.add(grading_session)
    await session.commit()

    created = await _load_session(session, grading_session.id)
    return _to_session_detail(created)


@router.get("", response_model=list[SessionRead])
async def list_sessions(
    current_user: CurrentUserDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SessionRead]:
    result = await session.execute(
        select(GradingSession)
        .options(selectinload(GradingSession.exams).selectinload(Exam.result))
        .where(GradingSession.user_id == current_user.id)
        .order_by(GradingSession.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_to_session_read(s) for s in result.scalars().all()]


@router.get("/recent", response_model=SessionRead | None)
async def recent_session(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> SessionRead | None:
    result = await session.execute(
        select(GradingSession)
        .options(selectinload(GradingSession.exams).selectinload(Exam.result))
        .where(GradingSession.user_id == current_user.id)
        .order_by(GradingSession.updated_at.desc())
        .limit(1)
    )
    grading_session = result.scalar_one_or_none()
    return _to_session_read(grading_session) if grading_session is not None else None


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session_detail(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> SessionDetail:
    grading_session = _owned_or_error(await _load_session(session, session_id), current_user)
    return _to_session_detail(grading_session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    storage: StorageDep,
) -> None:
    grading_session = _owned_or_error(await _load_session(session, session_id), current_user)

    # Ficheros a borrar del storage tras eliminar la fila en BD
    keys = [doc.storage_path for doc in grading_session.documents]
    keys += [exam.storage_path for exam in grading_session.exams]

    await session.delete(grading_session)
    await session.commit()

    for key in keys:
        try:
            await storage.delete(key)
        except StorageError as exc:
            logger.warning(
                "No se pudo borrar el fichero '%s' de la sesión %s: %s",
                key,
                session_id,
                exc,
            )
