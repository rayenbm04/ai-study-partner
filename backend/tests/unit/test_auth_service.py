from datetime import date

import pytest

from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PasswordMismatchError,
    PseudoAlreadyTakenError,
    WeakPasswordError,
)
from app.services.auth_service import AuthService
from tests.unit.fakes import FakeRefreshTokenRepository, FakeUserRepository

_DOB = date(2005, 1, 1)


@pytest.fixture
def auth_service():
    return AuthService(FakeUserRepository(), FakeRefreshTokenRepository())


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


async def test_register_creates_user(auth_service):
    user = await auth_service.register(**_register_kwargs())
    assert user.email == "a@x.com"
    assert user.pseudo == "alice"
    assert user.date_of_birth == _DOB
    assert user.hashed_password != "p4ssw0rd!zx"


async def test_register_rejects_duplicate_email(auth_service):
    await auth_service.register(**_register_kwargs())
    with pytest.raises(EmailAlreadyRegisteredError):
        await auth_service.register(**_register_kwargs(pseudo="bob"))


async def test_register_rejects_duplicate_pseudo(auth_service):
    await auth_service.register(**_register_kwargs())
    with pytest.raises(PseudoAlreadyTakenError):
        await auth_service.register(**_register_kwargs(email="other@x.com"))


async def test_register_rejects_password_mismatch(auth_service):
    with pytest.raises(PasswordMismatchError):
        await auth_service.register(**_register_kwargs(confirm_password="something-else123"))


async def test_register_rejects_weak_password(auth_service):
    with pytest.raises(WeakPasswordError):
        await auth_service.register(**_register_kwargs(password="password", confirm_password="password"))


async def test_register_accepts_optional_school_name(auth_service):
    user = await auth_service.register(**_register_kwargs(school_name="Lycée Victor Hugo"))
    assert user.school_name == "Lycée Victor Hugo"


async def test_authenticate_success(auth_service):
    await auth_service.register(**_register_kwargs())
    user = await auth_service.authenticate(email="a@x.com", password="p4ssw0rd!zx")
    assert user.email == "a@x.com"


async def test_authenticate_wrong_password(auth_service):
    await auth_service.register(**_register_kwargs())
    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate(email="a@x.com", password="wrong-password")


async def test_authenticate_unknown_email(auth_service):
    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate(email="ghost@x.com", password="password123")


async def test_refresh_rotates_token_and_old_one_stops_working(auth_service):
    user = await auth_service.register(**_register_kwargs())
    first_pair = await auth_service.issue_token_pair(user)

    second_pair = await auth_service.refresh(first_pair.refresh_token)
    assert second_pair.refresh_token != first_pair.refresh_token

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(first_pair.refresh_token)


async def test_refresh_rejects_unknown_token(auth_service):
    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh("not-a-real-token")


async def test_logout_revokes_refresh_token(auth_service):
    user = await auth_service.register(**_register_kwargs())
    pair = await auth_service.issue_token_pair(user)

    await auth_service.logout(pair.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(pair.refresh_token)
