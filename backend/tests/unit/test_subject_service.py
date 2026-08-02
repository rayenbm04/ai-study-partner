import pytest

from app.core.exceptions import DuplicateSubjectError, SubjectNotFoundError
from app.services.subject_service import SubjectService
from tests.unit.fakes import FakeSubjectRepository


@pytest.fixture
def subject_service():
    return SubjectService(FakeSubjectRepository())


async def test_create_and_list_for_user(subject_service):
    subject = await subject_service.create("user-1", name="Mathematics")
    subjects = await subject_service.list_for_user("user-1")
    assert subjects == [subject]


async def test_create_rejects_duplicate_name_for_same_user(subject_service):
    await subject_service.create("user-1", name="Mathematics")
    with pytest.raises(DuplicateSubjectError):
        await subject_service.create("user-1", name="Mathematics")


async def test_duplicate_name_allowed_across_different_users(subject_service):
    await subject_service.create("user-1", name="Mathematics")
    subject = await subject_service.create("user-2", name="Mathematics")
    assert subject.user_id == "user-2"


async def test_get_owned_rejects_other_users_subject(subject_service):
    subject = await subject_service.create("user-1", name="Physics")
    with pytest.raises(SubjectNotFoundError):
        await subject_service.get_owned("user-2", subject.id)


async def test_get_owned_rejects_unknown_id(subject_service):
    with pytest.raises(SubjectNotFoundError):
        await subject_service.get_owned("user-1", "does-not-exist")


async def test_update_changes_fields(subject_service):
    subject = await subject_service.create("user-1", name="Physics")
    updated = await subject_service.update("user-1", subject.id, description="Mechanics & thermo")
    assert updated.description == "Mechanics & thermo"
    assert updated.name == "Physics"


async def test_archive_removes_from_default_listing(subject_service):
    subject = await subject_service.create("user-1", name="Physics")
    await subject_service.archive("user-1", subject.id)
    assert await subject_service.list_for_user("user-1") == []
