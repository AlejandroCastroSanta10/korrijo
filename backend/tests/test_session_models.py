import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.exam import Exam, ExamStatus
from app.db.models.grading_result import GradingResult
from app.db.models.grading_session import GradingSession, SessionStatus
from app.db.models.session_document import DocumentKind, SessionDocument
from app.db.models.user import User


async def _make_user(session: AsyncSession, email: str = "prof@example.com") -> User:
    user = User(email=email)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _make_full_session(session: AsyncSession, user: User) -> GradingSession:
    """Crea una sesión con un documento, un examen y su resultado."""
    grading_session = GradingSession(user_id=user.id, name="Examen de junio")
    grading_session.documents.append(
        SessionDocument(
            kind=DocumentKind.RUBRIC,
            filename="rubrica.pdf",
            storage_path="prof/sesion/rubrica.pdf",
            size_bytes=1024,
            mime_type="application/pdf",
        )
    )
    exam = Exam(filename="alumno1.pdf", storage_path="prof/sesion/alumno1.pdf")
    exam.result = GradingResult(
        total_score=7.5,
        rubric_filled=[{"item_name": "Pregunta 1", "assigned_score": 2.0, "max_score": 2.0}],
        feedback_report="Buen trabajo.",
        transcription={"answers": []},
        pipeline_metadata={"llm_model": "test"},
    )
    grading_session.exams.append(exam)
    session.add(grading_session)
    await session.commit()
    await session.refresh(grading_session)
    return grading_session


@pytest.mark.asyncio
async def test_create_session_applies_defaults(session: AsyncSession):
    user = await _make_user(session)

    grading_session = GradingSession(user_id=user.id, name="Sesión sin material")
    session.add(grading_session)
    await session.commit()
    await session.refresh(grading_session)

    assert grading_session.id is not None
    assert grading_session.max_score == 10.0
    assert grading_session.status == SessionStatus.DRAFT
    assert grading_session.created_at is not None


@pytest.mark.asyncio
async def test_create_full_graph_and_navigate_relationships(session: AsyncSession):
    user = await _make_user(session)
    grading_session = await _make_full_session(session, user)

    loaded = (
        await session.execute(
            select(GradingSession)
            .options(
                selectinload(GradingSession.documents),
                selectinload(GradingSession.exams).selectinload(Exam.result),
            )
            .where(GradingSession.id == grading_session.id)
        )
    ).scalar_one()

    assert len(loaded.documents) == 1
    assert loaded.documents[0].kind == DocumentKind.RUBRIC
    assert len(loaded.exams) == 1
    exam = loaded.exams[0]
    assert exam.status == ExamStatus.PENDING
    assert exam.result is not None
    assert exam.result.total_score == 7.5


@pytest.mark.asyncio
async def test_navigation_from_user_to_sessions(session: AsyncSession):
    user = await _make_user(session)
    await _make_full_session(session, user)

    loaded = (
        await session.execute(
            select(User)
            .options(selectinload(User.grading_sessions))
            .where(User.id == user.id)
        )
    ).scalar_one()

    assert len(loaded.grading_sessions) == 1
    assert loaded.grading_sessions[0].name == "Examen de junio"


@pytest.mark.asyncio
async def test_deleting_session_cascades_to_children(session: AsyncSession):
    user = await _make_user(session)
    grading_session = await _make_full_session(session, user)
    session_id = grading_session.id

    await session.delete(grading_session)
    await session.commit()

    for model in (SessionDocument, Exam):
        count = (
            await session.execute(
                select(func.count()).where(model.session_id == session_id)
            )
        ).scalar_one()
        assert count == 0

    results = (
        await session.execute(select(func.count()).select_from(GradingResult))
    ).scalar_one()
    assert results == 0
