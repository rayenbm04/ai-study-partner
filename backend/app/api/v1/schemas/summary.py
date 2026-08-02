from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.domain.entities.summary import Summary

SummaryType = Literal["short", "detailed", "bullet", "key_concepts", "formula_sheet", "definitions"]


class SummaryRequest(BaseModel):
    document_id: str
    summary_type: SummaryType


class SummaryResponse(BaseModel):
    id: str
    document_id: str
    subject_id: str
    summary_type: str
    content: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, summary: Summary) -> "SummaryResponse":
        return cls(
            id=summary.id,
            document_id=summary.document_id,
            subject_id=summary.subject_id,
            summary_type=summary.summary_type,
            content=summary.content,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
        )
