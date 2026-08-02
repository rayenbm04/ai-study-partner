from datetime import datetime

from pydantic import BaseModel

from app.domain.entities.document import Document


class DocumentResponse(BaseModel):
    id: str
    subject_id: str
    original_filename: str
    file_type: str
    status: str
    page_count: int | None
    error_message: str | None
    uploaded_at: datetime

    @classmethod
    def from_entity(cls, document: Document) -> "DocumentResponse":
        return cls(
            id=document.id,
            subject_id=document.subject_id,
            original_filename=document.original_filename,
            file_type=document.file_type,
            status=document.status,
            page_count=document.page_count,
            error_message=document.error_message,
            uploaded_at=document.uploaded_at,
        )
