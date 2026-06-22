import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_file_storage
from app.core.config import settings
from app.db.models.exam import Exam
from app.db.models.grading_session import GradingSession, SessionStatus
from app.db.models.session_document import DocumentKind, SessionDocument
from app.db.models.user import User
from app.main import app
from app.services.session import sign_session
from app.services.storage import FileStorage, LocalFileStorage


async def _make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def _login(client: AsyncClient, user: User) -> None:
    client.cookies.set(settings.session_cookie_name, sign_session(str(user.id)))


def _payload(**overrides) -> dict:
    return {"name": "Examen Historia T1", "max_score": 10, **overrides}


@pytest.fixture
def storage(tmp_path):
    """Sobrescribe get_file_storage por un storage local en tmp_path."""
    instance = LocalFileStorage(tmp_path / "storage")
    app.dependency_overrides[get_file_storage] = lambda: instance
    yield instance
    app.dependency_overrides.pop(get_file_storage, None)


# --------------------------------------------------------------------------- #
# POST /api/sessions
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_create_returns_201_with_draft_detail(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    _login(client, user)

    resp = await client.post("/api/sessions", json=_payload(name="Mi sesión"))

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Mi sesión"
    assert data["status"] == "draft"
    assert data["documents"] == []
    assert data["exams"] == []
    assert data["graded_count"] == 0
    assert data["average_score"] is None


@pytest.mark.asyncio
async def test_create_requires_auth(client: AsyncClient):
    resp = await client.post("/api/sessions", json=_payload())
    assert resp.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [{"name": ""}, {"max_score": 0}, {"max_score": -3}])
async def test_create_validation_error(client: AsyncClient, session: AsyncSession, bad: dict):
    user = await _make_user(session, "prof@example.com")
    _login(client, user)

    resp = await client.post("/api/sessions", json=_payload(**bad))

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_beyond_limit_returns_422(
    client: AsyncClient, session: AsyncSession, monkeypatch
):
    monkeypatch.setattr(settings, "max_active_sessions_per_user", 2)
    user = await _make_user(session, "prof@example.com")
    session.add_all(
        [
            GradingSession(user_id=user.id, name="S1", status=SessionStatus.READY),
            GradingSession(user_id=user.id, name="S2", status=SessionStatus.READY),
        ]
    )
    await session.commit()
    _login(client, user)

    resp = await client.post("/api/sessions", json=_payload(name="S3"))

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_archived_sessions_do_not_count_toward_limit(
    client: AsyncClient, session: AsyncSession, monkeypatch
):
    monkeypatch.setattr(settings, "max_active_sessions_per_user", 2)
    user = await _make_user(session, "prof@example.com")
    session.add_all(
        [
            GradingSession(user_id=user.id, name="Activa", status=SessionStatus.READY),
            GradingSession(user_id=user.id, name="Archivada", status=SessionStatus.ARCHIVED),
        ]
    )
    await session.commit()
    _login(client, user)

    # 1 activa + 1 archivada; con límite 2, la archivada no cuenta -> se permite.
    resp = await client.post("/api/sessions", json=_payload(name="Nueva"))

    assert resp.status_code == 201


# --------------------------------------------------------------------------- #
# GET /api/sessions
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_list_returns_only_current_user_ordered_desc(
    client: AsyncClient, session: AsyncSession
):
    user_a = await _make_user(session, "a@example.com")
    user_b = await _make_user(session, "b@example.com")
    now = datetime.now(UTC)
    session.add_all(
        [
            GradingSession(
                user_id=user_a.id, name="A1", status=SessionStatus.READY,
                created_at=now - timedelta(hours=2),
            ),
            GradingSession(
                user_id=user_a.id, name="A2", status=SessionStatus.READY, created_at=now
            ),
            GradingSession(
                user_id=user_b.id, name="B1", status=SessionStatus.READY, created_at=now
            ),
        ]
    )
    await session.commit()
    _login(client, user_a)

    resp = await client.get("/api/sessions")

    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert names == ["A2", "A1"]  # solo las de A, más reciente primero


# --------------------------------------------------------------------------- #
# GET /api/sessions/recent
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_recent_returns_null_when_no_sessions(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "a@example.com")
    _login(client, user)

    resp = await client.get("/api/sessions/recent")

    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_recent_returns_latest_modified(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "a@example.com")
    now = datetime.now(UTC)
    session.add_all(
        [
            GradingSession(
                user_id=user.id, name="Antigua", status=SessionStatus.READY,
                updated_at=now - timedelta(hours=1),
            ),
            GradingSession(
                user_id=user.id, name="Reciente", status=SessionStatus.READY, updated_at=now
            ),
        ]
    )
    await session.commit()
    _login(client, user)

    resp = await client.get("/api/sessions/recent")

    assert resp.json()["name"] == "Reciente"


# --------------------------------------------------------------------------- #
# Drafts abandonados (sesiones a medias, sin rúbrica confirmada)
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_list_excludes_drafts(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "a@example.com")
    session.add_all(
        [
            GradingSession(user_id=user.id, name="Lista", status=SessionStatus.READY),
            GradingSession(user_id=user.id, name="Borrador", status=SessionStatus.DRAFT),
        ]
    )
    await session.commit()
    _login(client, user)

    resp = await client.get("/api/sessions")

    assert resp.status_code == 200
    assert [s["name"] for s in resp.json()] == ["Lista"]


@pytest.mark.asyncio
async def test_recent_ignores_drafts(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "a@example.com")
    now = datetime.now(UTC)
    session.add_all(
        [
            GradingSession(
                user_id=user.id, name="Lista", status=SessionStatus.READY,
                updated_at=now - timedelta(hours=1),
            ),
            # Draft más reciente: no debe ser la "sesión reciente".
            GradingSession(
                user_id=user.id, name="Borrador", status=SessionStatus.DRAFT, updated_at=now
            ),
        ]
    )
    await session.commit()
    _login(client, user)

    resp = await client.get("/api/sessions/recent")

    assert resp.json()["name"] == "Lista"


@pytest.mark.asyncio
async def test_drafts_do_not_count_toward_limit(
    client: AsyncClient, session: AsyncSession, storage: LocalFileStorage, monkeypatch
):
    monkeypatch.setattr(settings, "max_active_sessions_per_user", 1)
    user = await _make_user(session, "a@example.com")
    # Un único draft abandonado: no cuenta para el límite (antes sí lo hacía).
    session.add(GradingSession(user_id=user.id, name="Borrador", status=SessionStatus.DRAFT))
    await session.commit()
    _login(client, user)

    resp = await client.post("/api/sessions", json=_payload(name="Nueva"))

    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_deletes_abandoned_drafts(
    client: AsyncClient, session: AsyncSession, storage: LocalFileStorage
):
    user = await _make_user(session, "a@example.com")
    draft = GradingSession(user_id=user.id, name="Borrador", status=SessionStatus.DRAFT)
    session.add(draft)
    await session.commit()
    await session.refresh(draft)

    doc_key = FileStorage.key_for(user.id, draft.id, "rubrica.pdf")
    await storage.save(b"rubrica", doc_key)
    session.add(
        SessionDocument(
            session_id=draft.id,
            kind=DocumentKind.RUBRIC,
            filename="rubrica.pdf",
            storage_path=doc_key,
            size_bytes=7,
            mime_type="application/pdf",
        )
    )
    await session.commit()
    _login(client, user)

    resp = await client.post("/api/sessions", json=_payload(name="Nueva"))

    assert resp.status_code == 201
    # El draft anterior (y su fichero) ya no existen.
    remaining = (
        await session.execute(
            select(func.count())
            .select_from(GradingSession)
            .where(GradingSession.id == draft.id)
        )
    ).scalar_one()
    assert remaining == 0
    assert not await storage.exists(doc_key)


# --------------------------------------------------------------------------- #
# GET /api/sessions/{id}
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_get_detail_owner(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "a@example.com")
    grading_session = GradingSession(user_id=user.id, name="S1")
    session.add(grading_session)
    await session.commit()
    await session.refresh(grading_session)
    _login(client, user)

    resp = await client.get(f"/api/sessions/{grading_session.id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(grading_session.id)


@pytest.mark.asyncio
async def test_get_detail_not_found(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "a@example.com")
    _login(client, user)

    resp = await client.get(f"/api/sessions/{uuid.uuid4()}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_detail_other_user_forbidden(client: AsyncClient, session: AsyncSession):
    owner = await _make_user(session, "owner@example.com")
    other = await _make_user(session, "other@example.com")
    grading_session = GradingSession(user_id=owner.id, name="S1")
    session.add(grading_session)
    await session.commit()
    await session.refresh(grading_session)
    _login(client, other)

    resp = await client.get(f"/api/sessions/{grading_session.id}")

    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# DELETE /api/sessions/{id}
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_delete_removes_session_and_files(
    client: AsyncClient, session: AsyncSession, storage: LocalFileStorage
):
    user = await _make_user(session, "a@example.com")
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

    resp = await client.delete(f"/api/sessions/{grading_session.id}")

    assert resp.status_code == 204
    remaining = (
        await session.execute(
            select(func.count())
            .select_from(GradingSession)
            .where(GradingSession.id == grading_session.id)
        )
    ).scalar_one()
    assert remaining == 0
    assert not await storage.exists(doc_key)
    assert not await storage.exists(exam_key)


@pytest.mark.asyncio
async def test_delete_other_user_forbidden(
    client: AsyncClient, session: AsyncSession, storage: LocalFileStorage
):
    owner = await _make_user(session, "owner@example.com")
    other = await _make_user(session, "other@example.com")
    grading_session = GradingSession(user_id=owner.id, name="S1")
    session.add(grading_session)
    await session.commit()
    await session.refresh(grading_session)
    _login(client, other)

    resp = await client.delete(f"/api/sessions/{grading_session.id}")

    assert resp.status_code == 403
