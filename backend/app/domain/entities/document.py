from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    subject_id: str
    original_filename: str
    storage_path: str
    file_type: str
    status: str  # pending | processing | ready | failed
    page_count: int | None
    error_message: str | None
    uploaded_at: datetime
    document_type: str | None = None  # exam | resume | td | tp | cours | other
    chapter_id: str | None = None
    lesson_id: str | None = None
    classification_confidence: float | None = None
    classified_at: datetime | None = None
    content_hash: str | None = None  # sha256 of the raw upload — dedup key, scoped per subject
    # Granular sub-status within "processing", for the upload-progress UI —
    # status stays the coarse pending|processing|ready|failed a client
    # branches on; these are optional extra detail on top of it.
    processing_step: str | None = None  # extracting | chunking | embedding | classifying | tagging_concepts
    processing_progress: int | None = None  # 0-100
