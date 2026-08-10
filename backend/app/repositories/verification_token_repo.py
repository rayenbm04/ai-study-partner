from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.verification_token import TokenPurpose, VerificationToken
from app.domain.repositories.verification_token_repository import VerificationTokenRepository
from app.infrastructure.db.models.verification_token import VerificationTokenModel


def _to_entity(model: VerificationTokenModel) -> VerificationToken:
    return VerificationToken(
        id=model.id,
        user_id=model.user_id,
        token_hash=model.token_hash,
        purpose=model.purpose,
        expires_at=model.expires_at,
        used_at=model.used_at,
        created_at=model.created_at,
    )


class SqlAlchemyVerificationTokenRepository(VerificationTokenRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self, *, user_id: str, token_hash: str, purpose: TokenPurpose, expires_at: datetime
    ) -> VerificationToken:
        model = VerificationTokenModel(user_id=user_id, token_hash=token_hash, purpose=purpose, expires_at=expires_at)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_active_by_hash(self, token_hash: str, *, purpose: TokenPurpose) -> VerificationToken | None:
        stmt = select(VerificationTokenModel).where(
            VerificationTokenModel.token_hash == token_hash, VerificationTokenModel.purpose == purpose
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        entity = _to_entity(model)
        now = datetime.now(timezone.utc)
        expires_at = entity.expires_at if entity.expires_at.tzinfo else entity.expires_at.replace(tzinfo=timezone.utc)
        if not entity.is_active or expires_at < now:
            return None
        return entity

    async def mark_used(self, token_id: str) -> None:
        stmt = (
            update(VerificationTokenModel)
            .where(VerificationTokenModel.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)

    async def invalidate_all_for_user(self, user_id: str, *, purpose: TokenPurpose) -> None:
        stmt = (
            update(VerificationTokenModel)
            .where(
                VerificationTokenModel.user_id == user_id,
                VerificationTokenModel.purpose == purpose,
                VerificationTokenModel.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)
