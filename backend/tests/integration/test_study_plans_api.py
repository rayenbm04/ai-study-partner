"""Integration tests for the study-plan (Planning Engine) API.

Auth/ownership/empty-state checks run against the standard SQLite `client`
fixture. The one test that generates a real plan uses `pg_client` purely to
seed a concept directly via a DB session — same reasoning as
test_progress_api.py: concepts are only ever created by the ingestion
pipeline's concept tagger, and there's no public "create concept" endpoint.
"""
from app.repositories.concept_repo import SqlAlchemyConceptRepository


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


async def _create_subject(client, headers, name="Physics"):
    resp = await client.post("/api/v1/subjects", json={"name": name}, headers=headers)
    return resp.json()["id"]


async def test_generate_study_plan_requires_auth(client):
    resp = await client.post("/api/v1/study-plans", json={"name": "Plan", "subject_ids": ["some-id"]})
    assert resp.status_code == 403


async def test_generate_study_plan_404s_for_subject_not_owned(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)

    resp = await client.post(
        "/api/v1/study-plans", headers=bob_headers, json={"name": "Plan", "subject_ids": [subject_id]}
    )
    assert resp.status_code == 404


async def test_generate_study_plan_400s_when_subject_has_no_concepts(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)

    resp = await client.post(
        "/api/v1/study-plans", headers=headers, json={"name": "Plan", "subject_ids": [subject_id]}
    )
    assert resp.status_code == 400


async def test_get_study_plan_requires_auth(client):
    resp = await client.get("/api/v1/study-plans/some-id")
    assert resp.status_code == 403


async def test_get_study_plan_404s_for_unknown_id(client):
    headers = await _register_and_login(client, "alice@example.com")

    resp = await client.get("/api/v1/study-plans/nonexistent", headers=headers)
    assert resp.status_code == 404


async def test_update_study_plan_item_404s_for_unknown_item(client):
    headers = await _register_and_login(client, "alice@example.com")

    resp = await client.patch("/api/v1/study-plan-items/nonexistent", headers=headers, json={"status": "done"})
    assert resp.status_code == 404


async def test_generate_get_and_update_study_plan_end_to_end(pg_client):
    headers = await _register_and_login(pg_client, "alice@example.com")
    subject_id = await _create_subject(pg_client, headers)

    async with pg_client.test_sessionmaker() as session:
        concept_repo = SqlAlchemyConceptRepository(session)
        await concept_repo.create(subject_id=subject_id, name="Ohm's Law", description=None)
        await session.commit()

    gen_resp = await pg_client.post(
        "/api/v1/study-plans",
        headers=headers,
        json={"name": "Exam Prep", "subject_ids": [subject_id], "daily_minutes_available": 30},
    )
    assert gen_resp.status_code == 201
    plan = gen_resp.json()
    assert plan["name"] == "Exam Prep"
    assert len(plan["items"]) > 0
    item_id = plan["items"][0]["id"]

    get_resp = await pg_client.get(f"/api/v1/study-plans/{plan['id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == plan["id"]

    other_headers = await _register_and_login(pg_client, "bob@example.com")
    forbidden_resp = await pg_client.get(f"/api/v1/study-plans/{plan['id']}", headers=other_headers)
    assert forbidden_resp.status_code == 404

    update_resp = await pg_client.patch(
        f"/api/v1/study-plan-items/{item_id}", headers=headers, json={"status": "done"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "done"

    invalid_status_resp = await pg_client.patch(
        f"/api/v1/study-plan-items/{item_id}", headers=headers, json={"status": "bogus"}
    )
    assert invalid_status_resp.status_code == 400

    forbidden_update_resp = await pg_client.patch(
        f"/api/v1/study-plan-items/{item_id}", headers=other_headers, json={"status": "done"}
    )
    assert forbidden_update_resp.status_code == 404
