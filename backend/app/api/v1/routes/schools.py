"""The institution catalog. Unlike curriculum.py, these routes are public
(no auth) — a student needs to search for (or add) their school *during* the
registration form, before an account exists to authenticate with. Same
trade-off POST /auth/register itself already makes; there's no admin
gate/abuse protection here yet, matching the rest of this codebase's current
scope."""
from fastapi import APIRouter, Depends

from app.api.v1.deps import get_school_service
from app.api.v1.schemas.school import (
    CreateSchoolClassRequest,
    CreateSchoolRequest,
    SchoolClassResponse,
    SchoolResponse,
)
from app.services.school_service import SchoolService

router = APIRouter(prefix="/schools", tags=["schools"])


@router.get("", response_model=list[SchoolResponse])
async def search_schools(
    q: str = "",
    service: SchoolService = Depends(get_school_service),
) -> list[SchoolResponse]:
    schools = await service.search(q)
    return [SchoolResponse.from_entity(s) for s in schools]


@router.post("", response_model=SchoolResponse, status_code=201)
async def create_school(
    payload: CreateSchoolRequest,
    service: SchoolService = Depends(get_school_service),
) -> SchoolResponse:
    school = await service.create(name=payload.name, country=payload.country, city=payload.city)
    return SchoolResponse.from_entity(school)


@router.get("/{school_id}", response_model=SchoolResponse)
async def get_school(
    school_id: str,
    service: SchoolService = Depends(get_school_service),
) -> SchoolResponse:
    school = await service.get(school_id)
    return SchoolResponse.from_entity(school)


@router.get("/{school_id}/classes", response_model=list[SchoolClassResponse])
async def list_school_classes(
    school_id: str,
    service: SchoolService = Depends(get_school_service),
) -> list[SchoolClassResponse]:
    classes = await service.list_classes(school_id)
    return [SchoolClassResponse.from_entity(c) for c in classes]


@router.post("/{school_id}/classes", response_model=SchoolClassResponse, status_code=201)
async def create_school_class(
    school_id: str,
    payload: CreateSchoolClassRequest,
    service: SchoolService = Depends(get_school_service),
) -> SchoolClassResponse:
    school_class = await service.create_class(school_id, level=payload.level, label=payload.label)
    return SchoolClassResponse.from_entity(school_class)
