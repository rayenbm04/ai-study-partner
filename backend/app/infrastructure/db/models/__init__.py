"""Import every model module so Base.metadata is fully populated for Alembic
autogenerate and for Base.metadata.create_all() in tests."""
from app.infrastructure.db.models.chunk import ChunkModel  # noqa: F401
from app.infrastructure.db.models.concept import ConceptModel  # noqa: F401
from app.infrastructure.db.models.concept_chunk import ConceptChunkModel  # noqa: F401
from app.infrastructure.db.models.concept_prerequisite import ConceptPrerequisiteModel  # noqa: F401
from app.infrastructure.db.models.document import DocumentModel  # noqa: F401
from app.infrastructure.db.models.embedding import EmbeddingModel  # noqa: F401
from app.infrastructure.db.models.refresh_token import RefreshTokenModel  # noqa: F401
from app.infrastructure.db.models.subject import SubjectModel  # noqa: F401
from app.infrastructure.db.models.user import UserModel  # noqa: F401
