import pytest

from app.core.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError, InvalidRefreshTokenError
from app.services.auth_service import AuthService
from tests.unit.fakes import FakeRefreshTokenRepository, FakeUserRepository


@pytest.fixture
def auth_service():
    return AuthService(FakeUserRepository(), FakeRefreshTokenRepository())


async def test_register_creates_user(auth_service):
    user = await auth_service.register(email="a@x.com", password="password123", firstname="A", lastname="B")
    assert user.email == "a@x.com"
    assert user.hashed_password != "password123"


async def test_register_rejects_duplicate_email(auth_service):
    await auth_service.register(email="a@x.com", password="password123", firstname="A", lastname="B")
    with pytest.raises(EmailAlreadyRegisteredError):
        await auth_service.register(email="a@x.com", password="other12345", firstname="C", lastname="D")


async def test_authenticate_success(auth_service):
    await auth_service.register(email="a@x.com", password="password123", firstname="A", lastname="B")
    user = await auth_service.authenticate(email="a@x.com", password="password123")
    assert user.email == "a@x.com"


async def test_authenticate_wrong_password(auth_service):
    await auth_service.register(email="a@x.com", password="password123", firstname="A", lastname="B")
    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate(email="a@x.com", password="wrong-password")


async def test_authenticate_unknown_email(auth_service):
    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate(email="ghost@x.com", password="password123")


async def test_refresh_rotates_token_and_old_one_stops_working(auth_service):
    user = await auth_service.register(email="a@x.com", password="password123", firstname="A", lastname="B")
    first_pair = await auth_service.issue_token_pair(user)

    second_pair = await auth_service.refresh(first_pair.refresh_token)
    assert second_pair.refresh_token != first_pair.refresh_token

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(first_pair.refresh_token)


async def test_refresh_rejects_unknown_token(auth_service):
    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh("not-a-real-token")


async def test_logout_revokes_refresh_token(auth_service):
    user = await auth_service.register(email="a@x.com", password="password123", firstname="A", lastname="B")
    pair = await auth_service.issue_token_pair(user)

    await auth_service.logout(pair.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(pair.refresh_token)
