import json

from app.api.v1 import deps
from tests.unit.fakes import FakeLLMProvider

_SAMPLE_TEXT = ("Ohm's law relates voltage, current, and resistance in a circuit: V = I * R. " * 20).encode(
    "utf-8"
)

_TWO_MCQ_RESPONSE = json.dumps(
    {
        "questions": [
            {"type": "mcq", "question": "V = ?", "options": ["I*R", "I+R"], "correct_answer": "I*R",
             "explanation": "Ohm's law", "points": 1, "difficulty": "easy", "concept_name": None},
            {"type": "mcq", "question": "Unit of resistance?", "options": ["Ohm", "Volt"], "correct_answer": "Ohm",
             "explanation": "Resistance is in ohms", "points": 1, "difficulty": "easy", "concept_name": None},
        ]
    }
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


def _override_llm(client, *, response):
    client.app.dependency_overrides[deps.get_llm_provider] = lambda: FakeLLMProvider(response=response)


async def test_generate_exam_sets_kind_and_exam_params(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_llm(client, response=_TWO_MCQ_RESPONSE)

    resp = await client.post(
        f"/api/v1/subjects/{subject_id}/exams/generate",
        headers=headers,
        json={"document_id": document_id, "duration_minutes": 60, "style": "past-exam"},
    )
    assert resp.status_code == 200
    exam = resp.json()
    assert exam["kind"] == "exam"
    assert exam["duration_minutes"] == 60
    assert exam["style"] == "past-exam"

    # An exam's id is a quiz id — the regular quiz attempt endpoints work on it.
    attempt_resp = await client.post(f"/api/v1/quizzes/{exam['id']}/attempts", headers=headers)
    assert attempt_resp.status_code == 201


async def test_exam_history_lists_this_users_attempts(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_llm(client, response=_TWO_MCQ_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/exams/generate", headers=headers, json={"document_id": document_id},
    )
    exam_id = gen_resp.json()["id"]

    attempt_resp = await client.post(f"/api/v1/quizzes/{exam_id}/attempts", headers=headers)
    attempt_id = attempt_resp.json()["id"]
    await client.post(f"/api/v1/quiz-attempts/{attempt_id}/submit", headers=headers)

    history_resp = await client.get(f"/api/v1/exams/{exam_id}/history", headers=headers)
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["id"] == attempt_id
    assert history[0]["completed_at"] is not None


async def test_exam_history_excludes_other_users_attempts(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)
    document_id = await _upload_and_ingest(client, alice_headers, subject_id)
    _override_llm(client, response=_TWO_MCQ_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/exams/generate", headers=alice_headers, json={"document_id": document_id},
    )
    exam_id = gen_resp.json()["id"]

    history_resp = await client.get(f"/api/v1/exams/{exam_id}/history", headers=bob_headers)
    assert history_resp.status_code == 404  # bob doesn't own the subject this exam belongs to


async def test_generate_exam_requires_auth(client):
    resp = await client.post("/api/v1/subjects/some-id/exams/generate", json={"document_id": "doc-1"})
    assert resp.status_code == 403
