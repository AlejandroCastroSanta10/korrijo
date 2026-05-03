from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.services.auth import count_recent_tokens, create_magic_link_token
from app.services.email import SmtpEmailService

router = APIRouter()

_email_service = SmtpEmailService()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class RequestMagicLinkBody(BaseModel):
    email: EmailStr


@router.post("/request-magic-link", status_code=status.HTTP_202_ACCEPTED)
async def request_magic_link(
    body: RequestMagicLinkBody,
    session: SessionDep,
) -> dict:
    recent = await count_recent_tokens(body.email, session)
    if recent >= 3:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)

    link = await create_magic_link_token(body.email, session)
    await _email_service.send_magic_link(body.email, link, settings.magic_link_expiration_minutes)

    return {"message": "Comprueba tu email, recibirás un enlace de acceso en breve."}
