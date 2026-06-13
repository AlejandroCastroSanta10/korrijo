import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_exam_runner, get_file_storage
from app.core.config import settings
from app.db.models.exam import Exam, ExamStatus
from app.db.models.grading_result import GradingResult
from app.db.models.grading_session import GradingSession, SessionStatus
from app.db.models.session_document import DocumentKind, SessionDocument
from app.db.models.user import User
from app.main import app
from app.pipeline.errors import ProviderError
from app.services.exams import process_exam
from app.services.session import sign_session
from app.services.storage import LocalFileStorage

# Salidas válidas que los proveedores falsos devuelven al pipeline.
_TRANSCRIPTION_JSON = json.dumps(
    {
        "metadata": {"nombre": "Ana", "apellidos": "García"},
        "answers": [{"question_number": 1, "answer_text": "La prehistoria es..."}],
    }
)
_GRADING_JSON = json.dumps(
    {
        "total_score": 7.0,
        "rubric_filled": [
            {"item_name": "Definición", "assigned_score": 7.0, "max_score": 10.0, "comment": "Bien"}
        ],
        "feedback_report": "Buen trabajo, mejora los ejemplos.",
    }
)


# --------------------------------------------------------------------------- #
# Dobles de proveedores
# --------------------------------------------------------------------------- #

class FakeVLM:
    """VLMProvider falso: devuelve una transcripción fija o lanza un error."""

    model = "fake-vlm"

    def __init__(self, response: str = _TRANSCRIPTION_JSON, error: Exception | None = None) -> None:
        self.response = response
        self.error = error

    async def transcribe(self, images: list[bytes], prompt: str) -> str:
        if self.error is not None:
            raise self.error
        return self.response


class FakeLLM:
    """LLMProvider falso: devuelve una corrección fija."""

    model = "fake-llm"

    def __init__(self, response: str = _GRADING_JSON) -> None:
        self.response = response

    async def generate(self, prompt: str, schema: dict | None = None) -> str:
        return self.response


# --------------------------------------------------------------------------- #
# Fixtures y utilidades
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def storage(tmp_path):
    instance = LocalFileStorage(tmp_path / "storage")
    app.dependency_overrides[get_file_storage] = lambda: instance
    yield instance
    app.dependency_overrides.pop(get_file_storage, None)


@pytest.fixture
def fake_runner():
    """Sustituye el runner real por uno que solo registra los ids agendados."""
    calls: list[uuid.UUID] = []

    async def runner(exam_id: uuid.UUID) -> None:
        calls.append(exam_id)

    app.dependency_overrides[get_exam_runner] = lambda: runner
    yield calls
    app.dependency_overrides.pop(get_exam_runner, None)


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


async def _make_exam(
    session: AsyncSession, grading_session: GradingSession, **overrides
) -> Exam:
    exam = Exam(
        session_id=grading_session.id,
        filename=overrides.pop("filename", "examen.jpeg"),
        storage_path=overrides.pop("storage_path", "key/examen.jpeg"),
        status=overrides.pop("status", ExamStatus.PENDING),
        **overrides,
    )
    session.add(exam)
    await session.commit()
    await session.refresh(exam)
    return exam


def _login(client: AsyncClient, user: User) -> None:
    client.cookies.set(settings.session_cookie_name, sign_session(str(user.id)))


def _upload(client: AsyncClient, session_id, files):
    return client.post(f"/api/sessions/{session_id}/exams", files=files)


def _one_file(name="examen.pdf", content=b"%PDF-1.4 fake", mime="application/pdf"):
    return [("files", (name, content, mime))]


# --------------------------------------------------------------------------- #
# POST /exams — subida
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_upload_returns_202_and_creates_pending_exam(
    client: AsyncClient, session: AsyncSession, fake_runner: list, storage: LocalFileStorage
):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user, status=SessionStatus.READY)
    _login(client, user)

    resp = await _upload(client, gs.id, _one_file())

    assert resp.status_code == 202
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "pending"

    exams = (
        await session.execute(select(Exam).where(Exam.session_id == gs.id))
    ).scalars().all()
    assert len(exams) == 1
    assert exams[0].status == ExamStatus.PENDING
    assert await storage.exists(exams[0].storage_path)
    assert fake_runner == [exams[0].id]


@pytest.mark.asyncio
async def test_upload_accepts_multiple_exams(
    client: AsyncClient, session: AsyncSession, fake_runner: list
):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user, status=SessionStatus.READY)
    _login(client, user)

    files = [
        ("files", ("a.pdf", b"%PDF a", "application/pdf")),
        ("files", ("b.pdf", b"%PDF b", "application/pdf")),
        ("files", ("c.pdf", b"%PDF c", "application/pdf")),
    ]
    resp = await _upload(client, gs.id, files)

    assert resp.status_code == 202
    assert len(resp.json()) == 3
    assert len(fake_runner) == 3


@pytest.mark.asyncio
async def test_upload_rejects_more_than_max(
    client: AsyncClient, session: AsyncSession, fake_runner: list, monkeypatch
):
    monkeypatch.setattr(settings, "max_exams_per_upload", 2)
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user, status=SessionStatus.READY)
    _login(client, user)

    files = [("files", (f"{i}.pdf", b"%PDF", "application/pdf")) for i in range(3)]
    resp = await _upload(client, gs.id, files)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejected_when_session_not_ready(
    client: AsyncClient, session: AsyncSession, fake_runner: list
):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user, status=SessionStatus.DRAFT)
    _login(client, user)

    resp = await _upload(client, gs.id, _one_file())

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_upload_rejects_invalid_format(
    client: AsyncClient, session: AsyncSession, fake_runner: list
):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user, status=SessionStatus.READY)
    _login(client, user)

    resp = await _upload(
        client, gs.id, [("files", ("malware.exe", b"x", "application/octet-stream"))]
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejects_file_over_size_limit(
    client: AsyncClient, session: AsyncSession, fake_runner: list, monkeypatch
):
    monkeypatch.setattr(settings, "max_exam_upload_bytes", 10)
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user, status=SessionStatus.READY)
    _login(client, user)

    resp = await _upload(client, gs.id, _one_file(content=b"x" * 20))

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user, status=SessionStatus.READY)

    resp = await _upload(client, gs.id, _one_file())

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_other_user_forbidden(
    client: AsyncClient, session: AsyncSession, fake_runner: list
):
    owner = await _make_user(session, "owner@example.com")
    other = await _make_user(session, "other@example.com")
    gs = await _make_session(session, owner, status=SessionStatus.READY)
    _login(client, other)

    resp = await _upload(client, gs.id, _one_file())

    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# GET /exams/{exam_id} — detalle
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_get_exam_detail_pending_has_no_result(
    client: AsyncClient, session: AsyncSession
):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user, status=SessionStatus.READY)
    exam = await _make_exam(session, gs)
    _login(client, user)

    resp = await client.get(f"/api/sessions/{gs.id}/exams/{exam.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["result"] is None


@pytest.mark.asyncio
async def test_get_exam_detail_completed_includes_result(
    client: AsyncClient, session: AsyncSession
):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user, status=SessionStatus.READY)
    exam = await _make_exam(session, gs, status=ExamStatus.COMPLETED)
    session.add(
        GradingResult(
            exam_id=exam.id,
            total_score=8.5,
            rubric_filled=[
                {"item_name": "P1", "assigned_score": 8.5, "max_score": 10.0, "comment": "ok"}
            ],
            feedback_report="Informe",
            transcription={"answers": []},
            pipeline_metadata={},
        )
    )
    await session.commit()
    _login(client, user)

    resp = await client.get(f"/api/sessions/{gs.id}/exams/{exam.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["total_score"] == 8.5
    assert data["result"]["feedback_report"] == "Informe"
    assert data["result"]["rubric_filled"][0]["item_name"] == "P1"


@pytest.mark.asyncio
async def test_get_exam_detail_not_found(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user, status=SessionStatus.READY)
    _login(client, user)

    resp = await client.get(f"/api/sessions/{gs.id}/exams/{uuid.uuid4()}")

    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# process_exam — pipeline en background (con proveedores falsos, sin Ollama)
# --------------------------------------------------------------------------- #

async def _ready_session_with_material(
    session: AsyncSession, user: User
) -> GradingSession:
    gs = await _make_session(
        session,
        user,
        status=SessionStatus.READY,
        max_score=10.0,
        rubric_structured=[{"name": "Definición", "max_score": 10.0, "description": "Concepto"}],
    )
    await _add_document(
        session, gs, DocumentKind.MODEL_EXAM, extracted_text="Respuesta modelo de referencia."
    )
    return gs


@pytest.mark.asyncio
async def test_process_exam_completes_and_persists_result(
    session: AsyncSession, storage: LocalFileStorage
):
    user = await _make_user(session, "prof@example.com")
    gs = await _ready_session_with_material(session, user)

    key = f"{user.id}/{gs.id}/exams/examen.jpeg"
    await storage.save(b"fake image bytes", key)
    exam = await _make_exam(session, gs, filename="examen.jpeg", storage_path=key)

    await process_exam(exam.id, session, storage, FakeVLM(), FakeLLM())

    refreshed = await session.get(Exam, exam.id)
    assert refreshed.status == ExamStatus.COMPLETED
    assert refreshed.started_at is not None
    assert refreshed.completed_at is not None

    result = (
        await session.execute(select(GradingResult).where(GradingResult.exam_id == exam.id))
    ).scalar_one()
    assert result.total_score == 7.0
    assert result.feedback_report.startswith("Buen trabajo")


@pytest.mark.asyncio
async def test_process_exam_marks_error_on_pipeline_failure(
    session: AsyncSession, storage: LocalFileStorage
):
    user = await _make_user(session, "prof@example.com")
    gs = await _ready_session_with_material(session, user)

    key = f"{user.id}/{gs.id}/exams/examen.jpeg"
    await storage.save(b"fake image bytes", key)
    exam = await _make_exam(session, gs, filename="examen.jpeg", storage_path=key)

    failing_vlm = FakeVLM(error=ProviderError("modelo caído"))
    await process_exam(exam.id, session, storage, failing_vlm, FakeLLM())

    refreshed = await session.get(Exam, exam.id)
    assert refreshed.status == ExamStatus.ERROR
    assert "modelo caído" in refreshed.error_message

    result = (
        await session.execute(select(GradingResult).where(GradingResult.exam_id == exam.id))
    ).scalar_one_or_none()
    assert result is None
