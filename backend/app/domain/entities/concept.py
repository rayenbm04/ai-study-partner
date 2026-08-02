from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Concept:
    id: str
    subject_id: str
    name: str
    description: str | None
    parent_concept_id: str | None
