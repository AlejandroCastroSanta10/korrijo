import uuid
from io import BytesIO
from types import SimpleNamespace

import pdfplumber
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.exam import Exam, ExamStatus
from app.db.models.grading_result import GradingResult
from app.db.models.grading_session import GradingSession, SessionStatus
from app.db.models.user import User
from app.services.pdf_generator import (
    generate_feedback_report_pdf,
    generate_filled_rubric_pdf,
    student_display_name,
    student_dni,
)
from app.services.session import sign_session

# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #

def _pdf_text(content: bytes) -> str:
    with pdfplumber.open(BytesIO(content)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


async def _make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _make_session(session: AsyncSession, user: User, **overrides) -> GradingSession:
    grading_session = GradingSession(
        user_id=user.id,
        name=overrides.pop("name", "Examen Historia T1"),
        status=SessionStatus.READY,
        max_score=overrides.pop("max_score", 10.0),
        **overrides,
    )
    session.add(grading_session)
    await session.commit()
    await session.refresh(grading_session)
    return grading_session


async def _make_completed_exam(
    session: AsyncSession, grading_session: GradingSession, **overrides
) -> Exam:
    exam = Exam(
        session_id=grading_session.id,
        filename=overrides.pop("filename", "Examen_AlejandroCastro.pdf"),
        storage_path="key/x.pdf",
        status=overrides.pop("status", ExamStatus.COMPLETED),
    )
    session.add(exam)
    await session.commit()
    await session.refresh(exam)
    if exam.status == ExamStatus.COMPLETED:
        session.add(
            GradingResult(
                exam_id=exam.id,
                total_score=overrides.pop("total_score", 7.5),
                rubric_filled=overrides.pop(
                    "rubric_filled",
                    [
                        {"item_name": "Definición", "assigned_score": 4.5, "max_score": 6.0, "comment": "Correcta"},
                        {"item_name": "Ejemplo", "assigned_score": 3.0, "max_score": 4.0, "comment": ""},
                    ],
                ),
                feedback_report=overrides.pop(
                    "feedback_report", "Buen trabajo.\nMejora los ejemplos del segundo apartado."
                ),
                transcription={
                    "metadata": {"nombre": "Alejandro", "apellidos": "Castro"},
                    "answers": [],
                },
                pipeline_metadata={},
            )
        )
        await session.commit()
        await session.refresh(exam, attribute_names=["result"])
    return exam


def _login(client: AsyncClient, user: User) -> None:
    client.cookies.set(settings.session_cookie_name, sign_session(str(user.id)))


# --------------------------------------------------------------------------- #
# Servicio de generación
# --------------------------------------------------------------------------- #

def test_student_display_name_uses_extracted_metadata():
    result = SimpleNamespace(
        transcription={"metadata": {"nombre": "María", "apellidos": "López"}}
    )
    assert student_display_name(result) == "María López"


def test_student_display_name_anonymous_when_missing():
    assert (
        student_display_name(SimpleNamespace(transcription={"answers": []}))
        == "Anónimo"
    )
    assert student_display_name(SimpleNamespace(transcription=None)) == "Anónimo"


def test_student_dni_uses_extracted_metadata():
    result = SimpleNamespace(transcription={"metadata": {"dni": "12345678A"}})
    assert student_dni(result) == "12345678A"


def test_student_dni_unknown_when_missing():
    assert student_dni(SimpleNamespace(transcription={"answers": []})) == "Desconocido"
    assert student_dni(SimpleNamespace(transcription=None)) == "Desconocido"


@pytest.mark.asyncio
async def test_rubric_pdf_is_valid_and_contains_items(
    session: AsyncSession
):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user)
    exam = await _make_completed_exam(session, gs)

    pdf = generate_filled_rubric_pdf(exam.result, gs)

    assert pdf.startswith(b"%PDF")
    text = _pdf_text(pdf)
    assert "Definición" in text
    assert "Alejandro Castro" in text  # nombre extraído por el modelo
    assert "Desconocido" in text  # DNI no presente en metadata -> fallback
    assert "7,5 / 10" in text  # total destacado, con coma decimal (es-ES)


@pytest.mark.asyncio
async def test_feedback_pdf_contains_disclaimer_and_report(session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user)
    exam = await _make_completed_exam(session, gs)

    pdf = generate_feedback_report_pdf(exam.result, gs)

    assert pdf.startswith(b"%PDF")
    text = _pdf_text(pdf).lower()
    assert "orientativa" in text  # disclaimer obligatorio
    assert "buen trabajo" in text


# --------------------------------------------------------------------------- #
# Endpoints de descarga
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_download_rubric_pdf(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user)
    exam = await _make_completed_exam(session, gs)
    _login(client, user)

    resp = await client.get(f"/api/sessions/{gs.id}/exams/{exam.id}/rubric.pdf")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert "Alejandro_Castro" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_download_feedback_pdf_has_disclaimer(
    client: AsyncClient, session: AsyncSession
):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user)
    exam = await _make_completed_exam(session, gs)
    _login(client, user)

    resp = await client.get(f"/api/sessions/{gs.id}/exams/{exam.id}/feedback.pdf")

    assert resp.status_code == 200
    assert "Alejandro_Castro" in resp.headers["content-disposition"]
    assert "orientativa" in _pdf_text(resp.content).lower()


@pytest.mark.asyncio
async def test_download_pdf_409_when_not_graded(
    client: AsyncClient, session: AsyncSession
):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user)
    exam = await _make_completed_exam(session, gs, status=ExamStatus.PENDING)
    _login(client, user)

    resp = await client.get(f"/api/sessions/{gs.id}/exams/{exam.id}/rubric.pdf")

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_download_pdf_404_when_exam_missing(
    client: AsyncClient, session: AsyncSession
):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user)
    _login(client, user)

    resp = await client.get(f"/api/sessions/{gs.id}/exams/{uuid.uuid4()}/feedback.pdf")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_pdf_requires_auth(client: AsyncClient, session: AsyncSession):
    user = await _make_user(session, "prof@example.com")
    gs = await _make_session(session, user)
    exam = await _make_completed_exam(session, gs)

    resp = await client.get(f"/api/sessions/{gs.id}/exams/{exam.id}/rubric.pdf")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_download_pdf_other_user_forbidden(
    client: AsyncClient, session: AsyncSession
):
    owner = await _make_user(session, "owner@example.com")
    other = await _make_user(session, "other@example.com")
    gs = await _make_session(session, owner)
    exam = await _make_completed_exam(session, gs)
    _login(client, other)

    resp = await client.get(f"/api/sessions/{gs.id}/exams/{exam.id}/rubric.pdf")

    assert resp.status_code == 403
