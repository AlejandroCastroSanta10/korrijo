from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models.user import User
from app.db.session import get_session
from app.services.auth import (
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    count_recent_tokens,
    create_magic_link_token,
    verify_magic_link_token,
)
from app.services.email import SmtpEmailService
from app.services.session import sign_session

router = APIRouter()

_email_service = SmtpEmailService()

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


class RequestMagicLinkBody(BaseModel):
    email: EmailStr


class VerifyMagicLinkBody(BaseModel):
    token: str


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


@router.post("/verify")
async def verify_magic_link(
    body: VerifyMagicLinkBody,
    response: Response,
    session: SessionDep,
) -> dict:
    try:
        user = await verify_magic_link_token(body.token, session)
    except TokenInvalid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid") from None
    except TokenExpired:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expired") from None
    except TokenAlreadyUsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="already_used"
        ) from None

    secure = settings.app_base_url.startswith("https")
    response.set_cookie(
        key=settings.session_cookie_name,
        value=sign_session(str(user.id)),
        max_age=settings.session_max_age_days * 86400,
        httponly=True,
        samesite="lax",
        secure=secure,  # Solo en producción sería segura
    )

    return {"id": str(user.id), "email": user.email, "name": user.name}


@router.get("/me")
async def get_me(current_user: CurrentUserDep) -> dict:
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        samesite="lax",
    )
