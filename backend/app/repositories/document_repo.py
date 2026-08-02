from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError
from app.domain.entities.document import Document
from app.domain.repositories.document_repository import DocumentRepository
from app.infrastructure.db.models.document import DocumentModel


def _to_entity(model: DocumentModel) -> Document:
    return Document(
        id=model.id,
        subject_id=model.subject_id,
        original_filename=model.original_filename,
        storage_path=model.storage_path,
        file_type=model.file_type,
        status=model.status,
        page_count=model.page_count,
        error_message=model.error_message,
        uploaded_at=model.uploaded_at,
    )


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self, *, document_id: str, subject_id: str, original_filename: str, storage_path: str, file_type: str
    ) -> Document:
        model = DocumentModel(
            id=document_id,
            subject_id=subject_id,
            original_filename=original_filename,
            storage_path=storage_path,
            file_type=file_type,
            status="pending",
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, document_id: str) -> Document | None:
        model = await self._session.get(DocumentModel, document_id)
        return _to_entity(model) if model else None

    async def list_by_subject(self, subject_id: str) -> list[Document]:
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.subject_id == subject_id)
            .order_by(DocumentModel.uploaded_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]

    async def _get_model_or_raise(self, document_id: str) -> DocumentModel:
        model = await self._session.get(DocumentModel, document_id)
        if model is None:
            raise DocumentNotFoundError(document_id)
        return model

    async def mark_processing(self, document_id: str) -> None:
        model = await self._get_model_or_raise(document_id)
        model.status = "processing"
        await self._session.flush()

    async def mark_ready(self, document_id: str, *, page_count: int) -> None:
        model = await self._get_model_or_raise(document_id)
        model.status = "ready"
        model.page_count = page_count
        model.error_message = None
        await self._session.flush()

    async def mark_failed(self, document_id: str, *, error_message: str) -> None:
        model = await self._get_model_or_raise(document_id)
        model.status = "failed"
        model.error_message = error_message
        await self._session.flush()

    async def delete(self, document_id: str) -> None:
        model = await self._get_model_or_raise(document_id)
        await self._session.delete(model)
        await self._session.flush()
