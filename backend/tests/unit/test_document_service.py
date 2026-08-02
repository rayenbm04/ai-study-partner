import pytest

from app.core.exceptions import DocumentNotFoundError, FileTooLargeError, SubjectNotFoundError, UnsupportedFileTypeError
from app.services.document_service import DocumentService
from app.services.subject_service import SubjectService
from tests.unit.fakes import FakeDocumentRepository, FakeStorage, FakeSubjectRepository


async def _service(max_upload_bytes=1_000_000):
    subject_service = SubjectService(FakeSubjectRepository())
    document_repo = FakeDocumentRepository()
    storage = FakeStorage()
    service = DocumentService(
        document_repo=document_repo, subject_service=subject_service, storage=storage, max_upload_bytes=max_upload_bytes
    )
    return service, subject_service, document_repo, storage


async def test_upload_creates_document_and_saves_bytes():
    service, subject_service, document_repo, storage = await _service()
    subject = await subject_service.create("user-1", name="Physics")

    document = await service.upload(user_id="user-1", subject_id=subject.id, filename="notes.pdf", content=b"%PDF-fake")

    assert document.status == "pending"
    assert document.original_filename == "notes.pdf"
    assert document.file_type == ".pdf"
    stored = await storage.read(document.storage_path)
    assert stored == b"%PDF-fake"


async def test_upload_rejects_other_users_subject():
    service, subject_service, *_ = await _service()
    subject = await subject_service.create("user-1", name="Physics")

    with pytest.raises(SubjectNotFoundError):
        await service.upload(user_id="user-2", subject_id=subject.id, filename="notes.pdf", content=b"data")


async def test_upload_rejects_unsupported_file_type():
    service, subject_service, *_ = await _service()
    subject = await subject_service.create("user-1", name="Physics")

    with pytest.raises(UnsupportedFileTypeError):
        await service.upload(user_id="user-1", subject_id=subject.id, filename="photo.jpg", content=b"data")


async def test_upload_rejects_file_over_size_limit():
    service, subject_service, *_ = await _service(max_upload_bytes=10)
    subject = await subject_service.create("user-1", name="Physics")

    with pytest.raises(FileTooLargeError):
        await service.upload(user_id="user-1", subject_id=subject.id, filename="notes.txt", content=b"x" * 100)


async def test_get_owned_rejects_other_users_document():
    service, subject_service, *_ = await _service()
    subject = await subject_service.create("user-1", name="Physics")
    document = await service.upload(user_id="user-1", subject_id=subject.id, filename="notes.txt", content=b"data")

    with pytest.raises(SubjectNotFoundError):
        await service.get_owned("user-2", document.id)


async def test_get_owned_rejects_unknown_document():
    service, *_ = await _service()
    with pytest.raises(DocumentNotFoundError):
        await service.get_owned("user-1", "does-not-exist")


async def test_delete_removes_document_and_file():
    service, subject_service, document_repo, storage = await _service()
    subject = await subject_service.create("user-1", name="Physics")
    document = await service.upload(user_id="user-1", subject_id=subject.id, filename="notes.txt", content=b"data")

    await service.delete("user-1", document.id)

    assert await document_repo.get_by_id(document.id) is None
    with pytest.raises(FileNotFoundError):
        await storage.read(document.storage_path)


async def test_list_for_subject_requires_ownership():
    service, subject_service, *_ = await _service()
    subject = await subject_service.create("user-1", name="Physics")

    with pytest.raises(SubjectNotFoundError):
        await service.list_for_subject("user-2", subject.id)
