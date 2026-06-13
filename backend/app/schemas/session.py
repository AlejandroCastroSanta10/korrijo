from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.exam import ExamStatus
from app.db.models.grading_session import SessionStatus
from app.db.models.session_document import DocumentKind
from app.pipeline.grading import RubricItemResult
from app.pipeline.rubric import RubricItem


class SessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    max_score: float = Field(default=10.0, gt=0)
    context_instructions: str | None = None
    model_exam_instructions: str | None = None


class SessionDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: DocumentKind
    filename: str
    size_bytes: int
    mime_type: str
    created_at: datetime


class SessionDocumentDetail(SessionDocumentRead):
    """Documento con su texto extraído."""

    extracted_text: str | None = None


class RubricStructured(BaseModel):
    """Rúbrica estructurada en ítems, con la comprobación de suma de puntos."""

    items: list[RubricItem]
    total_max_score: float
    warning: str | None = None


class DocumentUploadResponse(SessionDocumentDetail):
    """Respuesta a la subida de un documento. 'rubric' solo viene para rúbricas."""

    rubric: RubricStructured | None = None


class RubricValidateRequest(BaseModel):
    items: list[RubricItem] = Field(min_length=1)


class ExamRead(BaseModel):
    id: UUID
    filename: str
    status: ExamStatus
    total_score: float | None = None
    error_message: str | None = None
    created_at: datetime


class GradingResultRead(BaseModel):
    """Resultado de la corrección de un examen."""

    total_score: float
    rubric_filled: list[RubricItemResult]
    feedback_report: str
    created_at: datetime


class ExamDetail(ExamRead):
    """Examen con su resultado, presente solo si está completado."""

    result: GradingResultRead | None = None


class SessionRead(BaseModel):
    id: UUID
    name: str
    max_score: float
    status: SessionStatus
    context_instructions: str | None
    model_exam_instructions: str | None
    created_at: datetime
    updated_at: datetime
    graded_count: int
    passed_count: int
    failed_count: int
    average_score: float | None


class SessionDetail(SessionRead):
    documents: list[SessionDocumentRead]
    exams: list[ExamRead]
