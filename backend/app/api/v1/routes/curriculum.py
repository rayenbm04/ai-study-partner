"""Read-only browsing of the global curriculum catalog — no ownership
scoping, since this is shared reference data, not user-owned. Lets a client
walk Country -> EducationSystem -> AcademicLevel -> Section -> CurriculumSubject
-> Chapter -> Lesson to find the curriculum_subject_id to link a user's
Subject to (see PATCH /subjects/{id})."""
from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_curriculum_repo
from app.api.v1.schemas.curriculum import (
    AcademicLevelResponse,
    ChapterResponse,
    CountryResponse,
    CurriculumSubjectResponse,
    EducationSystemResponse,
    LessonResponse,
    SectionResponse,
)
from app.domain.entities.user import User
from app.domain.repositories.curriculum_repository import CurriculumRepository

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.get("/countries", response_model=list[CountryResponse])
async def list_countries(
    current_user: User = Depends(get_current_user),
    repo: CurriculumRepository = Depends(get_curriculum_repo),
) -> list[CountryResponse]:
    countries = await repo.list_countries()
    return [CountryResponse.from_entity(c) for c in countries]


@router.get("/countries/{country_id}/education-systems", response_model=list[EducationSystemResponse])
async def list_education_systems(
    country_id: str,
    current_user: User = Depends(get_current_user),
    repo: CurriculumRepository = Depends(get_curriculum_repo),
) -> list[EducationSystemResponse]:
    systems = await repo.list_education_systems(country_id)
    return [EducationSystemResponse.from_entity(s) for s in systems]


@router.get("/education-systems/{education_system_id}/academic-levels", response_model=list[AcademicLevelResponse])
async def list_academic_levels(
    education_system_id: str,
    current_user: User = Depends(get_current_user),
    repo: CurriculumRepository = Depends(get_curriculum_repo),
) -> list[AcademicLevelResponse]:
    levels = await repo.list_academic_levels(education_system_id)
    return [AcademicLevelResponse.from_entity(lvl) for lvl in levels]


@router.get("/academic-levels/{academic_level_id}/sections", response_model=list[SectionResponse])
async def list_sections(
    academic_level_id: str,
    current_user: User = Depends(get_current_user),
    repo: CurriculumRepository = Depends(get_curriculum_repo),
) -> list[SectionResponse]:
    sections = await repo.list_sections(academic_level_id)
    return [SectionResponse.from_entity(s) for s in sections]


@router.get("/academic-levels/{academic_level_id}/subjects", response_model=list[CurriculumSubjectResponse])
async def list_curriculum_subjects(
    academic_level_id: str,
    section_id: str | None = None,
    current_user: User = Depends(get_current_user),
    repo: CurriculumRepository = Depends(get_curriculum_repo),
) -> list[CurriculumSubjectResponse]:
    subjects = await repo.list_subjects(academic_level_id, section_id=section_id)
    return [CurriculumSubjectResponse.from_entity(s) for s in subjects]


@router.get("/subjects/{curriculum_subject_id}/chapters", response_model=list[ChapterResponse])
async def list_chapters(
    curriculum_subject_id: str,
    current_user: User = Depends(get_current_user),
    repo: CurriculumRepository = Depends(get_curriculum_repo),
) -> list[ChapterResponse]:
    chapters = await repo.list_chapters(curriculum_subject_id)
    return [ChapterResponse.from_entity(c) for c in chapters]


@router.get("/chapters/{chapter_id}/lessons", response_model=list[LessonResponse])
async def list_lessons(
    chapter_id: str,
    current_user: User = Depends(get_current_user),
    repo: CurriculumRepository = Depends(get_curriculum_repo),
) -> list[LessonResponse]:
    lessons = await repo.list_lessons(chapter_id)
    return [LessonResponse.from_entity(lesson) for lesson in lessons]
