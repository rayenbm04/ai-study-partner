from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundError
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.db.models.user import UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        firstname=model.firstname,
        lastname=model.lastname,
        hashed_password=model.hashed_password,
        role=model.role,
        created_at=model.created_at,
        pseudo=model.pseudo,
        date_of_birth=model.date_of_birth,
        school_name=model.school_name,
        academic_level_id=model.academic_level_id,
        section_id=model.section_id,
        is_verified=model.is_verified,
        email_verified_at=model.email_verified_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, user_id: str) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_pseudo(self, pseudo: str) -> User | None:
        stmt = select(UserModel).where(UserModel.pseudo == pseudo)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def create(
        self,
        *,
        email: str,
        firstname: str,
        lastname: str,
        hashed_password: str,
        role: str = "student",
        pseudo: str | None = None,
        date_of_birth: date | None = None,
        school_name: str | None = None,
    ) -> User:
        model = UserModel(
            email=email,
            firstname=firstname,
            lastname=lastname,
            hashed_password=hashed_password,
            role=role,
            pseudo=pseudo,
            date_of_birth=date_of_birth,
            school_name=school_name,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def set_classe(self, user_id: str, *, academic_level_id: str | None, section_id: str | None) -> User:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            raise UserNotFoundError(user_id)
        model.academic_level_id = academic_level_id
        model.section_id = section_id
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)
