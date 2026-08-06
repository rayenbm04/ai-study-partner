import pytest

from app.core.exceptions import CurriculumPackNotFoundError
from app.services.subject_pack_service import SubjectPackService
from tests.unit.fakes import FakeCurriculumRepository, FakeSubjectRepository


@pytest.fixture
def curriculum_repo():
    return FakeCurriculumRepository()


@pytest.fixture
def subject_repo():
    return FakeSubjectRepository()


@pytest.fixture
def pack_service(subject_repo, curriculum_repo):
    return SubjectPackService(subject_repo, curriculum_repo)


async def _seed_bac_math(curriculum_repo):
    country = await curriculum_repo.create_country(name="Tunisia", code="TN")
    system = await curriculum_repo.create_education_system(country_id=country.id, name="Tunisian National System")
    level = await curriculum_repo.create_academic_level(education_system_id=system.id, name="Bac", order_index=0)
    section = await curriculum_repo.create_section(academic_level_id=level.id, name="Math")
    math_subject = await curriculum_repo.create_subject(academic_level_id=level.id, section_id=section.id, name="Mathematiques")
    physics_subject = await curriculum_repo.create_subject(academic_level_id=level.id, section_id=section.id, name="Physique")
    return {
        "country": country, "system": system, "level": level, "section": section,
        "subjects": [math_subject, physics_subject],
    }


async def test_apply_creates_a_subject_per_catalog_entry(pack_service, curriculum_repo):
    seeded = await _seed_bac_math(curriculum_repo)

    result = await pack_service.apply("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)

    assert {s.name for s in result.created} == {"Mathematiques", "Physique"}
    assert result.skipped_duplicate_names == []
    assert all(s.curriculum_subject_id is not None for s in result.created)


async def test_apply_raises_for_unknown_node(pack_service):
    with pytest.raises(CurriculumPackNotFoundError):
        await pack_service.apply("user-1", academic_level_id="does-not-exist", section_id=None)


async def test_apply_skips_names_that_already_exist_for_user(pack_service, subject_repo, curriculum_repo):
    seeded = await _seed_bac_math(curriculum_repo)
    await subject_repo.create(user_id="user-1", name="Physique", description=None, color=None, icon=None)

    result = await pack_service.apply("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)

    assert {s.name for s in result.created} == {"Mathematiques"}
    assert result.skipped_duplicate_names == ["Physique"]


async def test_apply_is_idempotent_on_second_call(pack_service, curriculum_repo):
    seeded = await _seed_bac_math(curriculum_repo)
    await pack_service.apply("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)

    result = await pack_service.apply("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)

    assert result.created == []
    assert set(result.skipped_duplicate_names) == {"Mathematiques", "Physique"}


async def test_remove_archives_only_that_pack_subjects(pack_service, subject_repo, curriculum_repo):
    seeded = await _seed_bac_math(curriculum_repo)
    await pack_service.apply("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)
    manual_subject = await subject_repo.create(user_id="user-1", name="My own subject", description=None, color=None, icon=None)

    removed_count = await pack_service.remove("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)

    assert removed_count == 2
    remaining = await subject_repo.list_by_user("user-1")
    assert [s.id for s in remaining] == [manual_subject.id]


async def test_list_applied_groups_by_academic_level_and_section(pack_service, curriculum_repo):
    seeded = await _seed_bac_math(curriculum_repo)
    await pack_service.apply("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)

    packs = await pack_service.list_applied("user-1")

    assert len(packs) == 1
    pack = packs[0]
    assert pack.country_name == "Tunisia"
    assert pack.education_system_name == "Tunisian National System"
    assert pack.academic_level_name == "Bac"
    assert pack.section_name == "Math"
    assert len(pack.subjects) == 2


async def test_list_applied_reflects_partial_removal(pack_service, subject_repo, curriculum_repo):
    seeded = await _seed_bac_math(curriculum_repo)
    result = await pack_service.apply("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)
    await subject_repo.archive(result.created[0].id)

    packs = await pack_service.list_applied("user-1")

    assert len(packs) == 1
    assert len(packs[0].subjects) == 1


async def test_list_applied_empty_for_user_with_no_linked_subjects(pack_service):
    assert await pack_service.list_applied("user-1") == []


async def test_pack_can_be_reapplied_after_removal(pack_service, curriculum_repo):
    seeded = await _seed_bac_math(curriculum_repo)
    await pack_service.apply("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)
    await pack_service.remove("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)

    result = await pack_service.apply("user-1", academic_level_id=seeded["level"].id, section_id=seeded["section"].id)

    assert {s.name for s in result.created} == {"Mathematiques", "Physique"}
    assert result.skipped_duplicate_names == []
