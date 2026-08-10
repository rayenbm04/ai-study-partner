"""The institution catalog a student picks their school from at registration
(app/domain/entities/school.py has the full reasoning for why this is
separate from the curriculum catalog's AcademicLevel/Section). Read-mostly,
plus create — there's no admin tooling yet, so any authenticated user can add
a school/class that's missing from a search, mirroring the "not in list"
fallback the original registration spec called for."""
from app.core.exceptions import SchoolClassNotFoundError, SchoolNotFoundError
from app.domain.entities.school import School, SchoolClass
from app.domain.repositories.school_repository import SchoolRepository


class SchoolService:
    def __init__(self, school_repo: SchoolRepository):
        self._schools = school_repo

    async def search(self, query: str) -> list[School]:
        return await self._schools.search(query.strip())

    async def get(self, school_id: str) -> School:
        school = await self._schools.get_by_id(school_id)
        if school is None:
            raise SchoolNotFoundError(school_id)
        return school

    async def create(self, *, name: str, country: str | None, city: str | None) -> School:
        return await self._schools.create(name=name.strip(), country=country, city=city)

    async def list_classes(self, school_id: str) -> list[SchoolClass]:
        await self.get(school_id)  # 404s if the school itself doesn't exist
        return await self._schools.list_classes(school_id)

    async def create_class(self, school_id: str, *, level: str, label: str) -> SchoolClass:
        await self.get(school_id)
        return await self._schools.create_class(school_id=school_id, level=level.strip(), label=label.strip())

    async def get_class(self, class_id: str) -> SchoolClass:
        school_class = await self._schools.get_class(class_id)
        if school_class is None:
            raise SchoolClassNotFoundError(class_id)
        return school_class
