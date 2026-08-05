_SAMPLE_TEXT = ("Ohm's law relates voltage, current, and resistance in a circuit. " * 20).encode("utf-8")


async def _register_and_login(client, email):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "firstname": "A", "lastname": "B"},
    )
    login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_reset_deletes_subjects_and_documents_but_keeps_login(client):
    headers = await _register_and_login(client, "alice@example.com")
    create_resp = await client.post("/api/v1/subjects", json={"name": "Physics"}, headers=headers)
    subject_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("notes.txt", _SAMPLE_TEXT, "text/plain")},
    )

    reset_resp = await client.post("/api/v1/account/reset", headers=headers)
    assert reset_resp.status_code == 204

    list_resp = await client.get("/api/v1/subjects", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json() == []

    # the account itself still works — reset clears data, not the login
    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "password123"}
    )
    assert login_resp.status_code == 200


async def test_reset_does_not_affect_other_users(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    await client.post("/api/v1/subjects", json={"name": "Physics"}, headers=alice_headers)
    await client.post("/api/v1/subjects", json={"name": "Chemistry"}, headers=bob_headers)

    await client.post("/api/v1/account/reset", headers=alice_headers)

    bob_subjects = await client.get("/api/v1/subjects", headers=bob_headers)
    assert len(bob_subjects.json()) == 1


async def test_reset_requires_auth(client):
    resp = await client.post("/api/v1/account/reset")
    assert resp.status_code == 403
