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
    document_type: str | None
    chapter_id: str | None
    lesson_id: str | None
    classification_confidence: float | None
    classified_at: datetime | None

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
            document_type=document.document_type,
            chapter_id=document.chapter_id,
            lesson_id=document.lesson_id,
            classification_confidence=document.classification_confidence,
            classified_at=document.classified_at,
        )
