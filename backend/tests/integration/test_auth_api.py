async def _register(client, email="student@example.com", password="password123", pseudo=None):
    return await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "confirm_password": password,
            "firstname": "Ada",
            "lastname": "Lovelace",
            "pseudo": pseudo or email.split("@")[0],
            "date_of_birth": "2005-01-01",
        },
    )


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


async def test_register_with_school_name_succeeds(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "firstname": "Ada",
            "lastname": "Lovelace",
            "pseudo": "student",
            "date_of_birth": "2005-01-01",
            "school_name": "Lycée Victor Hugo",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["school_name"] == "Lycée Victor Hugo"
    assert body["pseudo"] == "student"


async def test_login_wrong_password_rejected(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401


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
