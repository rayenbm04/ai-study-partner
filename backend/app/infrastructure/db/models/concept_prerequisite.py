from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class ConceptPrerequisiteModel(Base):
    """Edge in the per-subject concept DAG: concept_id requires prerequisite_id."""

    __tablename__ = "concept_prerequisites"

    concept_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
