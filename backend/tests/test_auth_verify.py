import secrets
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.magic_link_token import MagicLinkToken
from app.db.models.user import User
from app.services.session import sign_session


async def _insert_token(
    session: AsyncSession,
    email: str,
    *,
    expired: bool = False,
    used: bool = False,
) -> str:
    token_str = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(UTC) - timedelta(minutes=1)
        if expired
        else datetime.now(UTC) + timedelta(minutes=settings.magic_link_expiration_minutes)
    )
    used_at = datetime.now(UTC) - timedelta(minutes=1) if used else None
    session.add(
        MagicLinkToken(token=token_str, email=email, expires_at=expires_at, used_at=used_at)
    )
    await session.commit()
    return token_str


@pytest.mark.asyncio
async def test_verify_valid_token_returns_200_with_cookie_and_marks_used_at(
    client: AsyncClient, session: AsyncSession
):
    token_str = await _insert_token(session, "user@example.com")

    response = await client.post("/auth/verify", json={"token": token_str})

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert settings.session_cookie_name in response.cookies

    result = await session.execute(
        select(MagicLinkToken).where(MagicLinkToken.token == token_str)
    )
    ml_token = result.scalar_one()
    assert ml_token.used_at is not None


@pytest.mark.asyncio
async def test_verify_valid_token_creates_user_if_not_exists(
    client: AsyncClient, session: AsyncSession
):
    token_str = await _insert_token(session, "new@example.com")

    await client.post("/auth/verify", json={"token": token_str})

    result = await session.execute(select(User).where(User.email == "new@example.com"))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_verify_expired_token_returns_400(client: AsyncClient, session: AsyncSession):
    token_str = await _insert_token(session, "user@example.com", expired=True)

    response = await client.post("/auth/verify", json={"token": token_str})

    assert response.status_code == 400
    assert response.json()["detail"] == "expired"


@pytest.mark.asyncio
async def test_verify_used_token_returns_400(client: AsyncClient, session: AsyncSession):
    token_str = await _insert_token(session, "user@example.com", used=True)

    response = await client.post("/auth/verify", json={"token": token_str})

    assert response.status_code == 400
    assert response.json()["detail"] == "already_used"


@pytest.mark.asyncio
async def test_verify_invalid_token_returns_400(client: AsyncClient):
    response = await client.post("/auth/verify", json={"token": "token-que-no-existe"})

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid"


@pytest.mark.asyncio
async def test_get_me_with_valid_cookie_returns_user(
    client: AsyncClient, session: AsyncSession
):
    user = User(email="me@example.com")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    cookie_value = sign_session(str(user.id))
    client.cookies.set(settings.session_cookie_name, cookie_value)

    response = await client.get("/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["id"] == str(user.id)


@pytest.mark.asyncio
async def test_get_me_without_cookie_returns_401(client: AsyncClient):
    response = await client.get("/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_returns_204_and_deletes_cookie(
    client: AsyncClient, session: AsyncSession
):
    user = User(email="logout@example.com")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    cookie_value = sign_session(str(user.id))
    client.cookies.set(settings.session_cookie_name, cookie_value)

    response = await client.post("/auth/logout")

    assert response.status_code == 204
    set_cookie = response.headers.get("set-cookie", "")
    assert settings.session_cookie_name in set_cookie
    assert "max-age=0" in set_cookie.lower()
