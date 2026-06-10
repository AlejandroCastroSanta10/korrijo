# Dependencias compartidas (reutilizables) entre varios routers.

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.user import User
from app.db.session import get_session
from app.services.session import verify_session
from app.services.storage import FileStorage, LocalFileStorage

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@lru_cache
def get_file_storage() -> FileStorage:
    return LocalFileStorage(settings.storage_root)


async def get_current_user(request: Request, session: SessionDep) -> User:
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        user_id = verify_session(cookie)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from None

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user
