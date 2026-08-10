from datetime import date

import pytest

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
from app.services.auth_service import AuthService
from tests.unit.fakes import (
    FakeEmailSender,
    FakeRefreshTokenRepository,
    FakeSchoolRepository,
    FakeSecurityEventRepository,
    FakeUserRepository,
    FakeVerificationTokenRepository,
)

_DOB = date(2005, 1, 1)


@pytest.fixture
def parts():
    """Builds an AuthService plus the individual fakes it wraps, so tests
    can both drive the service and inspect its dependencies directly (e.g.
    asserting an email got queued, or seeding a school)."""
    users = FakeUserRepository()
    refresh = FakeRefreshTokenRepository()
    schools = FakeSchoolRepository()
    tokens = FakeVerificationTokenRepository()
    events = FakeSecurityEventRepository()
    email = FakeEmailSender()
    service = AuthService(
        users,
        refresh,
        school_repo=schools,
        verification_token_repo=tokens,
        security_event_repo=events,
        email_sender=email,
        max_failed_attempts=3,
        lockout_minutes=15,
    )
    return service, users, refresh, schools, tokens, events, email


def _register_kwargs(**overrides):
    kwargs = dict(
        email="a@x.com",
        password="p4ssw0rd!zx",
        confirm_password="p4ssw0rd!zx",
        firstname="A",
        lastname="B",
        pseudo="alice",
        date_of_birth=_DOB,
    )
    kwargs.update(overrides)
    return kwargs


async def test_register_creates_user(parts):
    service, *_ = parts
    user = await service.register(**_register_kwargs())
    assert user.email == "a@x.com"
    assert user.pseudo == "alice"
    assert user.date_of_birth == _DOB
    assert user.hashed_password != "p4ssw0rd!zx"


async def test_register_sends_a_verification_email(parts):
    service, *_, email = parts
    await service.register(**_register_kwargs())
    assert len(email.sent) == 1
    assert email.sent[0]["to"] == "a@x.com"
    assert "subject" in email.sent[0]


async def test_register_rejects_duplicate_email(parts):
    service, *_ = parts
    await service.register(**_register_kwargs())
    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(**_register_kwargs(pseudo="bob"))


async def test_register_rejects_duplicate_pseudo(parts):
    service, *_ = parts
    await service.register(**_register_kwargs())
    with pytest.raises(PseudoAlreadyTakenError):
        await service.register(**_register_kwargs(email="other@x.com"))


async def test_register_rejects_password_mismatch(parts):
    service, *_ = parts
    with pytest.raises(PasswordMismatchError):
        await service.register(**_register_kwargs(confirm_password="something-else123"))


async def test_register_rejects_weak_password(parts):
    service, *_ = parts
    with pytest.raises(WeakPasswordError):
        await service.register(**_register_kwargs(password="password", confirm_password="password"))


async def test_register_accepts_valid_school_id(parts):
    service, _users, _refresh, schools, *_ = parts
    school = await schools.create(name="Lycee Victor Hugo", country="FR", city="Paris")
    user = await service.register(**_register_kwargs(school_id=school.id))
    assert user.school_id == school.id


async def test_register_rejects_unknown_school_id(parts):
    service, *_ = parts
    with pytest.raises(SchoolNotFoundError):
        await service.register(**_register_kwargs(school_id="does-not-exist"))


async def test_authenticate_success(parts):
    service, *_ = parts
    await service.register(**_register_kwargs())
    user = await service.authenticate(email="a@x.com", password="p4ssw0rd!zx")
    assert user.email == "a@x.com"
    assert user.last_login_at is not None
    assert user.failed_login_attempts == 0


async def test_authenticate_wrong_password(parts):
    service, *_ = parts
    await service.register(**_register_kwargs())
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(email="a@x.com", password="wrong-password")


async def test_authenticate_unknown_email(parts):
    service, *_ = parts
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(email="ghost@x.com", password="password123")


async def test_repeated_failed_logins_lock_the_account(parts):
    service, *_ = parts
    await service.register(**_register_kwargs())

    for _ in range(3):  # max_failed_attempts=3
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate(email="a@x.com", password="wrong-password")

    with pytest.raises(AccountLockedError):
        await service.authenticate(email="a@x.com", password="p4ssw0rd!zx")  # even the right password is blocked


async def test_successful_login_resets_failed_attempts(parts):
    service, *_ = parts
    await service.register(**_register_kwargs())

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(email="a@x.com", password="wrong-password")

    user = await service.authenticate(email="a@x.com", password="p4ssw0rd!zx")
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


async def test_refresh_rotates_token_and_old_one_stops_working(parts):
    service, *_ = parts
    user = await service.register(**_register_kwargs())
    first_pair = await service.issue_token_pair(user)

    second_pair = await service.refresh(first_pair.refresh_token)
    assert second_pair.refresh_token != first_pair.refresh_token

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(first_pair.refresh_token)


async def test_refresh_rejects_unknown_token(parts):
    service, *_ = parts
    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh("not-a-real-token")


async def test_logout_revokes_refresh_token(parts):
    service, *_ = parts
    user = await service.register(**_register_kwargs())
    pair = await service.issue_token_pair(user)

    await service.logout(pair.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(pair.refresh_token)


def _extract_token(body: str) -> str:
    # Both email bodies put the raw token alone on its own line.
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and " " not in stripped and len(stripped) > 10:
            return stripped
    raise AssertionError(f"couldn't find a token in email body: {body!r}")


async def test_verify_email_marks_user_verified(parts):
    service, *_, email = parts
    user = await service.register(**_register_kwargs())
    assert user.is_verified is False
    token = _extract_token(email.sent[0]["body"])

    verified = await service.verify_email(token)
    assert verified.is_verified is True
    assert verified.email_verified_at is not None


async def test_verify_email_rejects_unknown_token(parts):
    service, *_ = parts
    with pytest.raises(InvalidOrExpiredTokenError):
        await service.verify_email("not-a-real-token")


async def test_verify_email_token_is_single_use(parts):
    service, *_, email = parts
    await service.register(**_register_kwargs())
    token = _extract_token(email.sent[0]["body"])

    await service.verify_email(token)
    with pytest.raises(InvalidOrExpiredTokenError):
        await service.verify_email(token)


async def test_request_password_reset_sends_an_email(parts):
    service, *_, email = parts
    await service.register(**_register_kwargs())
    email.sent.clear()

    await service.request_password_reset("a@x.com")
    assert len(email.sent) == 1


async def test_request_password_reset_unknown_email_does_not_error(parts):
    service, *_, email = parts
    await service.request_password_reset("ghost@x.com")  # must not raise
    assert email.sent == []


async def test_reset_password_updates_password_and_allows_login(parts):
    service, *_, email = parts
    await service.register(**_register_kwargs())
    email.sent.clear()

    await service.request_password_reset("a@x.com")
    token = _extract_token(email.sent[0]["body"])

    await service.reset_password(raw_token=token, new_password="new-p4ss123", confirm_new_password="new-p4ss123")

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(email="a@x.com", password="p4ssw0rd!zx")
    user = await service.authenticate(email="a@x.com", password="new-p4ss123")
    assert user.email == "a@x.com"


async def test_reset_password_rejects_mismatch(parts):
    service, *_, email = parts
    await service.register(**_register_kwargs())
    email.sent.clear()
    await service.request_password_reset("a@x.com")
    token = _extract_token(email.sent[0]["body"])

    with pytest.raises(PasswordMismatchError):
        await service.reset_password(raw_token=token, new_password="new-p4ss123", confirm_new_password="different123")


async def test_reset_password_rejects_unknown_token(parts):
    service, *_ = parts
    with pytest.raises(InvalidOrExpiredTokenError):
        await service.reset_password(raw_token="not-a-real-token", new_password="new-p4ss123", confirm_new_password="new-p4ss123")


async def test_reset_password_token_is_single_use(parts):
    service, *_, email = parts
    await service.register(**_register_kwargs())
    email.sent.clear()
    await service.request_password_reset("a@x.com")
    token = _extract_token(email.sent[0]["body"])

    await service.reset_password(raw_token=token, new_password="new-p4ss123", confirm_new_password="new-p4ss123")
    with pytest.raises(InvalidOrExpiredTokenError):
        await service.reset_password(raw_token=token, new_password="another-p4ss1", confirm_new_password="another-p4ss1")


async def test_reset_password_revokes_existing_refresh_tokens(parts):
    service, *_, email = parts
    user = await service.register(**_register_kwargs())
    pair = await service.issue_token_pair(user)
    email.sent.clear()
    await service.request_password_reset("a@x.com")
    token = _extract_token(email.sent[0]["body"])

    await service.reset_password(raw_token=token, new_password="new-p4ss123", confirm_new_password="new-p4ss123")

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(pair.refresh_token)
