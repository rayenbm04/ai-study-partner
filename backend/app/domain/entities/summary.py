from dataclasses import dataclass
from datetime import datetime

# The six study-aid formats the architecture doc calls for. Kept as a plain
# tuple (not an enum) so it's trivial to check membership from both the
# service layer and the pydantic schema without an import cycle.
SUMMARY_TYPES = ("short", "detailed", "bullet", "key_concepts", "formula_sheet", "definitions")


@dataclass(frozen=True, slots=True)
class Summary:
    id: str
    document_id: str
    subject_id: str
    summary_type: str
    content: str
    created_at: datetime
    updated_at: datetime
