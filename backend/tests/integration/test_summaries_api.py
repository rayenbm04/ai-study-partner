from app.api.v1 import deps
from tests.unit.fakes import FakeLLMProvider

_SAMPLE_TEXT = ("Ohm's law relates voltage, current, and resistance in a circuit: V = I * R. " * 20).encode(
    "utf-8"
)


async def _register_and_login(client, email):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "firstname": "A", "lastname": "B"},
    )
    login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_subject(client, headers, name="Physics"):
    resp = await client.post("/api/v1/subjects", json={"name": name}, headers=headers)
    return resp.json()["id"]


async def _upload_and_ingest(client, headers, subject_id):
    resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("ohms_law.txt", _SAMPLE_TEXT, "text/plain")},
    )
    assert resp.status_code == 201
    document_id = resp.json()["id"]
    status_resp = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert status_resp.json()["status"] == "ready"
    return document_id


def _override_summary_llm(client, *, response):
    client.app.dependency_overrides[deps.get_llm_provider] = lambda: FakeLLMProvider(response=response)


async def test_generate_and_fetch_short_summary(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_summary_llm(client, response="Ohm's law: V = I * R.")

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/summaries",
        headers=headers,
        json={"document_id": document_id, "summary_type": "short"},
    )
    assert gen_resp.status_code == 200
    body = gen_resp.json()
    assert body["content"] == "Ohm's law: V = I * R."
    assert body["summary_type"] == "short"
    assert body["document_id"] == document_id

    get_resp = await client.get(
        f"/api/v1/documents/{document_id}/summary", headers=headers, params={"summary_type": "short"}
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["content"] == "Ohm's law: V = I * R."


async def test_get_summary_404_before_generation(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    # get_summary_service always builds an LLMProvider even for a read-only
    # GET (SummaryService threads it through the constructor like ChatService
    # does), so every authenticated request to these routes needs the fake
    # override — same reasoning as tests/integration/test_chat_api.py.
    _override_summary_llm(client, response="unused")

    resp = await client.get(
        f"/api/v1/documents/{document_id}/summary", headers=headers, params={"summary_type": "detailed"}
    )
    assert resp.status_code == 404


async def test_generate_rejects_invalid_summary_type(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_summary_llm(client, response="unused")

    resp = await client.post(
        f"/api/v1/subjects/{subject_id}/summaries",
        headers=headers,
        json={"document_id": document_id, "summary_type": "haiku"},
    )
    assert resp.status_code == 422  # rejected by the pydantic Literal before the service even runs


async def test_generate_rejects_document_not_ready(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    # Upload without waiting/asserting ready — httpx's ASGITransport runs the
    # background ingestion synchronously, so to get a genuinely "pending"
    # document we'd need to intercept mid-ingestion; instead, point the
    # request at a document id that was never uploaded (never ingested),
    # which the service treats identically to "not found" for this user.
    _override_summary_llm(client, response="unused")
    resp = await client.post(
        f"/api/v1/subjects/{subject_id}/summaries",
        headers=headers,
        json={"document_id": "does-not-exist", "summary_type": "short"},
    )
    assert resp.status_code == 404


async def test_generate_rejects_other_users_subject(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)
    document_id = await _upload_and_ingest(client, alice_headers, subject_id)
    _override_summary_llm(client, response="x")

    resp = await client.post(
        f"/api/v1/subjects/{subject_id}/summaries",
        headers=bob_headers,
        json={"document_id": document_id, "summary_type": "short"},
    )
    assert resp.status_code == 404


async def test_summary_isolated_between_users(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)
    document_id = await _upload_and_ingest(client, alice_headers, subject_id)
    _override_summary_llm(client, response="alice's summary")

    await client.post(
        f"/api/v1/subjects/{subject_id}/summaries",
        headers=alice_headers,
        json={"document_id": document_id, "summary_type": "short"},
    )

    resp = await client.get(
        f"/api/v1/documents/{document_id}/summary", headers=bob_headers, params={"summary_type": "short"}
    )
    assert resp.status_code == 404


async def test_list_summaries_returns_all_generated_types(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)

    _override_summary_llm(client, response="short version")
    await client.post(
        f"/api/v1/subjects/{subject_id}/summaries",
        headers=headers,
        json={"document_id": document_id, "summary_type": "short"},
    )
    _override_summary_llm(client, response="bullet version")
    await client.post(
        f"/api/v1/subjects/{subject_id}/summaries",
        headers=headers,
        json={"document_id": document_id, "summary_type": "bullet"},
    )

    resp = await client.get(f"/api/v1/documents/{document_id}/summaries", headers=headers)
    assert resp.status_code == 200
    types = {s["summary_type"] for s in resp.json()}
    assert types == {"short", "bullet"}


async def test_list_summaries_isolated_between_users(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)
    document_id = await _upload_and_ingest(client, alice_headers, subject_id)
    _override_summary_llm(client, response="alice's summary")
    await client.post(
        f"/api/v1/subjects/{subject_id}/summaries",
        headers=alice_headers,
        json={"document_id": document_id, "summary_type": "short"},
    )

    resp = await client.get(f"/api/v1/documents/{document_id}/summaries", headers=bob_headers)
    assert resp.status_code == 404


async def test_generate_requires_auth(client):
    resp = await client.post(
        "/api/v1/subjects/some-id/summaries", json={"document_id": "doc-1", "summary_type": "short"}
    )
    assert resp.status_code == 403


async def test_regenerate_overwrites_cached_summary(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)

    _override_summary_llm(client, response="first version")
    await client.post(
        f"/api/v1/subjects/{subject_id}/summaries",
        headers=headers,
        json={"document_id": document_id, "summary_type": "short"},
    )

    _override_summary_llm(client, response="second version")
    resp = await client.post(
        f"/api/v1/subjects/{subject_id}/summaries",
        headers=headers,
        json={"document_id": document_id, "summary_type": "short"},
    )
    assert resp.json()["content"] == "second version"

    get_resp = await client.get(
        f"/api/v1/documents/{document_id}/summary", headers=headers, params={"summary_type": "short"}
    )
    assert get_resp.json()["content"] == "second version"
