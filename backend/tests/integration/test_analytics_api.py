"""Integration tests for the Analytics Engine API — a pure read-side
aggregation layer, so the standard SQLite `client` fixture is enough for
every case here (no pgvector search involved).

get_analytics_service's DI chain pulls in get_flashcard_service (analytics
reuses FlashcardService.list_due for the due-card count), which in turn
depends on get_simple_llm_provider — FastAPI resolves the whole chain even
for routes that never call generate(), so every test here needs the same
FakeLLMProvider override the flashcard/quiz API tests use, or building the
real Gemini provider blows up on a missing API key. get_llm_provider is
overridden too since it's cheap insurance against another route in this
chain picking it up later.
"""
from app.api.v1 import deps
from tests.unit.fakes import FakeLLMProvider


async def _register_and_login(client, email):
    fake = FakeLLMProvider()
    client.app.dependency_overrides[deps.get_llm_provider] = lambda: fake
    client.app.dependency_overrides[deps.get_simple_llm_provider] = lambda: fake
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


async def test_overview_requires_auth(client):
    resp = await client.get("/api/v1/analytics/overview")
    assert resp.status_code == 403


async def test_subject_analytics_requires_auth(client):
    resp = await client.get("/api/v1/analytics/subjects/some-id")
    assert resp.status_code == 403


async def test_overview_with_no_subjects_returns_zeros(client):
    headers = await _register_and_login(client, "alice@example.com")

    resp = await client.get("/api/v1/analytics/overview", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body == {"subject_count": 0, "total_flashcards_due": 0, "subjects": []}


async def test_subject_analytics_404s_for_subject_not_owned(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)

    resp = await client.get(f"/api/v1/analytics/subjects/{subject_id}", headers=bob_headers)
    assert resp.status_code == 404


async def test_subject_analytics_on_empty_subject(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)

    resp = await client.get(f"/api/v1/analytics/subjects/{subject_id}", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["subject_id"] == subject_id
    assert body["document_count"] == 0
    assert body["flashcard_count"] == 0
    assert body["average_quiz_score"] is None
    assert body["average_mastery"] is None
    assert body["concepts_total"] == 0


async def test_overview_reflects_created_subject(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)

    resp = await client.get("/api/v1/analytics/overview", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["subject_count"] == 1
    assert body["subjects"][0]["subject_id"] == subject_id
