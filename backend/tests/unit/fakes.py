"""In-memory fakes for the repository interfaces, used by unit tests so
service logic is verified with no database, no event loop surprises, and no
test fixtures beyond plain Python dicts."""
import math
import uuid
from dataclasses import replace
from datetime import datetime, timezone

from app.domain.entities.chunk import Chunk
from app.domain.entities.concept import Concept
from app.domain.entities.conversation import Conversation
from app.domain.entities.curriculum import AcademicLevel, Chapter, Country, CurriculumSubject, EducationSystem, Lesson, Section
from app.domain.entities.document import Document
from app.domain.entities.flashcard import Flashcard, FlashcardReview
from app.domain.entities.message import Message
from app.domain.entities.progress import Progress, WeakConcept
from app.domain.entities.quiz import Quiz, QuizAttempt, QuizQuestion, StudentAnswer
from app.domain.entities.refresh_token import RefreshToken
from app.domain.entities.study_plan import StudyPlan, StudyPlanItem
from app.domain.entities.subject import Subject
from app.domain.entities.summary import Summary
from app.domain.entities.user import User
from app.domain.repositories.chunk_repository import ChunkRepository
from app.domain.repositories.concept_chunk_repository import ConceptChunkRepository
from app.domain.repositories.concept_repository import ConceptRepository
from app.domain.repositories.conversation_repository import ConversationRepository
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.embedding_repository import EmbeddingRepository
from app.domain.repositories.flashcard_repository import FlashcardRepository
from app.domain.repositories.flashcard_review_repository import FlashcardReviewRepository
from app.domain.repositories.message_repository import MessageRepository
from app.domain.repositories.progress_repository import ProgressRepository
from app.domain.repositories.quiz_attempt_repository import QuizAttemptRepository
from app.domain.repositories.quiz_repository import QuizRepository
from app.domain.repositories.refresh_token_repository import RefreshTokenRepository
from app.domain.repositories.student_answer_repository import StudentAnswerRepository
from app.domain.repositories.study_plan_repository import StudyPlanRepository
from app.domain.repositories.subject_repository import SubjectRepository
from app.domain.repositories.summary_repository import SummaryRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.repositories.weak_concept_repository import WeakConceptRepository
from app.infrastructure.storage.base import StoragePort
from app.services.embeddings.base import EmbeddingProvider
from app.services.llm.base import LLMProvider


class FakeUserRepository(UserRepository):
    def __init__(self):
        self._by_id: dict[str, User] = {}

    async def get_by_id(self, user_id):
        return self._by_id.get(user_id)

    async def get_by_email(self, email):
        return next((u for u in self._by_id.values() if u.email == email), None)

    async def create(self, *, email, firstname, lastname, hashed_password, role="student"):
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            firstname=firstname,
            lastname=lastname,
            hashed_password=hashed_password,
            role=role,
            created_at=datetime.now(timezone.utc),
        )
        self._by_id[user.id] = user
        return user


class FakeRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self):
        self._by_id: dict[str, RefreshToken] = {}

    async def store(self, *, user_id, token_hash, expires_at):
        token = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
            created_at=datetime.now(timezone.utc),
        )
        self._by_id[token.id] = token
        return token

    async def get_active_by_hash(self, token_hash):
        token = next((t for t in self._by_id.values() if t.token_hash == token_hash), None)
        if token is None or not token.is_active or token.expires_at < datetime.now(timezone.utc):
            return None
        return token

    async def revoke(self, token_id):
        token = self._by_id.get(token_id)
        if token is not None:
            self._by_id[token_id] = RefreshToken(
                id=token.id,
                user_id=token.user_id,
                token_hash=token.token_hash,
                expires_at=token.expires_at,
                revoked_at=datetime.now(timezone.utc),
                created_at=token.created_at,
            )

    async def revoke_all_for_user(self, user_id):
        for token_id, token in list(self._by_id.items()):
            if token.user_id == user_id and token.is_active:
                await self.revoke(token_id)


class FakeSubjectRepository(SubjectRepository):
    def __init__(self):
        self._by_id: dict[str, Subject] = {}

    async def list_by_user(self, user_id, *, include_archived=False):
        subjects = [s for s in self._by_id.values() if s.user_id == user_id]
        if not include_archived:
            subjects = [s for s in subjects if not s.is_archived]
        return sorted(subjects, key=lambda s: s.created_at, reverse=True)

    async def get_by_id(self, subject_id):
        return self._by_id.get(subject_id)

    async def get_by_user_and_name(self, user_id, name):
        return next(
            (s for s in self._by_id.values() if s.user_id == user_id and s.name == name and not s.is_archived), None
        )

    async def create(self, *, user_id, name, description, color, icon, curriculum_subject_id=None):
        subject = Subject(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            color=color,
            icon=icon,
            created_at=datetime.now(timezone.utc),
            archived_at=None,
            curriculum_subject_id=curriculum_subject_id,
        )
        self._by_id[subject.id] = subject
        return subject

    async def update(self, subject_id, **fields):
        subject = self._by_id[subject_id]
        updates = {k: v for k, v in fields.items() if v is not None}
        updated = replace(subject, **updates)
        self._by_id[subject_id] = updated
        return updated

    async def archive(self, subject_id):
        subject = self._by_id[subject_id]
        self._by_id[subject_id] = replace(subject, archived_at=datetime.now(timezone.utc))

    async def delete_all_for_user(self, user_id):
        for subject_id in [s.id for s in self._by_id.values() if s.user_id == user_id]:
            del self._by_id[subject_id]


class FakeDocumentRepository(DocumentRepository):
    def __init__(self):
        self._by_id: dict[str, Document] = {}

    async def create(self, *, document_id, subject_id, original_filename, storage_path, file_type):
        document = Document(
            id=document_id,
            subject_id=subject_id,
            original_filename=original_filename,
            storage_path=storage_path,
            file_type=file_type,
            status="pending",
            page_count=None,
            error_message=None,
            uploaded_at=datetime.now(timezone.utc),
        )
        self._by_id[document.id] = document
        return document

    async def get_by_id(self, document_id):
        return self._by_id.get(document_id)

    async def list_by_subject(self, subject_id):
        docs = [d for d in self._by_id.values() if d.subject_id == subject_id]
        return sorted(docs, key=lambda d: d.uploaded_at, reverse=True)

    async def mark_processing(self, document_id):
        self._by_id[document_id] = replace(self._by_id[document_id], status="processing")

    async def mark_ready(self, document_id, *, page_count):
        self._by_id[document_id] = replace(
            self._by_id[document_id], status="ready", page_count=page_count, error_message=None
        )

    async def mark_failed(self, document_id, *, error_message):
        self._by_id[document_id] = replace(self._by_id[document_id], status="failed", error_message=error_message)

    async def set_classification(self, document_id, *, document_type, chapter_id, lesson_id, confidence):
        self._by_id[document_id] = replace(
            self._by_id[document_id],
            document_type=document_type,
            chapter_id=chapter_id,
            lesson_id=lesson_id,
            classification_confidence=confidence,
            classified_at=datetime.now(timezone.utc),
        )

    async def delete(self, document_id):
        self._by_id.pop(document_id, None)


class FakeCurriculumRepository(CurriculumRepository):
    def __init__(self):
        self._countries: dict[str, Country] = {}
        self._education_systems: dict[str, EducationSystem] = {}
        self._academic_levels: dict[str, AcademicLevel] = {}
        self._sections: dict[str, Section] = {}
        self._subjects: dict[str, CurriculumSubject] = {}
        self._chapters: dict[str, Chapter] = {}
        self._lessons: dict[str, Lesson] = {}

    async def list_countries(self):
        return list(self._countries.values())

    async def create_country(self, *, name, code):
        country = Country(id=str(uuid.uuid4()), name=name, code=code, created_at=datetime.now(timezone.utc))
        self._countries[country.id] = country
        return country

    async def list_education_systems(self, country_id):
        return [s for s in self._education_systems.values() if s.country_id == country_id]

    async def create_education_system(self, *, country_id, name):
        system = EducationSystem(id=str(uuid.uuid4()), country_id=country_id, name=name, created_at=datetime.now(timezone.utc))
        self._education_systems[system.id] = system
        return system

    async def list_academic_levels(self, education_system_id):
        return [lvl for lvl in self._academic_levels.values() if lvl.education_system_id == education_system_id]

    async def create_academic_level(self, *, education_system_id, name, order_index):
        level = AcademicLevel(
            id=str(uuid.uuid4()), education_system_id=education_system_id, name=name, order_index=order_index,
            created_at=datetime.now(timezone.utc),
        )
        self._academic_levels[level.id] = level
        return level

    async def get_academic_level(self, academic_level_id):
        return self._academic_levels.get(academic_level_id)

    async def list_sections(self, academic_level_id):
        return [s for s in self._sections.values() if s.academic_level_id == academic_level_id]

    async def create_section(self, *, academic_level_id, name):
        section = Section(id=str(uuid.uuid4()), academic_level_id=academic_level_id, name=name, created_at=datetime.now(timezone.utc))
        self._sections[section.id] = section
        return section

    async def get_section(self, section_id):
        return self._sections.get(section_id)

    async def get_education_system(self, education_system_id):
        return self._education_systems.get(education_system_id)

    async def get_country(self, country_id):
        return self._countries.get(country_id)

    async def list_subjects(self, academic_level_id, *, section_id=None):
        subjects = [s for s in self._subjects.values() if s.academic_level_id == academic_level_id]
        if section_id is not None:
            subjects = [s for s in subjects if s.section_id == section_id]
        return subjects

    async def get_subject(self, curriculum_subject_id):
        return self._subjects.get(curriculum_subject_id)

    async def list_subjects_by_ids(self, curriculum_subject_ids):
        ids = set(curriculum_subject_ids)
        return [s for s in self._subjects.values() if s.id in ids]

    async def create_subject(self, *, academic_level_id, section_id, name):
        subject = CurriculumSubject(
            id=str(uuid.uuid4()), academic_level_id=academic_level_id, section_id=section_id, name=name,
            created_at=datetime.now(timezone.utc),
        )
        self._subjects[subject.id] = subject
        return subject

    async def list_chapters(self, curriculum_subject_id):
        return [c for c in self._chapters.values() if c.curriculum_subject_id == curriculum_subject_id]

    async def create_chapter(self, *, curriculum_subject_id, name, order_index):
        chapter = Chapter(
            id=str(uuid.uuid4()), curriculum_subject_id=curriculum_subject_id, name=name, order_index=order_index,
            created_at=datetime.now(timezone.utc),
        )
        self._chapters[chapter.id] = chapter
        return chapter

    async def list_lessons(self, chapter_id):
        return [lesson for lesson in self._lessons.values() if lesson.chapter_id == chapter_id]

    async def create_lesson(self, *, chapter_id, name, order_index):
        lesson = Lesson(
            id=str(uuid.uuid4()), chapter_id=chapter_id, name=name, order_index=order_index,
            created_at=datetime.now(timezone.utc),
        )
        self._lessons[lesson.id] = lesson
        return lesson


class FakeChunkRepository(ChunkRepository):
    def __init__(self):
        self._by_id: dict[str, Chunk] = {}

    async def bulk_create(self, *, document_id, subject_id, drafts):
        ids_by_index: dict[int, str] = {}
        results: list[Chunk] = []

        for index, draft in enumerate(drafts):
            parent_id = None
            if draft.chunk_type != "parent" and draft.parent_index is not None:
                parent_id = ids_by_index.get(draft.parent_index)

            chunk = Chunk(
                id=str(uuid.uuid4()),
                document_id=document_id,
                subject_id=subject_id,
                content=draft.content,
                chunk_type=draft.chunk_type,
                parent_chunk_id=parent_id,
                page=draft.page,
                section_title=draft.section_title,
                chapter=draft.chapter,
                token_count=draft.token_count,
            )
            self._by_id[chunk.id] = chunk
            ids_by_index[index] = chunk.id
            results.append(chunk)

        return results

    async def list_by_document(self, document_id):
        return [c for c in self._by_id.values() if c.document_id == document_id]

    async def get_by_ids(self, chunk_ids):
        return [self._by_id[cid] for cid in chunk_ids if cid in self._by_id]


class FakeConceptRepository(ConceptRepository):
    """list_by_document needs both a concept_chunk_repo (for the concept<->chunk
    links) and a chunk_repo (to filter those links down to one document's
    chunks) — pass both in for tests that exercise it (e.g. the summary
    engine's key_concepts grounding); tests that don't care about that method
    can construct this with no arguments as before."""

    def __init__(self, concept_chunk_repo=None, chunk_repo=None):
        self._by_id: dict[str, Concept] = {}
        self.prerequisites: list[tuple[str, str]] = []
        self._concept_chunk_repo = concept_chunk_repo
        self._chunk_repo = chunk_repo

    async def list_by_subject(self, subject_id):
        return [c for c in self._by_id.values() if c.subject_id == subject_id]

    async def get_by_subject_and_name(self, subject_id, name):
        return next((c for c in self._by_id.values() if c.subject_id == subject_id and c.name == name), None)

    async def create(self, *, subject_id, name, description):
        concept = Concept(id=str(uuid.uuid4()), subject_id=subject_id, name=name, description=description, parent_concept_id=None)
        self._by_id[concept.id] = concept
        return concept

    async def add_prerequisite(self, *, concept_id, prerequisite_id):
        if concept_id != prerequisite_id:
            self.prerequisites.append((concept_id, prerequisite_id))

    async def list_by_document(self, document_id):
        if self._concept_chunk_repo is None or self._chunk_repo is None:
            return []
        chunk_ids_in_doc = {c.id for c in self._chunk_repo._by_id.values() if c.document_id == document_id}
        concept_ids = {
            concept_id for concept_id, chunk_id, _relevance in self._concept_chunk_repo.links
            if chunk_id in chunk_ids_in_doc
        }
        return [self._by_id[cid] for cid in concept_ids if cid in self._by_id]


class FakeConceptChunkRepository(ConceptChunkRepository):
    def __init__(self):
        self.links: list[tuple[str, str, float]] = []

    async def link(self, *, concept_id, chunk_id, relevance):
        self.links.append((concept_id, chunk_id, relevance))


def _cosine_distance(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return 1.0 - dot / (norm_a * norm_b)


class FakeEmbeddingRepository(EmbeddingRepository):
    """search() mirrors the real repository's join against chunks to filter
    by subject_id — takes an optional chunk_repo reference to resolve that,
    since (like the real embeddings table) this fake doesn't otherwise know
    which subject a chunk_id belongs to."""

    def __init__(self, chunk_repo: "FakeChunkRepository | None" = None):
        self.stored: dict[str, tuple[list[float], str]] = {}
        self._chunk_repo = chunk_repo

    async def bulk_create(self, *, chunk_ids, vectors, model_name):
        for chunk_id, vector in zip(chunk_ids, vectors):
            self.stored[chunk_id] = (vector, model_name)

    async def search(self, *, subject_id, query_vector, top_k, model_name, document_id=None):
        candidates: list[tuple[str, float]] = []
        for chunk_id, (vector, stored_model_name) in self.stored.items():
            if stored_model_name != model_name:
                continue
            if self._chunk_repo is not None:
                chunk = self._chunk_repo._by_id.get(chunk_id)
                if chunk is None or chunk.subject_id != subject_id:
                    continue
                if document_id is not None and chunk.document_id != document_id:
                    continue
            candidates.append((chunk_id, _cosine_distance(query_vector, vector)))
        candidates.sort(key=lambda pair: pair[1])
        return candidates[:top_k]


class FakeStorage(StoragePort):
    def __init__(self):
        self.files: dict[str, bytes] = {}

    async def save(self, *, subject_id, document_id, filename, content):
        path = f"{subject_id}/{document_id}/{filename}"
        self.files[path] = content
        return path

    async def read(self, storage_path):
        if storage_path not in self.files:
            raise FileNotFoundError(storage_path)
        return self.files[storage_path]

    async def delete(self, storage_path):
        self.files.pop(storage_path, None)


class FakeLLMProvider(LLMProvider):
    """Returns canned responses in order (or a single fixed response) and
    records every call so tests can assert on the prompt built for the LLM."""

    def __init__(
        self,
        response: str | None = None,
        responses: list[str] | None = None,
        vision_response: str = "A described image.",
    ):
        self._response = response
        self._responses = list(responses) if responses is not None else None
        self._vision_response = vision_response
        self.calls: list[dict] = []
        self.vision_calls: list[dict] = []

    async def complete(self, *, prompt, system=None, temperature=0.2, max_output_tokens=2048, response_json=False):
        self.calls.append({"prompt": prompt, "system": system, "response_json": response_json})
        if self._responses is not None:
            return self._responses.pop(0) if self._responses else "{}"
        return self._response if self._response is not None else "{}"

    async def complete_vision(self, *, image_bytes, mime_type, prompt, max_output_tokens=2048):
        self.vision_calls.append({"image_bytes": image_bytes, "mime_type": mime_type, "prompt": prompt})
        return self._vision_response


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimension: int = 8):
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return "fake-embedder"

    @property
    def dimension(self) -> int:
        return self._dimension

    def _vector_for(self, text: str) -> list[float]:
        # Deterministic, cheap, and non-degenerate — good enough to prove the
        # embedding pipeline plumbing works without a real model.
        seed = sum(text.encode("utf-8")) or 1
        return [((seed * (i + 1)) % 97) / 97 for i in range(self._dimension)]

    async def embed_documents(self, texts):
        return [self._vector_for(t) for t in texts]

    async def embed_query(self, text):
        return self._vector_for(text)


class FakeConversationRepository(ConversationRepository):
    def __init__(self):
        self._by_id: dict[str, Conversation] = {}

    async def create(self, *, user_id, subject_id, title):
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            subject_id=subject_id,
            title=title,
            created_at=datetime.now(timezone.utc),
        )
        self._by_id[conversation.id] = conversation
        return conversation

    async def get_by_id(self, conversation_id):
        return self._by_id.get(conversation_id)

    async def list_by_subject(self, user_id, subject_id):
        conversations = [
            c for c in self._by_id.values() if c.user_id == user_id and c.subject_id == subject_id
        ]
        return sorted(conversations, key=lambda c: c.created_at, reverse=True)


class FakeMessageRepository(MessageRepository):
    def __init__(self):
        self._by_id: dict[str, Message] = {}
        self._order: list[str] = []

    async def create(self, *, conversation_id, role, content, citations):
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=list(citations),
            created_at=datetime.now(timezone.utc),
        )
        self._by_id[message.id] = message
        self._order.append(message.id)
        return message

    async def list_by_conversation(self, conversation_id):
        return [
            self._by_id[mid]
            for mid in self._order
            if self._by_id[mid].conversation_id == conversation_id
        ]


class FakeSummaryRepository(SummaryRepository):
    def __init__(self):
        # Keyed by (document_id, summary_type) — mirrors the real table's
        # unique constraint, so upsert-vs-insert semantics match for free.
        self._by_key: dict[tuple[str, str], Summary] = {}

    async def upsert(self, *, document_id, subject_id, summary_type, content):
        key = (document_id, summary_type)
        existing = self._by_key.get(key)
        now = datetime.now(timezone.utc)
        summary = Summary(
            id=existing.id if existing else str(uuid.uuid4()),
            document_id=document_id,
            subject_id=subject_id,
            summary_type=summary_type,
            content=content,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._by_key[key] = summary
        return summary

    async def get_by_document_and_type(self, document_id, summary_type):
        return self._by_key.get((document_id, summary_type))

    async def list_by_document(self, document_id):
        return [s for s in self._by_key.values() if s.document_id == document_id]


class FakeFlashcardRepository(FlashcardRepository):
    """list_by_user needs to know which subjects belong to which user — takes
    an optional subject_repo reference to resolve that, mirroring the pattern
    used by FakeEmbeddingRepository/FakeConceptRepository for the same reason
    (this fake doesn't otherwise know the subject->user mapping)."""

    def __init__(self, subject_repo=None):
        self._by_id: dict[str, Flashcard] = {}
        self._subject_repo = subject_repo

    async def bulk_create(self, *, subject_id, drafts):
        cards = []
        for draft in drafts:
            card = Flashcard(
                id=str(uuid.uuid4()),
                subject_id=subject_id,
                concept_id=draft.concept_id,
                question=draft.question,
                answer=draft.answer,
                difficulty=draft.difficulty,
                tags=list(draft.tags),
                source=draft.source,
                created_at=datetime.now(timezone.utc),
            )
            self._by_id[card.id] = card
            cards.append(card)
        return cards

    async def get_by_id(self, flashcard_id):
        return self._by_id.get(flashcard_id)

    async def list_by_subject(self, subject_id):
        return [c for c in self._by_id.values() if c.subject_id == subject_id]

    async def list_by_user(self, user_id):
        if self._subject_repo is None:
            return []
        subject_ids = {s.id for s in self._subject_repo._by_id.values() if s.user_id == user_id}
        return [c for c in self._by_id.values() if c.subject_id in subject_ids]


class FakeFlashcardReviewRepository(FlashcardReviewRepository):
    def __init__(self):
        # Keyed by (flashcard_id, user_id) — mirrors the real table's unique
        # constraint.
        self._by_key: dict[tuple[str, str], FlashcardReview] = {}

    async def upsert(
        self, *, flashcard_id, user_id, ease_factor, interval_days, repetitions, last_grade,
        last_reviewed_at, next_review_date,
    ):
        key = (flashcard_id, user_id)
        existing = self._by_key.get(key)
        review = FlashcardReview(
            id=existing.id if existing else str(uuid.uuid4()),
            flashcard_id=flashcard_id,
            user_id=user_id,
            ease_factor=ease_factor,
            interval_days=interval_days,
            repetitions=repetitions,
            last_grade=last_grade,
            last_reviewed_at=last_reviewed_at,
            next_review_date=next_review_date,
        )
        self._by_key[key] = review
        return review

    async def get_by_flashcard_and_user(self, flashcard_id, user_id):
        return self._by_key.get((flashcard_id, user_id))

    async def list_by_user(self, user_id):
        return [r for r in self._by_key.values() if r.user_id == user_id]


class FakeQuizRepository(QuizRepository):
    def __init__(self):
        self._by_id: dict[str, Quiz] = {}
        self._questions_by_id: dict[str, QuizQuestion] = {}

    async def create(self, *, subject_id, user_id, title, kind, difficulty, topics, duration_minutes, style):
        quiz = Quiz(
            id=str(uuid.uuid4()),
            subject_id=subject_id,
            user_id=user_id,
            title=title,
            kind=kind,
            difficulty=difficulty,
            topics=list(topics),
            duration_minutes=duration_minutes,
            style=style,
            created_at=datetime.now(timezone.utc),
        )
        self._by_id[quiz.id] = quiz
        return quiz

    async def bulk_create_questions(self, *, quiz_id, drafts):
        questions = []
        for draft in drafts:
            question = QuizQuestion(
                id=str(uuid.uuid4()),
                quiz_id=quiz_id,
                concept_id=draft.concept_id,
                type=draft.type,
                question=draft.question,
                options=list(draft.options) if draft.options is not None else None,
                correct_answer=draft.correct_answer,
                explanation=draft.explanation,
                points=draft.points,
                difficulty=draft.difficulty,
            )
            self._questions_by_id[question.id] = question
            questions.append(question)
        return questions

    async def get_by_id(self, quiz_id):
        return self._by_id.get(quiz_id)

    async def list_by_subject(self, subject_id):
        return [q for q in self._by_id.values() if q.subject_id == subject_id]

    async def list_questions(self, quiz_id):
        return [q for q in self._questions_by_id.values() if q.quiz_id == quiz_id]

    async def get_question_by_id(self, question_id):
        return self._questions_by_id.get(question_id)


class FakeQuizAttemptRepository(QuizAttemptRepository):
    def __init__(self):
        self._by_id: dict[str, QuizAttempt] = {}

    async def create(self, *, quiz_id, user_id):
        attempt = QuizAttempt(
            id=str(uuid.uuid4()),
            quiz_id=quiz_id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            score=None,
        )
        self._by_id[attempt.id] = attempt
        return attempt

    async def get_by_id(self, attempt_id):
        return self._by_id.get(attempt_id)

    async def list_by_quiz(self, quiz_id):
        return [a for a in self._by_id.values() if a.quiz_id == quiz_id]

    async def complete(self, attempt_id, *, completed_at, score):
        updated = replace(self._by_id[attempt_id], completed_at=completed_at, score=score)
        self._by_id[attempt_id] = updated
        return updated

    async def list_by_user(self, user_id):
        return [a for a in self._by_id.values() if a.user_id == user_id]


class FakeStudentAnswerRepository(StudentAnswerRepository):
    def __init__(self):
        # Keyed by (quiz_attempt_id, quiz_question_id) — mirrors the real
        # table's unique constraint.
        self._by_key: dict[tuple[str, str], StudentAnswer] = {}

    async def upsert(self, *, quiz_attempt_id, quiz_question_id, answer, is_correct, time_spent_seconds, submitted_at):
        key = (quiz_attempt_id, quiz_question_id)
        existing = self._by_key.get(key)
        record = StudentAnswer(
            id=existing.id if existing else str(uuid.uuid4()),
            quiz_attempt_id=quiz_attempt_id,
            quiz_question_id=quiz_question_id,
            answer=answer,
            is_correct=is_correct,
            time_spent_seconds=time_spent_seconds,
            submitted_at=submitted_at,
        )
        self._by_key[key] = record
        return record

    async def list_by_attempt(self, quiz_attempt_id):
        return [a for a in self._by_key.values() if a.quiz_attempt_id == quiz_attempt_id]


class FakeProgressRepository(ProgressRepository):
    def __init__(self):
        # Keyed by (user_id, concept_id) — mirrors the real table's unique constraint.
        self._by_key: dict[tuple[str, str], Progress] = {}

    async def upsert(self, *, user_id, concept_id, mastery_score, trend):
        key = (user_id, concept_id)
        existing = self._by_key.get(key)
        record = Progress(
            id=existing.id if existing else str(uuid.uuid4()),
            user_id=user_id,
            concept_id=concept_id,
            mastery_score=mastery_score,
            trend=trend,
            last_updated=datetime.now(timezone.utc),
        )
        self._by_key[key] = record
        return record

    async def get_by_user_and_concept(self, user_id, concept_id):
        return self._by_key.get((user_id, concept_id))

    async def list_by_user(self, user_id):
        return [p for p in self._by_key.values() if p.user_id == user_id]


class FakeWeakConceptRepository(WeakConceptRepository):
    def __init__(self):
        self._by_id: dict[str, WeakConcept] = {}

    async def create(self, *, user_id, concept_id, reason, confidence):
        record = WeakConcept(
            id=str(uuid.uuid4()),
            user_id=user_id,
            concept_id=concept_id,
            reason=reason,
            confidence=confidence,
            status="active",
            detected_at=datetime.now(timezone.utc),
        )
        self._by_id[record.id] = record
        return record

    async def update_active(self, weak_concept_id, *, reason, confidence):
        updated = replace(self._by_id[weak_concept_id], reason=reason, confidence=confidence)
        self._by_id[weak_concept_id] = updated
        return updated

    async def resolve(self, weak_concept_id):
        updated = replace(self._by_id[weak_concept_id], status="resolved")
        self._by_id[weak_concept_id] = updated
        return updated

    async def get_active_by_user_and_concept(self, user_id, concept_id):
        return next(
            (
                w for w in self._by_id.values()
                if w.user_id == user_id and w.concept_id == concept_id and w.status == "active"
            ),
            None,
        )

    async def list_active_by_user(self, user_id):
        return [w for w in self._by_id.values() if w.user_id == user_id and w.status == "active"]


class FakeStudyPlanRepository(StudyPlanRepository):
    def __init__(self):
        self._plans_by_id: dict[str, StudyPlan] = {}
        self._items_by_id: dict[str, StudyPlanItem] = {}

    async def create(self, *, user_id, name, exam_date, daily_minutes_available):
        plan = StudyPlan(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            exam_date=exam_date,
            daily_minutes_available=daily_minutes_available,
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        self._plans_by_id[plan.id] = plan
        return plan

    async def bulk_create_items(self, *, study_plan_id, drafts):
        items = []
        for draft in drafts:
            item = StudyPlanItem(
                id=str(uuid.uuid4()),
                study_plan_id=study_plan_id,
                subject_id=draft.subject_id,
                concept_id=draft.concept_id,
                scheduled_date=draft.scheduled_date,
                activity_type=draft.activity_type,
                duration_minutes=draft.duration_minutes,
                status="pending",
            )
            self._items_by_id[item.id] = item
            items.append(item)
        return items

    async def get_by_id(self, study_plan_id):
        return self._plans_by_id.get(study_plan_id)

    async def list_items(self, study_plan_id):
        return [i for i in self._items_by_id.values() if i.study_plan_id == study_plan_id]

    async def get_item_by_id(self, item_id):
        return self._items_by_id.get(item_id)

    async def update_item_status(self, item_id, *, status):
        updated = replace(self._items_by_id[item_id], status=status)
        self._items_by_id[item_id] = updated
        return updated

    async def delete_all_for_user(self, user_id):
        removed_plan_ids = {p.id for p in self._plans_by_id.values() if p.user_id == user_id}
        for plan_id in removed_plan_ids:
            del self._plans_by_id[plan_id]
        for item_id in [i.id for i in self._items_by_id.values() if i.study_plan_id in removed_plan_ids]:
            del self._items_by_id[item_id]
