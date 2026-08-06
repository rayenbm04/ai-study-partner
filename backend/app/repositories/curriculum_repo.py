from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.curriculum import AcademicLevel, Chapter, Country, CurriculumSubject, EducationSystem, Lesson, Section
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.infrastructure.db.models.curriculum import (
    AcademicLevelModel,
    ChapterModel,
    CountryModel,
    CurriculumSubjectModel,
    EducationSystemModel,
    LessonModel,
    SectionModel,
)


def _country(model: CountryModel) -> Country:
    return Country(id=model.id, name=model.name, code=model.code, created_at=model.created_at)


def _education_system(model: EducationSystemModel) -> EducationSystem:
    return EducationSystem(id=model.id, country_id=model.country_id, name=model.name, created_at=model.created_at)


def _academic_level(model: AcademicLevelModel) -> AcademicLevel:
    return AcademicLevel(
        id=model.id,
        education_system_id=model.education_system_id,
        name=model.name,
        order_index=model.order_index,
        created_at=model.created_at,
    )


def _section(model: SectionModel) -> Section:
    return Section(id=model.id, academic_level_id=model.academic_level_id, name=model.name, created_at=model.created_at)


def _curriculum_subject(model: CurriculumSubjectModel) -> CurriculumSubject:
    return CurriculumSubject(
        id=model.id,
        academic_level_id=model.academic_level_id,
        section_id=model.section_id,
        name=model.name,
        created_at=model.created_at,
    )


def _chapter(model: ChapterModel) -> Chapter:
    return Chapter(
        id=model.id,
        curriculum_subject_id=model.curriculum_subject_id,
        name=model.name,
        order_index=model.order_index,
        created_at=model.created_at,
    )


def _lesson(model: LessonModel) -> Lesson:
    return Lesson(
        id=model.id, chapter_id=model.chapter_id, name=model.name, order_index=model.order_index, created_at=model.created_at
    )


class SqlAlchemyCurriculumRepository(CurriculumRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_countries(self) -> list[Country]:
        stmt = select(CountryModel).order_by(CountryModel.name)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_country(m) for m in models]

    async def create_country(self, *, name: str, code: str | None) -> Country:
        model = CountryModel(name=name, code=code)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _country(model)

    async def list_education_systems(self, country_id: str) -> list[EducationSystem]:
        stmt = (
            select(EducationSystemModel)
            .where(EducationSystemModel.country_id == country_id)
            .order_by(EducationSystemModel.name)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_education_system(m) for m in models]

    async def create_education_system(self, *, country_id: str, name: str) -> EducationSystem:
        model = EducationSystemModel(country_id=country_id, name=name)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _education_system(model)

    async def list_academic_levels(self, education_system_id: str) -> list[AcademicLevel]:
        stmt = (
            select(AcademicLevelModel)
            .where(AcademicLevelModel.education_system_id == education_system_id)
            .order_by(AcademicLevelModel.order_index, AcademicLevelModel.name)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_academic_level(m) for m in models]

    async def create_academic_level(self, *, education_system_id: str, name: str, order_index: int) -> AcademicLevel:
        model = AcademicLevelModel(education_system_id=education_system_id, name=name, order_index=order_index)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _academic_level(model)

    async def get_academic_level(self, academic_level_id: str) -> AcademicLevel | None:
        model = await self._session.get(AcademicLevelModel, academic_level_id)
        return _academic_level(model) if model else None

    async def list_sections(self, academic_level_id: str) -> list[Section]:
        stmt = select(SectionModel).where(SectionModel.academic_level_id == academic_level_id).order_by(SectionModel.name)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_section(m) for m in models]

    async def create_section(self, *, academic_level_id: str, name: str) -> Section:
        model = SectionModel(academic_level_id=academic_level_id, name=name)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _section(model)

    async def get_section(self, section_id: str) -> Section | None:
        model = await self._session.get(SectionModel, section_id)
        return _section(model) if model else None

    async def get_education_system(self, education_system_id: str) -> EducationSystem | None:
        model = await self._session.get(EducationSystemModel, education_system_id)
        return _education_system(model) if model else None

    async def get_country(self, country_id: str) -> Country | None:
        model = await self._session.get(CountryModel, country_id)
        return _country(model) if model else None

    async def list_subjects(self, academic_level_id: str, *, section_id: str | None = None) -> list[CurriculumSubject]:
        stmt = select(CurriculumSubjectModel).where(CurriculumSubjectModel.academic_level_id == academic_level_id)
        if section_id is not None:
            stmt = stmt.where(CurriculumSubjectModel.section_id == section_id)
        stmt = stmt.order_by(CurriculumSubjectModel.name)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_curriculum_subject(m) for m in models]

    async def get_subject(self, curriculum_subject_id: str) -> CurriculumSubject | None:
        model = await self._session.get(CurriculumSubjectModel, curriculum_subject_id)
        return _curriculum_subject(model) if model else None

    async def list_subjects_by_ids(self, curriculum_subject_ids: list[str]) -> list[CurriculumSubject]:
        if not curriculum_subject_ids:
            return []
        stmt = select(CurriculumSubjectModel).where(CurriculumSubjectModel.id.in_(curriculum_subject_ids))
        models = (await self._session.execute(stmt)).scalars().all()
        return [_curriculum_subject(m) for m in models]

    async def create_subject(self, *, academic_level_id: str, section_id: str | None, name: str) -> CurriculumSubject:
        model = CurriculumSubjectModel(academic_level_id=academic_level_id, section_id=section_id, name=name)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _curriculum_subject(model)

    async def list_chapters(self, curriculum_subject_id: str) -> list[Chapter]:
        stmt = (
            select(ChapterModel)
            .where(ChapterModel.curriculum_subject_id == curriculum_subject_id)
            .order_by(ChapterModel.order_index, ChapterModel.name)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_chapter(m) for m in models]

    async def create_chapter(self, *, curriculum_subject_id: str, name: str, order_index: int) -> Chapter:
        model = ChapterModel(curriculum_subject_id=curriculum_subject_id, name=name, order_index=order_index)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _chapter(model)

    async def list_lessons(self, chapter_id: str) -> list[Lesson]:
        stmt = select(LessonModel).where(LessonModel.chapter_id == chapter_id).order_by(LessonModel.order_index, LessonModel.name)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_lesson(m) for m in models]

    async def create_lesson(self, *, chapter_id: str, name: str, order_index: int) -> Lesson:
        model = LessonModel(chapter_id=chapter_id, name=name, order_index=order_index)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _lesson(model)
