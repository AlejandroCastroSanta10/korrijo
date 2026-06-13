import logging
import mimetypes
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Response, UploadFile, status

from app.api.deps import CurrentUserDep, LLMDep, SessionDep, StorageDep
from app.api.sessions_common import load_session, owned_or_error, to_session_detail
from app.db.models.grading_session import GradingSession, SessionStatus
from app.db.models.session_document import DocumentKind, SessionDocument
from app.pipeline.errors import ProviderError
from app.pipeline.extractors import ScannedPDFNotSupportedError, UnsupportedFormatError
from app.pipeline.llm.base import LLMProvider
from app.pipeline.rubric import RubricParseError, parse_rubric
from app.schemas.session import (
    DocumentUploadResponse,
    RubricStructured,
    RubricValidateRequest,
    SessionDetail,
    SessionDocumentDetail,
)
from app.services.documents import (
    ALLOWED_EXTENSIONS,
    extract_document_text,
    size_limit_for,
)
from app.services.storage.base import FileStorage, InvalidKey, StorageError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["documents"])

_SINGLETON_KINDS = {DocumentKind.RUBRIC, DocumentKind.MODEL_EXAM}

_RUBRIC_SUM_TOLERANCE = 0.01


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _document_or_error(grading_session: GradingSession, document_id: UUID) -> SessionDocument:
    """Devuelve el documento de la sesión"""
    for doc in grading_session.documents:
        if doc.id == document_id:
            return doc
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


async def _build_rubric_structured(
    rubric_text: str, max_score: float, llm: LLMProvider
) -> RubricStructured:
    """Estructura la rúbrica y comprueba que la suma de puntos cuadre con max_score."""
    try:
        items = await parse_rubric(rubric_text, llm)
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo estructurar la rúbrica: {exc}",
        ) from exc
    except RubricParseError:
        return RubricStructured(
            items=[],
            total_max_score=0.0,
            warning="No se pudo interpretar la rúbrica automáticamente. Revísala manualmente.",
        )

    total = sum(item.max_score for item in items)
    warning = None
    if abs(total - max_score) > _RUBRIC_SUM_TOLERANCE:
        warning = (
            f"La suma de los puntos de los ítems ({total:g}) no coincide con la "
            f"puntuación máxima de la sesión ({max_score:g}). Revísala antes de validar."
        )
    return RubricStructured(items=items, total_max_score=total, warning=warning)


def _validate_upload(filename: str, content: bytes, kind: DocumentKind) -> None:
    """Valida la extensión y el tamaño del fichero; lanza 422 si no cumplen."""
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Formato no admitido para '{filename}'. "
                f"Admitidos: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            ),
        )
    limit = size_limit_for(kind)
    if len(content) > limit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"El fichero supera el tamaño máximo permitido ({limit // (1024 * 1024)} MB).",
        )


async def _extract_or_422(content: bytes, filename: str) -> str:
    """Extrae el texto; mapea formato no soportado / PDF escaneado a 422."""
    try:
        return await extract_document_text(content, filename)
    except (UnsupportedFormatError, ScannedPDFNotSupportedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


async def _store_document(
    session: SessionDep,
    storage: StorageDep,
    grading_session: GradingSession,
    *,
    user_id: UUID,
    kind: DocumentKind,
    filename: str,
    content: bytes,
    content_type: str | None,
    extracted_text: str,
) -> SessionDocument:
    """Guarda el fichero, reemplaza el documento único previo y persiste el registro."""
    try:
        key = FileStorage.key_for(user_id, grading_session.id, filename)
    except InvalidKey as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    try:
        await storage.save(content, key)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No se pudo guardar el fichero: {exc}",
        ) from exc

    # Rúbrica y examen modelo son únicos por sesión: se borran los previos (BD +
    # storage)
    stale_keys: list[str] = []
    if kind in _SINGLETON_KINDS:
        for old in [d for d in grading_session.documents if d.kind == kind]:
            await session.delete(old)
            if old.storage_path != key:
                stale_keys.append(old.storage_path)

    document = SessionDocument(
        session_id=grading_session.id,
        kind=kind,
        filename=filename,
        storage_path=key,
        size_bytes=len(content),
        mime_type=content_type
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream",
        extracted_text=extracted_text,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)

    for old_key in stale_keys:
        try:
            await storage.delete(old_key)
        except StorageError as exc:
            logger.warning("No se pudo borrar el fichero reemplazado '%s': %s", old_key, exc)

    return document


# --------------------------------------------------------------------------- #
# Documentos iniciales de la sesión (fase 1)
# --------------------------------------------------------------------------- #

@router.post(
    "/{session_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentUploadResponse,
)
async def upload_document(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    storage: StorageDep,
    llm: LLMDep,
    kind: Annotated[DocumentKind, Form()],
    file: UploadFile,
) -> DocumentUploadResponse:
    grading_session = owned_or_error(await load_session(session, session_id), current_user)

    filename = file.filename or ""
    content = await file.read()
    _validate_upload(filename, content, kind)

    # Se extrae antes de tocar el storage: un documento no procesable se rechaza
    extracted_text = await _extract_or_422(content, filename)

    document = await _store_document(
        session,
        storage,
        grading_session,
        user_id=current_user.id,
        kind=kind,
        filename=filename,
        content=content,
        content_type=file.content_type,
        extracted_text=extracted_text,
    )

    rubric = (
        await _build_rubric_structured(extracted_text, grading_session.max_score, llm)
        if kind == DocumentKind.RUBRIC
        else None
    )
    return DocumentUploadResponse(
        **SessionDocumentDetail.model_validate(document).model_dump(),
        rubric=rubric,
    )


@router.get(
    "/{session_id}/documents/{document_id}", response_model=SessionDocumentDetail
)
async def get_document(
    session_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> SessionDocumentDetail:
    grading_session = owned_or_error(await load_session(session, session_id), current_user)
    document = _document_or_error(grading_session, document_id)
    return SessionDocumentDetail.model_validate(document)


@router.get("/{session_id}/documents/{document_id}/raw")
async def download_document(
    session_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    storage: StorageDep,
) -> Response:
    grading_session = owned_or_error(await load_session(session, session_id), current_user)
    document = _document_or_error(grading_session, document_id)
    try:
        content = await storage.read(document.storage_path)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El fichero ya no está disponible: {exc}",
        ) from exc
    return Response(
        content=content,
        media_type=document.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{document.filename}"'},
    )


@router.delete(
    "/{session_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_document(
    session_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    storage: StorageDep,
) -> None:
    grading_session = owned_or_error(await load_session(session, session_id), current_user)
    document = _document_or_error(grading_session, document_id)

    key = document.storage_path
    await session.delete(document)
    await session.commit()

    try:
        await storage.delete(key)
    except StorageError as exc:
        logger.warning("No se pudo borrar el fichero '%s' del documento: %s", key, exc)


# --------------------------------------------------------------------------- #
# Validación de la rúbrica (con esto fase 1 -> fase 2)
# --------------------------------------------------------------------------- #

@router.post("/{session_id}/rubric/validate", response_model=SessionDetail)
async def validate_rubric(
    session_id: UUID,
    body: RubricValidateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> SessionDetail:
    grading_session = owned_or_error(await load_session(session, session_id), current_user)

    kinds = {doc.kind for doc in grading_session.documents}
    if DocumentKind.RUBRIC not in kinds:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Sube primero la rúbrica de la sesión.",
        )
    if DocumentKind.MODEL_EXAM not in kinds:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Falta el examen modelo, obligatorio para pasar a la fase de corrección.",
        )

    grading_session.rubric_structured = [item.model_dump() for item in body.items]
    grading_session.status = SessionStatus.READY
    await session.commit()

    refreshed = await load_session(session, session_id)
    return to_session_detail(refreshed)
