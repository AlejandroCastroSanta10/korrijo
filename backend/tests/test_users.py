import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_file_storage
from app.core.config import settings
from app.db.models.exam import Exam
from app.db.models.grading_session import GradingSession
from app.db.models.session_document import DocumentKind, SessionDocument
from app.db.models.user import User
from app.main import app
from app.services.session import sign_session
from app.services.storage import FileStorage, LocalFileStorage


async def _make_user(session: AsyncSession, email: str, name: str | None = None) -> User:
    user = User(email=email, name=name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def _login(client: AsyncClient, user: User) -> None:
    client.cookies.set(settings.session_cookie_name, sign_session(str(user.id)))


@pytest.fixture
def storage(tmp_path):
    instance = LocalFileStorage(tmp_path / "storage")
    app.dependency_overrides[get_file_storage] = lambda: instance
    yield instance
    app.dependency_overrides.pop(get_file_storage, None)


# --------------------------------------------------------------------------- #
# PATCH /api/users/me
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_update_me_changes_name(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com", name="Antiguo")
    _login(client, user)

    resp = await client.patch("/api/users/me", json={"name": "Nuevo Nombre"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Nuevo Nombre"
    assert data["email"] == "prof@example.com"

    await session.refresh(user)
    assert user.name == "Nuevo Nombre"


@pytest.mark.asyncio
async def test_update_me_trims_whitespace(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    _login(client, user)

    resp = await client.patch("/api/users/me", json={"name": "  Juan Gil  "})

    assert resp.status_code == 200
    assert resp.json()["name"] == "Juan Gil"


@pytest.mark.asyncio
async def test_update_me_rejects_empty_name(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    _login(client, user)

    resp = await client.patch("/api/users/me", json={"name": "   "})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_me_requires_auth(client: AsyncClient):
    resp = await client.patch("/api/users/me", json={"name": "X"})
    assert resp.status_code == 401


# --------------------------------------------------------------------------- #
# DELETE /api/users/me
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_delete_me_requires_auth(client: AsyncClient):
    resp = await client.request("DELETE", "/api/users/me", json={"confirm": "DELETE"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_me_requires_confirmation(
    client: AsyncClient, session: AsyncSession, storage: LocalFileStorage
):
    user = await _make_user(session, "prof@example.com")
    _login(client, user)

    resp = await client.request("DELETE", "/api/users/me", json={"confirm": "nope"})

    assert resp.status_code == 422
    # La cuenta sigue existiendo.
    remaining = (
        await session.execute(select(func.count()).select_from(User).where(User.id == user.id))
    ).scalar_one()
    assert remaining == 1


@pytest.mark.asyncio
async def test_delete_me_removes_account_and_data(
    client: AsyncClient, session: AsyncSession, storage: LocalFileStorage
):
    user = await _make_user(session, "prof@example.com")
    grading_session = GradingSession(user_id=user.id, name="S1")
    session.add(grading_session)
    await session.commit()
    await session.refresh(grading_session)

    doc_key = FileStorage.key_for(user.id, grading_session.id, "rubrica.pdf")
    exam_key = FileStorage.key_for(user.id, grading_session.id, "alumno.pdf")
    await storage.save(b"rubrica", doc_key)
    await storage.save(b"examen", exam_key)
    session.add(
        SessionDocument(
            session_id=grading_session.id,
            kind=DocumentKind.RUBRIC,
            filename="rubrica.pdf",
            storage_path=doc_key,
            size_bytes=7,
            mime_type="application/pdf",
        )
    )
    session.add(
        Exam(session_id=grading_session.id, filename="alumno.pdf", storage_path=exam_key)
    )
    await session.commit()
    _login(client, user)

    resp = await client.request("DELETE", "/api/users/me", json={"confirm": "DELETE"})

    assert resp.status_code == 204
    # La cookie de sesión se borra.
    assert settings.session_cookie_name in resp.headers.get("set-cookie", "")

    # Usuario y sus sesiones eliminados (cascada).
    users_left = (
        await session.execute(select(func.count()).select_from(User).where(User.id == user.id))
    ).scalar_one()
    assert users_left == 0
    sessions_left = (
        await session.execute(
            select(func.count())
            .select_from(GradingSession)
            .where(GradingSession.user_id == user.id)
        )
    ).scalar_one()
    assert sessions_left == 0

    # Ficheros borrados del storage.
    assert not await storage.exists(doc_key)
    assert not await storage.exists(exam_key)
