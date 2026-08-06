from pydantic import BaseModel

from app.api.v1.schemas.subject import SubjectResponse
from app.services.subject_pack_service import AppliedPack, PackApplyResult


class SubjectPackRequest(BaseModel):
    academic_level_id: str
    section_id: str | None = None


class SubjectPackApplyResponse(BaseModel):
    created: list[SubjectResponse]
    skipped_duplicate_names: list[str]

    @classmethod
    def from_result(cls, result: PackApplyResult) -> "SubjectPackApplyResponse":
        return cls(
            created=[SubjectResponse.from_entity(s) for s in result.created],
            skipped_duplicate_names=result.skipped_duplicate_names,
        )


class SubjectPackRemoveResponse(BaseModel):
    removed_count: int


class AppliedSubjectPackResponse(BaseModel):
    academic_level_id: str
    section_id: str | None
    country_name: str
    education_system_name: str
    academic_level_name: str
    section_name: str | None
    subject_count: int
    subjects: list[SubjectResponse]

    @classmethod
    def from_entity(cls, pack: AppliedPack) -> "AppliedSubjectPackResponse":
        return cls(
            academic_level_id=pack.academic_level_id,
            section_id=pack.section_id,
            country_name=pack.country_name,
            education_system_name=pack.education_system_name,
            academic_level_name=pack.academic_level_name,
            section_name=pack.section_name,
            subject_count=len(pack.subjects),
            subjects=[SubjectResponse.from_entity(s) for s in pack.subjects],
        )
