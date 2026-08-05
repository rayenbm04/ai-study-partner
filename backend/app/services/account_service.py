"""Account-wide reset: wipes a user's content (subjects and everything that
cascades from them, plus study plans) while leaving the account/login itself
untouched. See docs/ARCHITECTURE.md-adjacent reasoning in the PR that added
this — nearly every content table cascades from subjects.user_id/subjects.id
except study_plans, which is keyed only by user_id.
"""
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.study_plan_repository import StudyPlanRepository
from app.domain.repositories.subject_repository import SubjectRepository
from app.infrastructure.storage.base import StoragePort


class AccountService:
    def __init__(
        self,
        *,
        subject_repo: SubjectRepository,
        document_repo: DocumentRepository,
        study_plan_repo: StudyPlanRepository,
        storage: StoragePort,
    ):
        self._subjects = subject_repo
        self._documents = document_repo
        self._study_plans = study_plan_repo
        self._storage = storage

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
