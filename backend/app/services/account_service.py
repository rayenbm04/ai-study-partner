"""Account-wide reset: wipes a user's content (subjects and everything that
cascades from them, plus study plans) while leaving the account/login itself
untouched. See docs/ARCHITECTURE.md-adjacent reasoning in the PR that added
this — nearly every content table cascades from subjects.user_id/subjects.id
except study_plans, which is keyed only by user_id.

Also owns setting a student's own "classe" (academic level + optional
section) on their profile — separate from subject-pack application
(SubjectPackService), which uses the same two ids to decide which curriculum
subjects to add but doesn't remember them as *the student's own* level.
"""
from app.core.exceptions import AcademicLevelNotFoundError, SectionDoesNotBelongToLevelError, SectionNotFoundError
from app.domain.entities.user import User
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.study_plan_repository import StudyPlanRepository
from app.domain.repositories.subject_repository import SubjectRepository
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.storage.base import StoragePort


class AccountService:
    def __init__(
        self,
        *,
        subject_repo: SubjectRepository,
        document_repo: DocumentRepository,
        study_plan_repo: StudyPlanRepository,
        storage: StoragePort,
        user_repo: UserRepository,
        curriculum_repo: CurriculumRepository,
    ):
        self._subjects = subject_repo
        self._documents = document_repo
        self._study_plans = study_plan_repo
        self._storage = storage
        self._users = user_repo
        self._curriculum = curriculum_repo

    async def reset(self, user_id: str) -> None:
        subjects = await self._subjects.list_by_user(user_id, include_archived=True)

        # Storage paths have to be collected before the DB delete — the
        # cascade removes the rows, not the files on disk (same reasoning as
        # DocumentService.delete for a single document).
        storage_paths: list[str] = []
        for subject in subjects:
            documents = await self._documents.list_by_subject(subject.id)
            storage_paths.extend(document.storage_path for document in documents)

        await self._subjects.delete_all_for_user(user_id)
        await self._study_plans.delete_all_for_user(user_id)

        for storage_path in storage_paths:
            await self._storage.delete(storage_path)

    async def set_classe(
        self, user_id: str, *, academic_level_id: str | None, section_id: str | None
    ) -> User:
        """Sets or clears the student's own academic level/section (both None
        clears it — a student who picked wrong should be able to redo it)."""
        if academic_level_id is not None:
            if await self._curriculum.get_academic_level(academic_level_id) is None:
                raise AcademicLevelNotFoundError(academic_level_id)
            if section_id is not None:
                section = await self._curriculum.get_section(section_id)
                if section is None:
                    raise SectionNotFoundError(section_id)
                if section.academic_level_id != academic_level_id:
                    raise SectionDoesNotBelongToLevelError(section_id, academic_level_id)
        elif section_id is not None:
            # A section without its level doesn't mean anything on its own.
            raise AcademicLevelNotFoundError(academic_level_id or "")
        return await self._users.set_classe(user_id, academic_level_id=academic_level_id, section_id=section_id)
