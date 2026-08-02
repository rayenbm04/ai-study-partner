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
