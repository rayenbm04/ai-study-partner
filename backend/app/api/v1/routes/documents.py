import mimetypes
import re
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import Response

from app.api.v1.deps import get_current_user, get_current_user_from_header_or_query, get_document_service, get_ingestion_runner
from app.api.v1.schemas.document import DocumentResponse
from app.domain.entities.user import User
from app.services.document_service import DocumentService

# mimetypes doesn't reliably know markdown across platforms/Python versions —
# every other extension the backend supports is covered by the stdlib db.
_EXTRA_MIME_TYPES = {".md": "text/markdown"}

# original_filename is stored as-uploaded (unsanitized — only the on-disk
# path is sanitized, see LocalStorage._safe_filename), so it has to be
# cleaned before landing in a header value to rule out CRLF/quote injection.
_UNSAFE_HEADER_CHARS = re.compile(r'[\r\n"]+')

router = APIRouter(tags=["documents"])


@router.post(
    "/subjects/{subject_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    subject_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    run_ingestion: Callable[[str], Awaitable[None]] = Depends(get_ingestion_runner),
) -> DocumentResponse:
    content = await file.read()
    document = await service.upload(
        user_id=current_user.id, subject_id=subject_id, filename=file.filename or "upload", content=content
    )
    # Ingestion runs after the response is sent — the student sees the upload
    # succeed immediately with status "pending" and can poll GET /documents/{id}
    # (or Phase 4's chat UI can just show "still processing this document").
    background_tasks.add_task(run_ingestion, document.id)
    return DocumentResponse.from_entity(document)


@router.get("/subjects/{subject_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentResponse]:
    documents = await service.list_for_subject(current_user.id, subject_id)
    return [DocumentResponse.from_entity(d) for d in documents]


@router.get("/documents/{document_id}/content")
async def get_document_content(
    document_id: str,
    current_user: User = Depends(get_current_user_from_header_or_query),
    service: DocumentService = Depends(get_document_service),
) -> Response:
    document, content = await service.read_content(current_user.id, document_id)
    media_type = _EXTRA_MIME_TYPES.get(document.file_type) or mimetypes.guess_type(document.original_filename)[0]
    safe_filename = _UNSAFE_HEADER_CHARS.sub("_", document.original_filename)
    return Response(
        content=content,
        media_type=media_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    document = await service.get_owned(current_user.id, document_id)
    return DocumentResponse.from_entity(document)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> None:
    await service.delete(current_user.id, document_id)
