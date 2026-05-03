import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.magic_link_token import MagicLinkToken
from app.db.models.user import User


class TokenInvalid(Exception):
    pass


class TokenExpired(Exception):
    pass


class TokenAlreadyUsed(Exception):
    pass


async def count_recent_tokens(email: str, session: AsyncSession) -> int:
    cutoff = datetime.now(UTC) - timedelta(minutes=settings.magic_link_expiration_minutes)
    result = await session.execute(
        select(func.count()).where(
            MagicLinkToken.email == email,
            MagicLinkToken.created_at >= cutoff,
        )
    )
    return result.scalar_one()


async def create_magic_link_token(email: str, session: AsyncSession) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.magic_link_expiration_minutes)

    session.add(MagicLinkToken(token=token, email=email, expires_at=expires_at))
    await session.commit()

    return f"{settings.app_base_url}/auth/verify?token={token}"


async def verify_magic_link_token(token: str, session: AsyncSession) -> User:
    result = await session.execute(
        select(MagicLinkToken).where(MagicLinkToken.token == token)
    )
    ml_token = result.scalar_one_or_none()

    if ml_token is None:
        raise TokenInvalid()
    if ml_token.used_at is not None:
        raise TokenAlreadyUsed()
    if ml_token.expires_at < datetime.now(UTC):
        raise TokenExpired()

    user_result = await session.execute(
        select(User).where(User.email == ml_token.email)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        user = User(email=ml_token.email)
        session.add(user)

    ml_token.used_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(user)

    return user
