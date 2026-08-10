import pytest

from app.services.account_service import AccountService
from tests.unit.fakes import (
    FakeCurriculumRepository,
    FakeDocumentRepository,
    FakeStorage,
    FakeStudyPlanRepository,
    FakeSubjectRepository,
    FakeUserRepository,
)


async def _build():
    subject_repo = FakeSubjectRepository()
    document_repo = FakeDocumentRepository()
    study_plan_repo = FakeStudyPlanRepository()
    storage = FakeStorage()
    user_repo = FakeUserRepository()
    curriculum_repo = FakeCurriculumRepository()
    service = AccountService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        study_plan_repo=study_plan_repo,
        storage=storage,
        user_repo=user_repo,
        curriculum_repo=curriculum_repo,
    )
    return service, subject_repo, document_repo, study_plan_repo, storage


async def test_reset_deletes_all_subjects_documents_and_study_plans_for_user():
    service, subject_repo, document_repo, study_plan_repo, storage = await _build()
    subject = await subject_repo.create(user_id="user-1", name="Physics", description=None, color=None, icon=None)
    await storage.save(subject_id=subject.id, document_id="doc-1", filename="notes.pdf", content=b"hello")
    document = await document_repo.create(
        document_id="doc-1", subject_id=subject.id, original_filename="notes.pdf",
        storage_path=f"{subject.id}/doc-1/notes.pdf", file_type=".pdf",
    )
    plan = await study_plan_repo.create(user_id="user-1", name="Exam prep", exam_date=None, daily_minutes_available=30)

    await service.reset("user-1")

    assert await subject_repo.list_by_user("user-1", include_archived=True) == []
    assert await study_plan_repo.get_by_id(plan.id) is None
    with pytest.raises(FileNotFoundError):
        await storage.read(document.storage_path)


async def test_reset_does_not_touch_other_users_data():
    service, subject_repo, document_repo, study_plan_repo, storage = await _build()
    await subject_repo.create(user_id="user-1", name="Physics", description=None, color=None, icon=None)
    other_subject = await subject_repo.create(user_id="user-2", name="Chemistry", description=None, color=None, icon=None)
    other_plan = await study_plan_repo.create(
        user_id="user-2", name="Other plan", exam_date=None, daily_minutes_available=15
    )

    await service.reset("user-1")

    remaining = await subject_repo.list_by_user("user-2", include_archived=True)
    assert [s.id for s in remaining] == [other_subject.id]
    assert await study_plan_repo.get_by_id(other_plan.id) is not None


async def test_reset_deletes_archived_subjects_too():
    service, subject_repo, document_repo, study_plan_repo, storage = await _build()
    subject = await subject_repo.create(user_id="user-1", name="Physics", description=None, color=None, icon=None)
    await subject_repo.archive(subject.id)

    await service.reset("user-1")

    assert await subject_repo.list_by_user("user-1", include_archived=True) == []
