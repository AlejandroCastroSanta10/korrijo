from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.magic_link_token import MagicLinkToken


@pytest.mark.asyncio
async def test_request_magic_link_returns_202(client: AsyncClient):
    with patch("app.api.auth._email_service.send_magic_link", new_callable=AsyncMock):
        response = await client.post(
            "/auth/request-magic-link", json={"email": "test@example.com"}
        )
    assert response.status_code == 202


@pytest.mark.asyncio
async def test_request_magic_link_creates_token_in_db(
    client: AsyncClient, session: AsyncSession
):
    with patch("app.api.auth._email_service.send_magic_link", new_callable=AsyncMock):
        await client.post(
            "/auth/request-magic-link", json={"email": "test@example.com"}
        )

    result = await session.execute(
        select(MagicLinkToken).where(MagicLinkToken.email == "test@example.com")
    )
    token = result.scalar_one()

    assert token.email == "test@example.com"
    assert len(token.token) > 0
    assert token.expires_at > datetime.now(UTC)
    assert token.used_at is None


@pytest.mark.asyncio
async def test_request_magic_link_calls_email_service(client: AsyncClient):
    with patch(
        "app.api.auth._email_service.send_magic_link", new_callable=AsyncMock
    ) as mock_send:
        await client.post(
            "/auth/request-magic-link", json={"email": "test@example.com"}
        )

    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert call_args.args[0] == "test@example.com"
    assert "/auth/verify?token=" in call_args.args[1]


@pytest.mark.asyncio
async def test_request_magic_link_rate_limit(client: AsyncClient, session: AsyncSession):
    email = "ratelimit@example.com"

    import secrets

    from app.core.config import settings
    from app.db.models.magic_link_token import MagicLinkToken

    for _ in range(3):
        session.add(
            MagicLinkToken(
                token=secrets.token_urlsafe(32),
                email=email,
                expires_at=datetime.now(UTC) + timedelta(minutes=settings.magic_link_expiration_minutes),
            )
        )
    await session.commit()

    with patch("app.api.auth._email_service.send_magic_link", new_callable=AsyncMock):
        response = await client.post(
            "/auth/request-magic-link", json={"email": email}
        )

    assert response.status_code == 429
