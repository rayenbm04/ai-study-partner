from app.api.v1 import deps
from tests.unit.fakes import FakeEmailSender


async def _register(client, email="student@example.com", password="password123", pseudo=None, school_id=None):
    payload = {
        "email": email,
        "password": password,
        "confirm_password": password,
        "firstname": "Ada",
        "lastname": "Lovelace",
        "pseudo": pseudo or email.split("@")[0],
        "date_of_birth": "2005-01-01",
    }
    if school_id is not None:
        payload["school_id"] = school_id
    return await client.post("/api/v1/auth/register", json=payload)


def _extract_token(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and " " not in stripped and len(stripped) > 10:
            return stripped
    raise AssertionError(f"couldn't find a token in email body: {body!r}")


def _use_fake_email_sender(client) -> FakeEmailSender:
    fake = FakeEmailSender()
    client.app.dependency_overrides[deps.get_email_sender] = lambda: fake
    return fake


async def test_register_login_me_flow(client):
    register_resp = await _register(client)
    assert register_resp.status_code == 201
    assert register_resp.json()["email"] == "student@example.com"

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "password123"}
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert tokens["token_type"] == "bearer"

    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "student@example.com"


async def test_register_duplicate_email_rejected(client):
    await _register(client)
    resp = await _register(client)
    assert resp.status_code == 409


async def test_register_duplicate_pseudo_rejected(client):
    await _register(client, email="student@example.com", pseudo="ada")
    resp = await _register(client, email="other@example.com", pseudo="ada")
    assert resp.status_code == 409


async def test_register_password_mismatch_rejected(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "password123",
            "confirm_password": "different123",
            "firstname": "Ada",
            "lastname": "Lovelace",
            "pseudo": "student",
            "date_of_birth": "2005-01-01",
        },
    )
    assert resp.status_code == 400


async def test_register_weak_password_rejected(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "password",
            "confirm_password": "password",
            "firstname": "Ada",
            "lastname": "Lovelace",
            "pseudo": "student",
            "date_of_birth": "2005-01-01",
        },
    )
    assert resp.status_code == 400


async def test_register_missing_pseudo_rejected(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "firstname": "Ada",
            "lastname": "Lovelace",
            "date_of_birth": "2005-01-01",
        },
    )
    assert resp.status_code == 422


async def test_register_future_date_of_birth_rejected(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "firstname": "Ada",
            "lastname": "Lovelace",
            "pseudo": "student",
            "date_of_birth": "2099-01-01",
        },
    )
    assert resp.status_code == 422


async def test_register_with_school_id_succeeds(client):
    school_resp = await client.post(
        "/api/v1/schools", json={"name": "Lycee Victor Hugo", "country": "FR", "city": "Paris"}
    )
    school_id = school_resp.json()["id"]

    resp = await _register(client, school_id=school_id)
    assert resp.status_code == 201
    body = resp.json()
    assert body["school_id"] == school_id
    assert body["pseudo"] == "student"


async def test_register_rejects_unknown_school_id(client):
    resp = await _register(client, school_id="does-not-exist")
    assert resp.status_code == 404


async def test_login_wrong_password_rejected(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_repeated_failed_logins_lock_the_account(client):
    await _register(client)
    for _ in range(5):  # default LOGIN_MAX_FAILED_ATTEMPTS
        await client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "wrong-password"})

    resp = await client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "password123"}
    )
    assert resp.status_code == 423


async def test_me_without_token_rejected(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 403  # HTTPBearer rejects missing credentials before the route runs


async def test_refresh_rotates_and_invalidates_old_token(client):
    await _register(client)
    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "password123"}
    )
    old_refresh = login_resp.json()["refresh_token"]

    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["refresh_token"] != old_refresh

    replay_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert replay_resp.status_code == 401


async def test_logout_invalidates_refresh_token(client):
    await _register(client)
    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "password123"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 204

    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401


async def test_verify_email_flow(client):
    fake_email = _use_fake_email_sender(client)
    await _register(client)
    token = _extract_token(fake_email.sent[0]["body"])

    resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert resp.status_code == 200
    assert resp.json()["is_verified"] is True


async def test_verify_email_rejects_bad_token(client):
    resp = await client.post("/api/v1/auth/verify-email", json={"token": "not-a-real-token"})
    assert resp.status_code == 401


async def test_forgot_password_then_reset_password_flow(client):
    fake_email = _use_fake_email_sender(client)
    await _register(client)
    fake_email.sent.clear()

    forgot_resp = await client.post("/api/v1/auth/forgot-password", json={"email": "student@example.com"})
    assert forgot_resp.status_code == 204
    token = _extract_token(fake_email.sent[0]["body"])

    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "new-p4ss123", "confirm_new_password": "new-p4ss123"},
    )
    assert reset_resp.status_code == 204

    old_login = await client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "password123"}
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "new-p4ss123"}
    )
    assert new_login.status_code == 200


async def test_forgot_password_unknown_email_still_returns_204(client):
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert resp.status_code == 204


async def test_reset_password_rejects_bad_token(client):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "new-p4ss123", "confirm_new_password": "new-p4ss123"},
    )
    assert resp.status_code == 401
