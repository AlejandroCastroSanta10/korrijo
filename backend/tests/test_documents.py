import json
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_file_storage, get_llm_provider
from app.core.config import settings
from app.db.models.grading_session import GradingSession, SessionStatus
from app.db.models.session_document import DocumentKind, SessionDocument
from app.db.models.user import User
from app.main import app
from app.services.session import sign_session
from app.services.storage import FileStorage, LocalFileStorage

FIXTURES = Path(__file__).parent / "pipeline" / "fixtures"


# --------------------------------------------------------------------------- #
# Utilidades y fixtures
# --------------------------------------------------------------------------- #

class FakeLLM:
    """LLMProvider falso: devuelve siempre la misma respuesta (configurable)."""

    def __init__(self, response: str = "") -> None:
        self.response = response

    async def generate(self, prompt: str, schema: dict | None = None) -> str:
        return self.response


def _rubric_json(*items: tuple[str, float, str]) -> str:
    """Serializa una rúbrica estructurada como la devolvería el LLM."""
    return json.dumps(
        {"items": [{"name": n, "max_score": s, "description": d} for n, s, d in items]}
    )


async def _make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _make_session(session: AsyncSession, user: User, **overrides) -> GradingSession:
    grading_session = GradingSession(user_id=user.id, name="S1", **overrides)
    session.add(grading_session)
    await session.commit()
    await session.refresh(grading_session)
    return grading_session


async def _add_document(
    session: AsyncSession, grading_session: GradingSession, kind: DocumentKind, **overrides
) -> SessionDocument:
    doc = SessionDocument(
        session_id=grading_session.id,
        kind=kind,
        filename=overrides.pop("filename", f"{kind.value}.txt"),
        storage_path=overrides.pop("storage_path", f"{grading_session.id}/{kind.value}.txt"),
        size_bytes=overrides.pop("size_bytes", 10),
        mime_type=overrides.pop("mime_type", "text/plain"),
        **overrides,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


def _login(client: AsyncClient, user: User) -> None:
    client.cookies.set(settings.session_cookie_name, sign_session(str(user.id)))


@pytest.fixture(autouse=True)
def storage(tmp_path):
    """Storage local aislado en tmp_path para todos los tests del módulo."""
    instance = LocalFileStorage(tmp_path / "storage")
    app.dependency_overrides[get_file_storage] = lambda: instance
    yield instance
    app.dependency_overrides.pop(get_file_storage, None)


@pytest.fixture(autouse=True)
def llm():
    """LLM falso instalado por defecto (los tests fijan `.response` si lo usan)."""
    fake = FakeLLM(_rubric_json(("Ítem 1", 10.0, "Todo")))
    app.dependency_overrides[get_llm_provider] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_llm_provider, None)


def _upload(client: AsyncClient, session_id, kind: str, filename: str, content: bytes, mime="text/plain"):
    return client.post(
        f"/api/sessions/{session_id}/documents",
        data={"kind": kind},
        files={"file": (filename, content, mime)},
    )


# --------------------------------------------------------------------------- #
# POST /documents
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_upload_context_returns_201_with_extracted_text(
    client: AsyncClient, session: AsyncSession
):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    _login(client, user)

    resp = await _upload(client, grading_session.id, "context", "apuntes.txt", b"Apuntes de clase")

    assert resp.status_code == 201
    data = resp.json()
    assert data["kind"] == "context"
    assert data["extracted_text"] == "Apuntes de clase"
    assert data["rubric"] is None


@pytest.mark.asyncio
async def test_upload_rubric_returns_structure_without_warning_when_sum_matches(
    client: AsyncClient, session: AsyncSession, llm: FakeLLM
):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user, max_score=10.0)
    llm.response = _rubric_json(("Definición", 6.0, "Concepto"), ("Ejemplo", 4.0, "Caso"))
    _login(client, user)

    resp = await _upload(client, grading_session.id, "rubric", "rubrica.txt", b"Criterios...")

    assert resp.status_code == 201
    rubric = resp.json()["rubric"]
    assert len(rubric["items"]) == 2
    assert rubric["total_max_score"] == 10.0
    assert rubric["warning"] is None


@pytest.mark.asyncio
async def test_upload_rubric_warns_when_items_do_not_sum_max_score(
    client: AsyncClient, session: AsyncSession, llm: FakeLLM
):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user, max_score=10.0)
    llm.response = _rubric_json(("Definición", 6.0, ""), ("Ejemplo", 2.0, ""))  # suma 8
    _login(client, user)

    resp = await _upload(client, grading_session.id, "rubric", "rubrica.txt", b"Criterios...")

    assert resp.status_code == 201
    assert resp.json()["rubric"]["warning"] is not None


@pytest.mark.asyncio
async def test_upload_rubric_pdf_extracts_and_structures(
    client: AsyncClient, session: AsyncSession, llm: FakeLLM
):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user, max_score=10.0)
    llm.response = _rubric_json(("Ítem", 10.0, ""))
    _login(client, user)

    content = (FIXTURES / "rubrica.pdf").read_bytes()
    resp = await _upload(
        client, grading_session.id, "rubric", "rubrica.pdf", content, mime="application/pdf"
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["extracted_text"]
    assert data["rubric"]["items"]


@pytest.mark.asyncio
async def test_upload_graceful_when_rubric_cannot_be_structured(
    client: AsyncClient, session: AsyncSession, llm: FakeLLM
):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    llm.response = "esto no es JSON"
    _login(client, user)

    resp = await _upload(client, grading_session.id, "rubric", "rubrica.txt", b"Criterios...")

    assert resp.status_code == 201
    rubric = resp.json()["rubric"]
    assert rubric["items"] == []
    assert rubric["warning"] is not None


@pytest.mark.asyncio
async def test_upload_rejects_invalid_extension(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    _login(client, user)

    resp = await _upload(client, grading_session.id, "context", "malware.exe", b"x", mime="application/octet-stream")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejects_file_over_size_limit(
    client: AsyncClient, session: AsyncSession, monkeypatch
):
    monkeypatch.setattr(settings, "max_document_upload_bytes", 10)
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    _login(client, user)

    resp = await _upload(client, grading_session.id, "model_exam", "modelo.txt", b"x" * 20)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_scanned_pdf_returns_422(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    _login(client, user)

    content = (FIXTURES / "escaneado.pdf").read_bytes()
    resp = await _upload(
        client, grading_session.id, "model_exam", "escaneado.pdf", content, mime="application/pdf"
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)

    resp = await _upload(client, grading_session.id, "context", "apuntes.txt", b"x")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_session_not_found(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    _login(client, user)

    resp = await _upload(client, uuid.uuid4(), "context", "apuntes.txt", b"x")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_other_user_forbidden(client: AsyncClient, session: AsyncSession):
    owner = await _make_user(session, "owner@example.com")
    other = await _make_user(session, "other@example.com")
    grading_session = await _make_session(session, owner)
    _login(client, other)

    resp = await _upload(client, grading_session.id, "context", "apuntes.txt", b"x")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_rubric_replaces_previous(
    client: AsyncClient, session: AsyncSession, storage: LocalFileStorage
):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    _login(client, user)

    await _upload(client, grading_session.id, "rubric", "primera.txt", b"vieja")
    await _upload(client, grading_session.id, "rubric", "segunda.txt", b"nueva")

    rubrics = (
        await session.execute(
            select(func.count())
            .select_from(SessionDocument)
            .where(
                SessionDocument.session_id == grading_session.id,
                SessionDocument.kind == DocumentKind.RUBRIC,
            )
        )
    ).scalar_one()
    assert rubrics == 1

    old_key = FileStorage.key_for(user.id, grading_session.id, "primera.txt")
    new_key = FileStorage.key_for(user.id, grading_session.id, "segunda.txt")
    assert not await storage.exists(old_key)
    assert await storage.exists(new_key)


# --------------------------------------------------------------------------- #
# GET /documents/{id} y /raw
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_get_document_detail_returns_extracted_text(
    client: AsyncClient, session: AsyncSession
):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    _login(client, user)
    created = (await _upload(client, grading_session.id, "context", "apuntes.txt", b"Hola")).json()

    resp = await client.get(f"/api/sessions/{grading_session.id}/documents/{created['id']}")

    assert resp.status_code == 200
    assert resp.json()["extracted_text"] == "Hola"


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    _login(client, user)

    resp = await client.get(f"/api/sessions/{grading_session.id}/documents/{uuid.uuid4()}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_raw_returns_bytes_and_headers(
    client: AsyncClient, session: AsyncSession
):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    _login(client, user)
    created = (await _upload(client, grading_session.id, "context", "apuntes.txt", b"contenido")).json()

    resp = await client.get(
        f"/api/sessions/{grading_session.id}/documents/{created['id']}/raw"
    )

    assert resp.status_code == 200
    assert resp.content == b"contenido"
    assert "apuntes.txt" in resp.headers["content-disposition"]


# --------------------------------------------------------------------------- #
# DELETE /documents/{id}
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_delete_document_removes_db_and_file(
    client: AsyncClient, session: AsyncSession, storage: LocalFileStorage
):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    _login(client, user)
    created = (await _upload(client, grading_session.id, "context", "apuntes.txt", b"x")).json()
    key = FileStorage.key_for(user.id, grading_session.id, "apuntes.txt")
    assert await storage.exists(key)

    resp = await client.delete(
        f"/api/sessions/{grading_session.id}/documents/{created['id']}"
    )

    assert resp.status_code == 204
    remaining = (
        await session.execute(
            select(func.count())
            .select_from(SessionDocument)
            .where(SessionDocument.id == uuid.UUID(created["id"]))
        )
    ).scalar_one()
    assert remaining == 0
    assert not await storage.exists(key)


# --------------------------------------------------------------------------- #
# POST /rubric/validate
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_validate_requires_model_exam(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    await _add_document(session, grading_session, DocumentKind.RUBRIC)
    _login(client, user)

    resp = await client.post(
        f"/api/sessions/{grading_session.id}/rubric/validate",
        json={"items": [{"name": "P1", "max_score": 10, "description": ""}]},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_validate_requires_rubric_document(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    await _add_document(session, grading_session, DocumentKind.MODEL_EXAM)
    _login(client, user)

    resp = await client.post(
        f"/api/sessions/{grading_session.id}/rubric/validate",
        json={"items": [{"name": "P1", "max_score": 10, "description": ""}]},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_validate_sets_session_ready_and_persists_rubric(
    client: AsyncClient, session: AsyncSession
):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    await _add_document(session, grading_session, DocumentKind.RUBRIC)
    await _add_document(session, grading_session, DocumentKind.MODEL_EXAM)
    _login(client, user)

    items = [{"name": "P1", "max_score": 6.0, "description": "a"},
             {"name": "P2", "max_score": 4.0, "description": "b"}]
    resp = await client.post(
        f"/api/sessions/{grading_session.id}/rubric/validate", json={"items": items}
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
    await session.refresh(grading_session)
    assert grading_session.status == SessionStatus.READY
    assert grading_session.rubric_structured == items


@pytest.mark.asyncio
async def test_validate_rejects_empty_items(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    grading_session = await _make_session(session, user)
    _login(client, user)

    resp = await client.post(
        f"/api/sessions/{grading_session.id}/rubric/validate", json={"items": []}
    )

    assert resp.status_code == 422
