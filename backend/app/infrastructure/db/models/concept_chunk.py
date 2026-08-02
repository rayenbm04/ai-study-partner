from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class ConceptChunkModel(Base):
    """Which chunks of source material a concept was tagged from, and how
    relevant the LLM judged the match — this is what lets the progress engine
    later point a student back at the exact paragraph a weak concept came from."""

    __tablename__ = "concept_chunks"

    concept_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    chunk_id: Mapped[str] = mapped_column(String(36), ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True)
    relevance: Mapped[float] = mapped_column(Float, nullable=False)
