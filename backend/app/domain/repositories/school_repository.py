from abc import ABC, abstractmethod

from app.domain.entities.school import School, SchoolClass


class SchoolRepository(ABC):
    @abstractmethod
    async def search(self, query: str, *, limit: int = 20) -> list[School]: ...

    @abstractmethod
    async def get_by_id(self, school_id: str) -> School | None: ...

    @abstractmethod
    async def create(self, *, name: str, country: str | None, city: str | None) -> School: ...

    @abstractmethod
    async def list_classes(self, school_id: str) -> list[SchoolClass]: ...

    @abstractmethod
    async def get_class(self, class_id: str) -> SchoolClass | None: ...

    @abstractmethod
    async def create_class(self, *, school_id: str, level: str, label: str) -> SchoolClass: ...
