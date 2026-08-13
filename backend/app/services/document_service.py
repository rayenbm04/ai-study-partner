import hashlib
import uuid

from app.core.exceptions import DocumentNotFoundError, FileTooLargeError
from app.domain.entities.document import Document
from app.domain.repositories.document_repository import DocumentRepository
from app.infrastructure.storage.base import StoragePort
from app.services.knowledge_base.extractors.registry import extension_of, get_extractor
from app.services.subject_service import SubjectService
from app.services.usage_service import UsageService


class DocumentService:
    """Owns upload validation and storage/DB coordination for one document.
    Ingestion itself (extraction, chunking, embedding, concept tagging) is
    scheduled separately as a background task — this service only needs to
    get the file safely stored and the document row created before returning,
    so an upload response is fast regardless of file size."""

    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        subject_service: SubjectService,
        storage: StoragePort,
        max_upload_bytes: int,
        dedup_enabled: bool = True,
        usage_service: UsageService | None = None,
    ):
        self._documents = document_repo
        self._subjects = subject_service
        self._storage = storage
        self._max_upload_bytes = max_upload_bytes
        self._dedup_enabled = dedup_enabled
        self._usage = usage_service

    async def upload(self, *, user_id: str, subject_id: str, filename: str, content: bytes) -> Document:
        await self._subjects.get_owned(user_id, subject_id)
        get_extractor(filename)  # raises UnsupportedFileTypeError before anything touches storage
        if len(content) > self._max_upload_bytes:
            raise FileTooLargeError(self._max_upload_bytes // (1024 * 1024))

        content_hash = hashlib.sha256(content).hexdigest()
        if self._dedup_enabled:
            existing = await self._documents.get_by_subject_and_hash(subject_id, content_hash)
            if existing is not None:
                # Byte-identical file already uploaded (and not failed) for
                # this subject — return it instead of reprocessing (a second
                # ingestion of the same bytes would just burn embedding/LLM
                # quota for an identical index). Still fully user-isolated:
                # the hash lookup is scoped to this subject_id, itself
                # already ownership-checked above. Doesn't count against the
                # daily upload quota below — nothing new is being processed.
                return existing

        if self._usage is not None:
            await self._usage.check_document_limit(user_id)

        # Generated here (not by the DB) because storage.save() needs an id to
        # key the file by before the row that will reference it can exist.
        document_id = str(uuid.uuid4())
        storage_path = await self._storage.save(
            subject_id=subject_id, document_id=document_id, filename=filename, content=content
        )
        document = await self._documents.create(
            document_id=document_id,
            subject_id=subject_id,
            original_filename=filename,
            storage_path=storage_path,
            file_type=extension_of(filename),
            content_hash=content_hash,
        )
        if self._usage is not None:
            await self._usage.record(user_id=user_id, event_type="document_uploaded", document_id=document_id)
        return document

    async def list_for_subject(self, user_id: str, subject_id: str) -> list[Document]:
        await self._subjects.get_owned(user_id, subject_id)
        return await self._documents.list_by_subject(subject_id)

    async def get_owned(self, user_id: str, document_id: str) -> Document:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        await self._subjects.get_owned(user_id, document.subject_id)  # 404s if this user doesn't own the subject
        return document

    async def read_content(self, user_id: str, document_id: str) -> tuple[Document, bytes]:
        document = await self.get_owned(user_id, document_id)
        content = await self._storage.read(document.storage_path)
        return document, content

    async def delete(self, user_id: str, document_id: str) -> None:
        document = await self.get_owned(user_id, document_id)
        await self._storage.delete(document.storage_path)
        await self._documents.delete(document.id)
