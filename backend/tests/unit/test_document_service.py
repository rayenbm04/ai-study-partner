import pytest

from app.core.exceptions import (
    DocumentNotFoundError,
    FileTooLargeError,
    SubjectNotFoundError,
    UnsupportedFileTypeError,
    UsageLimitExceededError,
)
from app.services.document_service import DocumentService
from app.services.subject_service import SubjectService
from app.services.usage_service import UsageService
from tests.unit.fakes import FakeDocumentRepository, FakeStorage, FakeSubjectRepository, FakeUsageEventRepository


async def _service(max_upload_bytes=1_000_000, dedup_enabled=True, usage_service=None):
    subject_service = SubjectService(FakeSubjectRepository())
    document_repo = FakeDocumentRepository()
    storage = FakeStorage()
    service = DocumentService(
        document_repo=document_repo, subject_service=subject_service, storage=storage,
        max_upload_bytes=max_upload_bytes, dedup_enabled=dedup_enabled, usage_service=usage_service,
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
        await service.upload(user_id="user-1", subject_id=subject.id, filename="clip.mp4", content=b"data")


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


async def test_upload_returns_existing_document_for_duplicate_content():
    service, subject_service, document_repo, _storage = await _service()
    subject = await subject_service.create("user-1", name="Physics")
    first = await service.upload(user_id="user-1", subject_id=subject.id, filename="notes.txt", content=b"same bytes")

    second = await service.upload(user_id="user-1", subject_id=subject.id, filename="notes-copy.txt", content=b"same bytes")

    assert second.id == first.id
    assert len(await document_repo.list_by_subject(subject.id)) == 1


async def test_upload_does_not_dedupe_across_different_subjects():
    service, subject_service, document_repo, _storage = await _service()
    physics = await subject_service.create("user-1", name="Physics")
    chemistry = await subject_service.create("user-1", name="Chemistry")
    await service.upload(user_id="user-1", subject_id=physics.id, filename="notes.txt", content=b"same bytes")

    second = await service.upload(user_id="user-1", subject_id=chemistry.id, filename="notes.txt", content=b"same bytes")

    assert second.subject_id == chemistry.id
    assert len(await document_repo.list_by_subject(chemistry.id)) == 1


async def test_upload_reprocesses_duplicate_content_when_dedup_disabled():
    service, subject_service, document_repo, _storage = await _service(dedup_enabled=False)
    subject = await subject_service.create("user-1", name="Physics")
    first = await service.upload(user_id="user-1", subject_id=subject.id, filename="notes.txt", content=b"same bytes")

    second = await service.upload(user_id="user-1", subject_id=subject.id, filename="notes.txt", content=b"same bytes")

    assert second.id != first.id
    assert len(await document_repo.list_by_subject(subject.id)) == 2


async def test_upload_enforces_daily_document_limit_when_usage_limits_enabled():
    usage_repo = FakeUsageEventRepository()
    usage = UsageService(usage_repo=usage_repo, limits_enabled=True, daily_ai_requests=100, daily_documents=1)
    service, subject_service, *_ = await _service(usage_service=usage)
    subject = await subject_service.create("user-1", name="Physics")
    await service.upload(user_id="user-1", subject_id=subject.id, filename="a.txt", content=b"aaa")

    with pytest.raises(UsageLimitExceededError):
        await service.upload(user_id="user-1", subject_id=subject.id, filename="b.txt", content=b"bbb")


async def test_upload_does_not_enforce_document_limit_by_default():
    usage_repo = FakeUsageEventRepository()
    usage = UsageService(usage_repo=usage_repo, limits_enabled=False, daily_ai_requests=100, daily_documents=1)
    service, subject_service, document_repo, _storage = await _service(usage_service=usage)
    subject = await subject_service.create("user-1", name="Physics")
    await service.upload(user_id="user-1", subject_id=subject.id, filename="a.txt", content=b"aaa")

    # Second upload succeeds even though daily_documents=1 — limits_enabled=False.
    await service.upload(user_id="user-1", subject_id=subject.id, filename="b.txt", content=b"bbb")

    assert len(await document_repo.list_by_subject(subject.id)) == 2
    assert len(usage_repo.events) == 2  # still recorded for observability, just not enforced
