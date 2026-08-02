from datetime import datetime

from pydantic import BaseModel

from app.domain.entities.progress import WeakConcept
from app.services.progress_engine.mastery import ConceptMastery


class ConceptMasteryResponse(BaseModel):
    concept_id: str
    name: str
    mastery_score: float | None
    trend: str | None
    children: list["ConceptMasteryResponse"] = []

    @classmethod
    def from_domain(cls, node: ConceptMastery) -> "ConceptMasteryResponse":
        return cls(
            concept_id=node.concept_id,
            name=node.name,
            mastery_score=node.mastery_score,
            trend=node.trend,
            children=[cls.from_domain(child) for child in node.children],
        )


# Needed because ConceptMasteryResponse refers to itself in its own field annotation.
ConceptMasteryResponse.model_rebuild()


class WeakConceptResponse(BaseModel):
    id: str
    concept_id: str
    reason: str
    confidence: float
    status: str
    detected_at: datetime

    @classmethod
    def from_entity(cls, weak_concept: WeakConcept) -> "WeakConceptResponse":
        return cls(
            id=weak_concept.id,
            concept_id=weak_concept.concept_id,
            reason=weak_concept.reason,
            confidence=weak_concept.confidence,
            status=weak_concept.status,
            detected_at=weak_concept.detected_at,
        )
