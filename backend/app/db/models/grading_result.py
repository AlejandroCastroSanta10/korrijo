from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.exam import Exam


class GradingResult(Base):
    __tablename__ = "grading_results"

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    exam_id: Mapped[UUID] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"), unique=True
    )
    total_score: Mapped[float] = mapped_column(Float)
   
    # Lista de ítems con puntuación y comentario + informe resumen. Estos dos son los que componen el feedback report.
    rubric_filled: Mapped[list] = mapped_column(JSONB)
    feedback_report: Mapped[str] = mapped_column(Text)
    
    # Transcripción estructurada del examen, guardada para auditoría.
    transcription: Mapped[dict] = mapped_column(JSONB)
    
    # Metadatos de la ejecución del pipeline (modelos, tiempos, etc.).
    pipeline_metadata: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    exam: Mapped["Exam"] = relationship(back_populates="result")
