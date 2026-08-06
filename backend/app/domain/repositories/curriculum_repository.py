from abc import ABC, abstractmethod

from app.domain.entities.curriculum import AcademicLevel, Chapter, Country, CurriculumSubject, EducationSystem, Lesson, Section


class CurriculumRepository(ABC):
    """Read-mostly access to the global curriculum catalog tree. One
    repository for all seven node types (rather than one per table) since
    they're always populated and queried together as a single tree — unlike
    documents/subjects, which have independent lifecycles."""

    @abstractmethod
    async def list_countries(self) -> list[Country]: ...

    @abstractmethod
    async def create_country(self, *, name: str, code: str | None) -> Country: ...

    @abstractmethod
    async def list_education_systems(self, country_id: str) -> list[EducationSystem]: ...

    @abstractmethod
    async def create_education_system(self, *, country_id: str, name: str) -> EducationSystem: ...

    @abstractmethod
    async def list_academic_levels(self, education_system_id: str) -> list[AcademicLevel]: ...

    @abstractmethod
    async def create_academic_level(self, *, education_system_id: str, name: str, order_index: int) -> AcademicLevel: ...

    @abstractmethod
    async def get_academic_level(self, academic_level_id: str) -> AcademicLevel | None: ...

    @abstractmethod
    async def list_sections(self, academic_level_id: str) -> list[Section]: ...

    @abstractmethod
    async def create_section(self, *, academic_level_id: str, name: str) -> Section: ...

    @abstractmethod
    async def get_section(self, section_id: str) -> Section | None: ...

    @abstractmethod
    async def get_education_system(self, education_system_id: str) -> EducationSystem | None: ...

    @abstractmethod
    async def get_country(self, country_id: str) -> Country | None: ...

    @abstractmethod
    async def list_subjects(self, academic_level_id: str, *, section_id: str | None = None) -> list[CurriculumSubject]: ...

    @abstractmethod
    async def get_subject(self, curriculum_subject_id: str) -> CurriculumSubject | None: ...

    @abstractmethod
    async def list_subjects_by_ids(self, curriculum_subject_ids: list[str]) -> list[CurriculumSubject]: ...

    @abstractmethod
    async def create_subject(self, *, academic_level_id: str, section_id: str | None, name: str) -> CurriculumSubject: ...

    @abstractmethod
    async def list_chapters(self, curriculum_subject_id: str) -> list[Chapter]: ...

    @abstractmethod
    async def create_chapter(self, *, curriculum_subject_id: str, name: str, order_index: int) -> Chapter: ...

    @abstractmethod
    async def list_lessons(self, chapter_id: str) -> list[Lesson]: ...

    @abstractmethod
    async def create_lesson(self, *, chapter_id: str, name: str, order_index: int) -> Lesson: ...
