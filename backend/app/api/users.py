import logging

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUserDep, SessionDep, StorageDep
from app.core.config import settings
from app.db.models.grading_session import GradingSession
from app.db.models.user import User
from app.schemas.user import AccountDeleteRequest, UserRead, UserUpdate
from app.services.storage.base import StorageError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])

# Palabra que el cliente debe enviar en el cuerpo para confirmar el borrado.
_DELETE_CONFIRMATION = "DELETE"


@router.patch("/me", response_model=UserRead)
async def update_me(
    body: UserUpdate,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> User:
    current_user.name = body.name
    await session.commit()
    await session.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    body: AccountDeleteRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
    storage: StorageDep,
    response: Response,
) -> None:
    if body.confirm != _DELETE_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="confirmation_mismatch",
        )

    # Ficheros a borrar del storage tras eliminar al usuario (la BD cae en cascada).
    result = await session.execute(
        select(GradingSession)
        .options(
            selectinload(GradingSession.documents),
            selectinload(GradingSession.exams),
        )
        .where(GradingSession.user_id == current_user.id)
    )
    keys: list[str] = []
    for grading_session in result.scalars().all():
        keys += [doc.storage_path for doc in grading_session.documents]
        keys += [exam.storage_path for exam in grading_session.exams if exam.storage_path]

    await session.delete(current_user)
    await session.commit()

    # Cierra la sesión: la cuenta ya no existe.
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        samesite="lax",
    )

    for key in keys:
        try:
            await storage.delete(key)
        except StorageError as exc:
            logger.warning(
                "No se pudo borrar el fichero '%s' de la cuenta %s: %s",
                key,
                current_user.id,
                exc,
            )
