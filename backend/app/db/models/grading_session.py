import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.exam import Exam
    from app.db.models.session_document import SessionDocument
    from app.db.models.user import User


class SessionStatus(enum.StrEnum):
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


class GradingSession(Base):
    __tablename__ = "grading_sessions"

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String)
    max_score: Mapped[float] = mapped_column(Float, default=10.0, server_default=text("10.0"))

    # Indicaciones del profesor (texto libre), separadas en las dos posibles.
    context_instructions: Mapped[str | None] = mapped_column(Text)
    model_exam_instructions: Mapped[str | None] = mapped_column(Text)

    # Rúbrica estructurada y validada por el profesor: lista de ítems
    rubric_structured: Mapped[list | None] = mapped_column(JSONB)

    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(
            SessionStatus,
            name="session_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=SessionStatus.DRAFT,
        server_default=text("'draft'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="grading_sessions")
    documents: Mapped[list["SessionDocument"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    exams: Mapped[list["Exam"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Exam.created_at, Exam.id",
    )
