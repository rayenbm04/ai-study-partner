from dataclasses import dataclass

from app.core.exceptions import CurriculumPackNotFoundError
from app.domain.entities.subject import Subject
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.domain.repositories.subject_repository import SubjectRepository


@dataclass(frozen=True, slots=True)
class PackApplyResult:
    created: list[Subject]
    skipped_duplicate_names: list[str]


@dataclass(frozen=True, slots=True)
class AppliedPack:
    academic_level_id: str
    section_id: str | None
    country_name: str
    education_system_name: str
    academic_level_name: str
    section_name: str | None
    subjects: list[Subject]


class SubjectPackService:
    """A 'subject pack' isn't a stored entity — it's a chosen
    (academic_level_id, section_id) node in the read-only curriculum
    catalog. Applying/removing a pack bulk-creates or bulk-archives the
    user's own Subject rows, linked via the curriculum_subject_id FK that
    already exists on Subject. 'Applied packs' are derived by grouping the
    user's curriculum-linked subjects by that node, so there's nothing to
    keep in sync and a partially-removed pack shows up as partial rather
    than lying about still being fully applied."""

    def __init__(self, subject_repo: SubjectRepository, curriculum_repo: CurriculumRepository):
        self._subjects = subject_repo
        self._curriculum = curriculum_repo

    async def apply(self, user_id: str, *, academic_level_id: str, section_id: str | None = None) -> PackApplyResult:
        catalog_subjects = await self._curriculum.list_subjects(academic_level_id, section_id=section_id)
        if not catalog_subjects:
            raise CurriculumPackNotFoundError(academic_level_id, section_id)

        created: list[Subject] = []
        skipped: list[str] = []
        for cs in catalog_subjects:
            if await self._subjects.get_by_user_and_name(user_id, cs.name):
                skipped.append(cs.name)
                continue
            created.append(
                await self._subjects.create(
                    user_id=user_id,
                    name=cs.name,
                    description=None,
                    color=None,
                    icon=None,
                    curriculum_subject_id=cs.id,
                )
            )
        return PackApplyResult(created=created, skipped_duplicate_names=skipped)

    async def remove(self, user_id: str, *, academic_level_id: str, section_id: str | None = None) -> int:
        catalog_subjects = await self._curriculum.list_subjects(academic_level_id, section_id=section_id)
        if not catalog_subjects:
            raise CurriculumPackNotFoundError(academic_level_id, section_id)
        catalog_ids = {cs.id for cs in catalog_subjects}

        user_subjects = await self._subjects.list_by_user(user_id)
        to_remove = [s for s in user_subjects if s.curriculum_subject_id in catalog_ids]
        for subject in to_remove:
            await self._subjects.archive(subject.id)
        return len(to_remove)

    async def list_applied(self, user_id: str) -> list[AppliedPack]:
        user_subjects = await self._subjects.list_by_user(user_id)
        linked = [s for s in user_subjects if s.curriculum_subject_id]
        if not linked:
            return []

        catalog_subjects = await self._curriculum.list_subjects_by_ids(
            [s.curriculum_subject_id for s in linked if s.curriculum_subject_id]
        )
        catalog_by_id = {cs.id: cs for cs in catalog_subjects}

        groups: dict[tuple[str, str | None], list[Subject]] = {}
        for subject in linked:
            cs = catalog_by_id.get(subject.curriculum_subject_id)
            if cs is None:
                continue  # catalog subject was deleted out from under the link
            groups.setdefault((cs.academic_level_id, cs.section_id), []).append(subject)

        packs: list[AppliedPack] = []
        for (academic_level_id, section_id), subjects in groups.items():
            academic_level = await self._curriculum.get_academic_level(academic_level_id)
            if academic_level is None:
                continue
            education_system = await self._curriculum.get_education_system(academic_level.education_system_id)
            country = await self._curriculum.get_country(education_system.country_id) if education_system else None
            section = await self._curriculum.get_section(section_id) if section_id else None

            packs.append(
                AppliedPack(
                    academic_level_id=academic_level_id,
                    section_id=section_id,
                    country_name=country.name if country else "",
                    education_system_name=education_system.name if education_system else "",
                    academic_level_name=academic_level.name,
                    section_name=section.name if section else None,
                    subjects=subjects,
                )
            )
        return packs
