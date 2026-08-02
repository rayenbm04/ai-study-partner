"""In-memory fakes for the repository interfaces, used by unit tests so
service logic is verified with no database, no event loop surprises, and no
test fixtures beyond plain Python dicts."""
import uuid
from dataclasses import replace
from datetime import datetime, timezone

from app.domain.entities.chunk import Chunk
from app.domain.entities.concept import Concept
from app.domain.entities.document import Document
from app.domain.entities.refresh_token import RefreshToken
from app.domain.entities.subject import Subject
from app.domain.entities.user import User
from app.domain.repositories.chunk_repository import ChunkRepository
from app.domain.repositories.concept_chunk_repository import ConceptChunkRepository
from app.domain.repositories.concept_repository import ConceptRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.embedding_repository import EmbeddingRepository
from app.domain.repositories.refresh_token_repository import RefreshTokenRepository
from app.domain.repositories.subject_repository import SubjectRepository
from app.domain.repositories.user_repository import UserRepository
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
        return next((s for s in self._by_id.values() if s.user_id == user_id and s.name == name), None)

    async def create(self, *, user_id, name, description, color, icon):
        subject = Subject(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            color=color,
            icon=icon,
            created_at=datetime.now(timezone.utc),
            archived_at=None,
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

    async def delete(self, document_id):
        self._by_id.pop(document_id, None)


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


class FakeConceptRepository(ConceptRepository):
    def __init__(self):
        self._by_id: dict[str, Concept] = {}
        self.prerequisites: list[tuple[str, str]] = []

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


class FakeConceptChunkRepository(ConceptChunkRepository):
    def __init__(self):
        self.links: list[tuple[str, str, float]] = []

    async def link(self, *, concept_id, chunk_id, relevance):
        self.links.append((concept_id, chunk_id, relevance))


class FakeEmbeddingRepository(EmbeddingRepository):
    def __init__(self):
        self.stored: dict[str, tuple[list[float], str]] = {}

    async def bulk_create(self, *, chunk_ids, vectors, model_name):
        for chunk_id, vector in zip(chunk_ids, vectors):
            self.stored[chunk_id] = (vector, model_name)


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
