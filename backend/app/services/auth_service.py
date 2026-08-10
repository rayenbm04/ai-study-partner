from dataclasses import dataclass
from datetime import date

from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PasswordMismatchError,
    PseudoAlreadyTakenError,
    WeakPasswordError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    verify_password,
    weak_password_reason,
)
from app.domain.entities.user import User
from app.domain.repositories.refresh_token_repository import RefreshTokenRepository
from app.domain.repositories.user_repository import UserRepository


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


class AuthService:
    """Registration, login, and refresh-token rotation.

    Depends only on the repository interfaces, not on SQLAlchemy — unit tests
    exercise this against in-memory fakes with no database at all.
    """

    def __init__(self, user_repo: UserRepository, refresh_repo: RefreshTokenRepository):
        self._users = user_repo
        self._refresh = refresh_repo

    async def register(
        self,
        *,
        email: str,
        password: str,
        confirm_password: str,
        firstname: str,
        lastname: str,
        pseudo: str,
        date_of_birth: date,
        school_name: str | None = None,
    ) -> User:
        if password != confirm_password:
            raise PasswordMismatchError()
        weak_reason = weak_password_reason(password, pseudo=pseudo, email=email)
        if weak_reason is not None:
            raise WeakPasswordError(weak_reason)
        if await self._users.get_by_email(email):
            raise EmailAlreadyRegisteredError(email)
        if await self._users.get_by_pseudo(pseudo):
            raise PseudoAlreadyTakenError(pseudo)
        return await self._users.create(
            email=email,
            firstname=firstname,
            lastname=lastname,
            hashed_password=hash_password(password),
            pseudo=pseudo,
            date_of_birth=date_of_birth,
            school_name=school_name,
        )

    async def authenticate(self, *, email: str, password: str) -> User:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        return user

    async def issue_token_pair(self, user: User) -> TokenPair:
        access_token = create_access_token(subject=user.id, extra_claims={"email": user.email, "role": user.role})
        raw_refresh_token = create_refresh_token()
        await self._refresh.store(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=refresh_token_expiry(),
        )
        return TokenPair(access_token=access_token, refresh_token=raw_refresh_token)

    async def refresh(self, raw_refresh_token: str) -> TokenPair:
        """Rotates the refresh token: the old one is revoked the moment it's used,
        so a leaked-and-replayed refresh token stops working after the legitimate
        client's next refresh."""
        stored = await self._refresh.get_active_by_hash(hash_token(raw_refresh_token))
        if stored is None:
            raise InvalidRefreshTokenError()
        await self._refresh.revoke(stored.id)
        user = await self._users.get_by_id(stored.user_id)
        if user is None:
            raise InvalidRefreshTokenError()
        return await self.issue_token_pair(user)

    async def logout(self, raw_refresh_token: str) -> None:
        stored = await self._refresh.get_active_by_hash(hash_token(raw_refresh_token))
        if stored is not None:
            await self._refresh.revoke(stored.id)
