import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUserDep, SessionDep, StorageDep
from app.api.sessions_common import (
    load_session,
    owned_or_error,
    to_session_detail,
    to_session_read,
)
from app.core.config import settings
from app.db.models.exam import Exam
from app.db.models.grading_session import GradingSession, SessionStatus
from app.schemas.session import SessionCreate, SessionDetail, SessionRead
from app.services.storage.base import StorageError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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

    created = await load_session(session, grading_session.id)
    return to_session_detail(created)


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
    return [to_session_read(s) for s in result.scalars().all()]


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
    return to_session_read(grading_session) if grading_session is not None else None


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session_detail(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> SessionDetail:
    grading_session = owned_or_error(await load_session(session, session_id), current_user)
    return to_session_detail(grading_session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    storage: StorageDep,
) -> None:
    grading_session = owned_or_error(await load_session(session, session_id), current_user)

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
