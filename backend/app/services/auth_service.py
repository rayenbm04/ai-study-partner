from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.core.exceptions import (
    AccountLockedError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
    InvalidRefreshTokenError,
    PasswordMismatchError,
    PseudoAlreadyTakenError,
    SchoolNotFoundError,
    WeakPasswordError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_verification_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    verify_password,
    weak_password_reason,
)
from app.domain.entities.user import User
from app.domain.repositories.refresh_token_repository import RefreshTokenRepository
from app.domain.repositories.school_repository import SchoolRepository
from app.domain.repositories.security_event_repository import SecurityEventRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.repositories.verification_token_repository import VerificationTokenRepository
from app.services.email.base import EmailSender


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


class AuthService:
    """Registration, login, refresh-token rotation, login-attempt limiting,
    and email verification / password reset (delivery is stubbed — see
    app/services/email/ — but the tokens, expiry, and state transitions are
    real).

    Depends only on the repository interfaces, not on SQLAlchemy — unit tests
    exercise this against in-memory fakes with no database at all.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_repo: RefreshTokenRepository,
        *,
        school_repo: SchoolRepository,
        verification_token_repo: VerificationTokenRepository,
        security_event_repo: SecurityEventRepository,
        email_sender: EmailSender,
        max_failed_attempts: int = 5,
        lockout_minutes: int = 15,
        email_verification_ttl_hours: int = 24,
        password_reset_ttl_minutes: int = 60,
    ):
        self._users = user_repo
        self._refresh = refresh_repo
        self._schools = school_repo
        self._tokens = verification_token_repo
        self._events = security_event_repo
        self._email = email_sender
        self._max_failed_attempts = max_failed_attempts
        self._lockout_minutes = lockout_minutes
        self._email_verification_ttl_hours = email_verification_ttl_hours
        self._password_reset_ttl_minutes = password_reset_ttl_minutes

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
        school_id: str | None = None,
    ) -> User:
        if password != confirm_password:
            raise PasswordMismatchError()
        weak_reason = weak_password_reason(password, pseudo=pseudo, email=email)
        if weak_reason is not None:
            raise WeakPasswordError(weak_reason)
        if school_id is not None and await self._schools.get_by_id(school_id) is None:
            raise SchoolNotFoundError(school_id)
        if await self._users.get_by_email(email):
            raise EmailAlreadyRegisteredError(email)
        if await self._users.get_by_pseudo(pseudo):
            raise PseudoAlreadyTakenError(pseudo)
        user = await self._users.create(
            email=email,
            firstname=firstname,
            lastname=lastname,
            hashed_password=hash_password(password),
            pseudo=pseudo,
            date_of_birth=date_of_birth,
            school_id=school_id,
        )
        await self._events.record(user_id=user.id, event_type="register")
        await self._send_verification_email(user)
        return user

    async def authenticate(self, *, email: str, password: str) -> User:
        user = await self._users.get_by_email(email)
        if user is None:
            await self._events.record(user_id=None, event_type="login_failed", detail=f"unknown email: {email}")
            raise InvalidCredentialsError()

        now = datetime.now(timezone.utc)
        if user.locked_until is not None:
            locked_until = user.locked_until if user.locked_until.tzinfo else user.locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                await self._events.record(user_id=user.id, event_type="login_blocked_locked")
                retry_minutes = max(1, int((locked_until - now).total_seconds() // 60) + 1)
                raise AccountLockedError(retry_minutes)

        if not verify_password(password, user.hashed_password):
            failed_attempts = user.failed_login_attempts + 1
            locked_until = now + timedelta(minutes=self._lockout_minutes) if failed_attempts >= self._max_failed_attempts else None
            await self._users.update_login_state(
                user.id, failed_login_attempts=failed_attempts, locked_until=locked_until, last_login_at=None
            )
            await self._events.record(
                user_id=user.id,
                event_type="login_locked" if locked_until else "login_failed",
                detail=f"attempt {failed_attempts}/{self._max_failed_attempts}",
            )
            raise InvalidCredentialsError()

        updated = await self._users.update_login_state(
            user.id, failed_login_attempts=0, locked_until=None, last_login_at=now
        )
        await self._events.record(user_id=user.id, event_type="login_success")
        return updated

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

    async def verify_email(self, raw_token: str) -> User:
        token = await self._tokens.get_active_by_hash(hash_token(raw_token), purpose="email_verify")
        if token is None:
            raise InvalidOrExpiredTokenError()
        user = await self._users.get_by_id(token.user_id)
        if user is None:
            raise InvalidOrExpiredTokenError()
        updated = await self._users.mark_email_verified(user.id, datetime.now(timezone.utc))
        await self._tokens.mark_used(token.id)
        await self._events.record(user_id=user.id, event_type="email_verified")
        return updated

    async def request_password_reset(self, email: str) -> None:
        """Always succeeds regardless of whether the email is registered —
        the response can't reveal that, or it becomes an account-enumeration
        oracle. Silently no-ops (after logging) if the email is unknown."""
        user = await self._users.get_by_email(email)
        if user is None:
            await self._events.record(user_id=None, event_type="password_reset_requested_unknown_email")
            return
        await self._tokens.invalidate_all_for_user(user.id, purpose="password_reset")
        raw_token = create_verification_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self._password_reset_ttl_minutes)
        await self._tokens.create(
            user_id=user.id, token_hash=hash_token(raw_token), purpose="password_reset", expires_at=expires_at
        )
        await self._email.send(
            to=user.email,
            subject="Reset your password",
            body=(
                f"Hi {user.firstname},\n\n"
                f"Use this code to reset your password (expires in {self._password_reset_ttl_minutes} minutes):\n\n"
                f"{raw_token}\n\n"
                "If you didn't request this, you can ignore this message."
            ),
        )
        await self._events.record(user_id=user.id, event_type="password_reset_requested")

    async def reset_password(self, *, raw_token: str, new_password: str, confirm_new_password: str) -> None:
        if new_password != confirm_new_password:
            raise PasswordMismatchError()
        token = await self._tokens.get_active_by_hash(hash_token(raw_token), purpose="password_reset")
        if token is None:
            raise InvalidOrExpiredTokenError()
        user = await self._users.get_by_id(token.user_id)
        if user is None:
            raise InvalidOrExpiredTokenError()
        weak_reason = weak_password_reason(new_password, pseudo=user.pseudo, email=user.email)
        if weak_reason is not None:
            raise WeakPasswordError(weak_reason)
        await self._users.set_password(user.id, hash_password(new_password))
        await self._tokens.mark_used(token.id)
        await self._tokens.invalidate_all_for_user(user.id, purpose="password_reset")
        # A password reset invalidates every existing session — a stolen
        # refresh token shouldn't survive the legitimate owner reclaiming the
        # account.
        await self._refresh.revoke_all_for_user(user.id)
        await self._events.record(user_id=user.id, event_type="password_reset_completed")

    async def _send_verification_email(self, user: User) -> None:
        await self._tokens.invalidate_all_for_user(user.id, purpose="email_verify")
        raw_token = create_verification_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self._email_verification_ttl_hours)
        await self._tokens.create(
            user_id=user.id, token_hash=hash_token(raw_token), purpose="email_verify", expires_at=expires_at
        )
        await self._email.send(
            to=user.email,
            subject="Verify your email",
            body=(
                f"Hi {user.firstname},\n\n"
                f"Use this code to verify your email (expires in {self._email_verification_ttl_hours} hours):\n\n"
                f"{raw_token}"
            ),
        )
