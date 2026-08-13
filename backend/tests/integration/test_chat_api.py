"""End-to-end chat API tests against the real Postgres+pgvector fixture
(pg_client) — the only way to genuinely exercise EmbeddingRepository.search()
through the full HTTP stack rather than against fakes. RAG orchestration
logic itself (query rewriting, RRF, reranking) is already covered by fast
fake-backed unit tests in tests/unit/test_chat_service.py; these tests exist
to prove the wiring (auth, ownership, DB persistence, response schemas) is
correct end to end.
"""
import json

import pytest

from app.api.v1 import deps
from app.core.config import settings
from tests.unit.fakes import FakeEmbeddingProvider, FakeLLMProvider

_SAMPLE_TEXT = ("Ohm's law relates voltage, current, and resistance in a circuit: V = I * R. " * 20).encode(
    "utf-8"
)


@pytest.fixture(autouse=True)
def _disable_rerank():
    """The sample document above chunks into more pieces than the default
    rag_final_context_chunks, which would otherwise make rerank() issue an
    extra LLM call — turning the exact number of FakeLLMProvider responses
    each test needs into a fragile function of chunk counts. Reranking's own
    behavior is already covered by tests/unit/test_rerank.py and
    test_chat_service.py; these tests are about the HTTP/DB wiring."""
    original = settings.rag_enable_rerank
    settings.rag_enable_rerank = False
    yield
    settings.rag_enable_rerank = original


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


def _override_chat_llm(client, *, responses):
    """Chat's answer-generation LLM goes through deps.get_llm_provider;
    condense/expand/rerank go through deps.get_simple_llm_provider (see
    app/api/v1/deps.py) — both point at the same FakeLLMProvider instance so
    its single ordered `responses` queue is consumed in actual call order
    regardless of which one issues each call, matching every test below that
    asserts on that order. Separate from the fake wired into ingestion by the
    pg_client fixture — override it per-test so each test controls exactly
    what the "model" says back."""
    fake = FakeLLMProvider(responses=list(responses))
    client.app.dependency_overrides[deps.get_llm_provider] = lambda: fake
    client.app.dependency_overrides[deps.get_simple_llm_provider] = lambda: fake
    client.app.dependency_overrides[deps.get_embedding_provider] = lambda: FakeEmbeddingProvider(
        dimension=settings.embedding_dimension
    )


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


_EXPAND_RESPONSE = json.dumps({"hypothetical_answer": "V = I * R.", "variations": ["Ohm's law formula"]})


async def test_chat_answers_with_citation_to_ingested_document(pg_client):
    headers = await _register_and_login(pg_client, "alice@example.com")
    subject_id = await _create_subject(pg_client, headers)
    await _upload_and_ingest(pg_client, headers, subject_id)
    _override_chat_llm(pg_client, responses=[_EXPAND_RESPONSE, "Ohm's law states V = I * R [1]."])

    resp = await pg_client.post(
        f"/api/v1/subjects/{subject_id}/chat", headers=headers, json={"question": "What is Ohm's law?"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["assistant_message"]["content"] == "Ohm's law states V = I * R [1]."
    assert len(body["assistant_message"]["citations"]) >= 1
    assert body["assistant_message"]["citations"][0]["document_filename"] == "ohms_law.txt"
    assert body["user_message"]["content"] == "What is Ohm's law?"
    assert body["conversation_id"]


async def test_chat_requires_auth(pg_client):
    resp = await pg_client.post("/api/v1/subjects/some-id/chat", json={"question": "hi"})
    assert resp.status_code == 403  # HTTPBearer rejects missing credentials before the route runs


async def test_chat_rejects_other_users_subject(pg_client):
    alice_headers = await _register_and_login(pg_client, "alice@example.com")
    bob_headers = await _register_and_login(pg_client, "bob@example.com")
    subject_id = await _create_subject(pg_client, alice_headers)
    _override_chat_llm(pg_client, responses=[_EXPAND_RESPONSE, "answer"])

    resp = await pg_client.post(
        f"/api/v1/subjects/{subject_id}/chat", headers=bob_headers, json={"question": "hi"}
    )

    assert resp.status_code == 404


async def test_list_conversations_and_messages_round_trip(pg_client):
    headers = await _register_and_login(pg_client, "alice@example.com")
    subject_id = await _create_subject(pg_client, headers)
    await _upload_and_ingest(pg_client, headers, subject_id)
    _override_chat_llm(pg_client, responses=[_EXPAND_RESPONSE, "Ohm's law states V = I * R [1]."])

    chat_resp = await pg_client.post(
        f"/api/v1/subjects/{subject_id}/chat", headers=headers, json={"question": "What is Ohm's law?"}
    )
    conversation_id = chat_resp.json()["conversation_id"]

    conversations_resp = await pg_client.get(f"/api/v1/subjects/{subject_id}/conversations", headers=headers)
    assert conversations_resp.status_code == 200
    assert any(c["id"] == conversation_id for c in conversations_resp.json())

    messages_resp = await pg_client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=headers)
    assert messages_resp.status_code == 200
    messages = messages_resp.json()
    assert [m["role"] for m in messages] == ["user", "assistant"]


async def test_messages_isolated_between_users(pg_client):
    alice_headers = await _register_and_login(pg_client, "alice@example.com")
    bob_headers = await _register_and_login(pg_client, "bob@example.com")
    subject_id = await _create_subject(pg_client, alice_headers)
    await _upload_and_ingest(pg_client, alice_headers, subject_id)
    _override_chat_llm(pg_client, responses=[_EXPAND_RESPONSE, "answer"])

    chat_resp = await pg_client.post(
        f"/api/v1/subjects/{subject_id}/chat", headers=alice_headers, json={"question": "q"}
    )
    conversation_id = chat_resp.json()["conversation_id"]

    resp = await pg_client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=bob_headers)
    assert resp.status_code == 404


async def test_chat_continues_existing_conversation(pg_client):
    headers = await _register_and_login(pg_client, "alice@example.com")
    subject_id = await _create_subject(pg_client, headers)
    await _upload_and_ingest(pg_client, headers, subject_id)
    _override_chat_llm(
        pg_client,
        responses=[_EXPAND_RESPONSE, "first answer", "second condensed question", _EXPAND_RESPONSE, "second answer"],
    )

    first = await pg_client.post(
        f"/api/v1/subjects/{subject_id}/chat", headers=headers, json={"question": "What is Ohm's law?"}
    )
    conversation_id = first.json()["conversation_id"]

    second = await pg_client.post(
        f"/api/v1/subjects/{subject_id}/chat",
        headers=headers,
        json={"question": "explain it differently", "conversation_id": conversation_id},
    )

    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id

    messages_resp = await pg_client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=headers)
    assert len(messages_resp.json()) == 4
