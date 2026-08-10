async def _register_and_login(client, email):
    pseudo = email.split("@")[0]
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
            "firstname": "A",
            "lastname": "B",
            "pseudo": pseudo,
            "date_of_birth": "2005-01-01",
        },
    )
    login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_list_get_subject(client):
    headers = await _register_and_login(client, "alice@example.com")

    create_resp = await client.post("/api/v1/subjects", json={"name": "Mathematics"}, headers=headers)
    assert create_resp.status_code == 201
    subject_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/subjects", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    get_resp = await client.get(f"/api/v1/subjects/{subject_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Mathematics"


async def test_duplicate_subject_name_rejected(client):
    headers = await _register_and_login(client, "alice@example.com")
    await client.post("/api/v1/subjects", json={"name": "Mathematics"}, headers=headers)
    resp = await client.post("/api/v1/subjects", json={"name": "Mathematics"}, headers=headers)
    assert resp.status_code == 409


async def test_subjects_are_isolated_between_users(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")

    create_resp = await client.post("/api/v1/subjects", json={"name": "Physics"}, headers=alice_headers)
    subject_id = create_resp.json()["id"]

    bob_get_resp = await client.get(f"/api/v1/subjects/{subject_id}", headers=bob_headers)
    assert bob_get_resp.status_code == 404

    bob_list_resp = await client.get("/api/v1/subjects", headers=bob_headers)
    assert bob_list_resp.json() == []


async def test_update_and_archive_subject(client):
    headers = await _register_and_login(client, "alice@example.com")
    create_resp = await client.post("/api/v1/subjects", json={"name": "Physics"}, headers=headers)
    subject_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/subjects/{subject_id}", json={"description": "Mechanics"}, headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Mechanics"

    archive_resp = await client.delete(f"/api/v1/subjects/{subject_id}", headers=headers)
    assert archive_resp.status_code == 204

    list_resp = await client.get("/api/v1/subjects", headers=headers)
    assert list_resp.json() == []
