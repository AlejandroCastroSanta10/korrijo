import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.magic_link_token import MagicLinkToken


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
