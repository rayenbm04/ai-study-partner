from collections.abc import Awaitable, Callable

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status

from app.api.v1.deps import get_current_user, get_document_service, get_ingestion_runner
from app.api.v1.schemas.document import DocumentResponse
from app.domain.entities.user import User
from app.services.document_service import DocumentService

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
