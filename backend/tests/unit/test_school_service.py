import pytest

from app.core.exceptions import SchoolClassNotFoundError, SchoolNotFoundError
from app.services.school_service import SchoolService
from tests.unit.fakes import FakeSchoolRepository


@pytest.fixture
def service():
    return SchoolService(FakeSchoolRepository())


async def test_create_and_search_school(service):
    await service.create(name="Lycee Victor Hugo", country="FR", city="Paris")
    await service.create(name="Lycee Carnot", country="FR", city="Paris")

    results = await service.search("victor")
    assert [s.name for s in results] == ["Lycee Victor Hugo"]


async def test_search_empty_query_returns_all(service):
    await service.create(name="Lycee Victor Hugo", country="FR", city="Paris")
    await service.create(name="Lycee Carnot", country="FR", city="Paris")

    results = await service.search("")
    assert len(results) == 2


async def test_get_unknown_school_raises(service):
    with pytest.raises(SchoolNotFoundError):
        await service.get("does-not-exist")


async def test_create_and_list_classes(service):
    school = await service.create(name="Lycee Victor Hugo", country="FR", city="Paris")
    await service.create_class(school.id, level="Seconde", label="Seconde A")

    classes = await service.list_classes(school.id)
    assert [c.label for c in classes] == ["Seconde A"]


async def test_list_classes_for_unknown_school_raises(service):
    with pytest.raises(SchoolNotFoundError):
        await service.list_classes("does-not-exist")


async def test_create_class_for_unknown_school_raises(service):
    with pytest.raises(SchoolNotFoundError):
        await service.create_class("does-not-exist", level="Seconde", label="Seconde A")


async def test_get_unknown_class_raises(service):
    with pytest.raises(SchoolClassNotFoundError):
        await service.get_class("does-not-exist")
