"""Import every model module so Base.metadata is fully populated for Alembic
autogenerate and for Base.metadata.create_all() in tests."""
from app.infrastructure.db.models.chunk import ChunkModel  # noqa: F401
from app.infrastructure.db.models.concept import ConceptModel  # noqa: F401
from app.infrastructure.db.models.concept_chunk import ConceptChunkModel  # noqa: F401
from app.infrastructure.db.models.concept_prerequisite import ConceptPrerequisiteModel  # noqa: F401
from app.infrastructure.db.models.conversation import ConversationModel  # noqa: F401
from app.infrastructure.db.models.document import DocumentModel  # noqa: F401
from app.infrastructure.db.models.embedding import EmbeddingModel  # noqa: F401
from app.infrastructure.db.models.flashcard import FlashcardModel  # noqa: F401
from app.infrastructure.db.models.flashcard_review import FlashcardReviewModel  # noqa: F401
from app.infrastructure.db.models.message import MessageModel  # noqa: F401
from app.infrastructure.db.models.progress import ProgressModel  # noqa: F401
from app.infrastructure.db.models.quiz import QuizModel  # noqa: F401
from app.infrastructure.db.models.quiz_attempt import QuizAttemptModel  # noqa: F401
from app.infrastructure.db.models.quiz_question import QuizQuestionModel  # noqa: F401
from app.infrastructure.db.models.refresh_token import RefreshTokenModel  # noqa: F401
from app.infrastructure.db.models.student_answer import StudentAnswerModel  # noqa: F401
from app.infrastructure.db.models.study_plan import StudyPlanModel  # noqa: F401
from app.infrastructure.db.models.study_plan_item import StudyPlanItemModel  # noqa: F401
from app.infrastructure.db.models.subject import SubjectModel  # noqa: F401
from app.infrastructure.db.models.summary import SummaryModel  # noqa: F401
from app.infrastructure.db.models.user import UserModel  # noqa: F401
from app.infrastructure.db.models.weak_concept import WeakConceptModel  # noqa: F401
