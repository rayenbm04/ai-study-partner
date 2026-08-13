import json

from app.api.v1 import deps
from tests.unit.fakes import FakeLLMProvider

_SAMPLE_TEXT = ("Ohm's law relates voltage, current, and resistance in a circuit: V = I * R. " * 20).encode(
    "utf-8"
)

_TWO_CARDS_RESPONSE = json.dumps(
    {
        "flashcards": [
            {"question": "What is Ohm's law?", "answer": "V = I * R", "difficulty": "easy",
             "concept_name": None, "tags": ["circuits"]},
            {"question": "What does V stand for?", "answer": "Voltage", "difficulty": "easy",
             "concept_name": None, "tags": ["circuits"]},
        ]
    }
)


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


def _override_flashcard_llm(client, *, response):
    # FlashcardService now runs on get_simple_llm_provider (mechanical
    # extraction — see app/api/v1/deps.py) — get_llm_provider is overridden
    # too since nothing here cares which one flashcard generation uses.
    fake = FakeLLMProvider(response=response)
    client.app.dependency_overrides[deps.get_llm_provider] = lambda: fake
    client.app.dependency_overrides[deps.get_simple_llm_provider] = lambda: fake


async def test_generate_and_list_flashcards(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_flashcard_llm(client, response=_TWO_CARDS_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/flashcards/generate",
        headers=headers,
        json={"document_id": document_id},
    )
    assert gen_resp.status_code == 200
    cards = gen_resp.json()
    assert len(cards) == 2
    assert cards[0]["question"] == "What is Ohm's law?"
    assert cards[0]["source"] == "generated"
    assert cards[0]["review"] is None

    list_resp = await client.get(f"/api/v1/subjects/{subject_id}/flashcards", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2


async def test_review_flashcard_updates_sm2_state(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_flashcard_llm(client, response=_TWO_CARDS_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/flashcards/generate",
        headers=headers,
        json={"document_id": document_id},
    )
    flashcard_id = gen_resp.json()[0]["id"]

    review_resp = await client.post(
        f"/api/v1/flashcards/{flashcard_id}/review", headers=headers, json={"quality": 5}
    )
    assert review_resp.status_code == 200
    body = review_resp.json()
    assert body["repetitions"] == 1
    assert body["interval_days"] == 1
    assert body["last_grade"] == 5


async def test_review_rejects_out_of_range_quality(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_flashcard_llm(client, response=_TWO_CARDS_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/flashcards/generate",
        headers=headers,
        json={"document_id": document_id},
    )
    flashcard_id = gen_resp.json()[0]["id"]

    resp = await client.post(f"/api/v1/flashcards/{flashcard_id}/review", headers=headers, json={"quality": 9})
    assert resp.status_code == 422


async def test_review_unknown_flashcard_404s(client):
    headers = await _register_and_login(client, "alice@example.com")
    _override_flashcard_llm(client, response="unused")

    resp = await client.post(
        "/api/v1/flashcards/does-not-exist/review", headers=headers, json={"quality": 4}
    )
    assert resp.status_code == 404


async def test_flashcards_isolated_between_users(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)
    document_id = await _upload_and_ingest(client, alice_headers, subject_id)
    _override_flashcard_llm(client, response=_TWO_CARDS_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/flashcards/generate",
        headers=alice_headers,
        json={"document_id": document_id},
    )
    flashcard_id = gen_resp.json()[0]["id"]

    list_resp = await client.get(f"/api/v1/subjects/{subject_id}/flashcards", headers=bob_headers)
    assert list_resp.status_code == 404

    review_resp = await client.post(
        f"/api/v1/flashcards/{flashcard_id}/review", headers=bob_headers, json={"quality": 4}
    )
    assert review_resp.status_code == 404


async def test_due_endpoint_lists_new_cards_across_subjects(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_flashcard_llm(client, response=_TWO_CARDS_RESPONSE)

    await client.post(
        f"/api/v1/subjects/{subject_id}/flashcards/generate", headers=headers, json={"document_id": document_id}
    )

    due_resp = await client.get("/api/v1/flashcards/due", headers=headers)
    assert due_resp.status_code == 200
    assert len(due_resp.json()) == 2


async def test_due_endpoint_excludes_just_reviewed_cards(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_flashcard_llm(client, response=_TWO_CARDS_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/flashcards/generate", headers=headers, json={"document_id": document_id}
    )
    flashcard_id = gen_resp.json()[0]["id"]

    await client.post(f"/api/v1/flashcards/{flashcard_id}/review", headers=headers, json={"quality": 5})

    due_resp = await client.get("/api/v1/flashcards/due", headers=headers)
    due_ids = {card["id"] for card in due_resp.json()}
    assert flashcard_id not in due_ids


async def test_generate_requires_auth(client):
    resp = await client.post(
        "/api/v1/subjects/some-id/flashcards/generate", json={"document_id": "doc-1"}
    )
    assert resp.status_code == 403


async def test_due_requires_auth(client):
    resp = await client.get("/api/v1/flashcards/due")
    assert resp.status_code == 403
