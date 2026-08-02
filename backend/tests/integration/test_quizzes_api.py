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


def _override_llm(client, *, response=None, responses=None):
    client.app.dependency_overrides[deps.get_llm_provider] = lambda: FakeLLMProvider(
        response=response, responses=responses
    )


async def test_generate_and_get_quiz(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_llm(client, response=_TWO_MCQ_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/quizzes/generate", headers=headers, json={"document_id": document_id},
    )
    assert gen_resp.status_code == 200
    quiz = gen_resp.json()
    assert quiz["kind"] == "quiz"
    assert len(quiz["questions"]) == 2
    # correct_answer/explanation must never be exposed before an attempt is submitted
    assert "correct_answer" not in quiz["questions"][0]
    assert "explanation" not in quiz["questions"][0]

    get_resp = await client.get(f"/api/v1/quizzes/{quiz['id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == quiz["id"]


async def test_full_attempt_flow_scores_correctly(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_llm(client, response=_TWO_MCQ_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/quizzes/generate", headers=headers, json={"document_id": document_id},
    )
    quiz = gen_resp.json()
    questions = quiz["questions"]

    attempt_resp = await client.post(f"/api/v1/quizzes/{quiz['id']}/attempts", headers=headers)
    assert attempt_resp.status_code == 201
    attempt = attempt_resp.json()
    assert attempt["score"] is None

    ans1 = await client.post(
        f"/api/v1/quiz-attempts/{attempt['id']}/answers", headers=headers,
        json={"question_id": questions[0]["id"], "answer": "I*R"},
    )
    assert ans1.status_code == 200
    assert "is_correct" not in ans1.json()  # withheld until submit

    await client.post(
        f"/api/v1/quiz-attempts/{attempt['id']}/answers", headers=headers,
        json={"question_id": questions[1]["id"], "answer": "Volt"},
    )

    submit_resp = await client.post(f"/api/v1/quiz-attempts/{attempt['id']}/submit", headers=headers)
    assert submit_resp.status_code == 200
    result = submit_resp.json()
    assert result["score"] == 50.0
    assert result["completed_at"] is not None
    by_id = {a["question_id"]: a for a in result["answers"]}
    assert by_id[questions[0]["id"]]["is_correct"] is True
    assert by_id[questions[1]["id"]]["is_correct"] is False
    assert by_id[questions[1]["id"]]["correct_answer"] == "Ohm"


async def test_submitting_answer_after_attempt_submitted_fails(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    document_id = await _upload_and_ingest(client, headers, subject_id)
    _override_llm(client, response=_TWO_MCQ_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/quizzes/generate", headers=headers, json={"document_id": document_id},
    )
    quiz = gen_resp.json()
    attempt = (await client.post(f"/api/v1/quizzes/{quiz['id']}/attempts", headers=headers)).json()

    await client.post(f"/api/v1/quiz-attempts/{attempt['id']}/submit", headers=headers)

    resp = await client.post(
        f"/api/v1/quiz-attempts/{attempt['id']}/answers", headers=headers,
        json={"question_id": quiz["questions"][0]["id"], "answer": "I*R"},
    )
    assert resp.status_code == 409

    resp2 = await client.post(f"/api/v1/quiz-attempts/{attempt['id']}/submit", headers=headers)
    assert resp2.status_code == 409


async def test_quiz_isolated_between_users(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)
    document_id = await _upload_and_ingest(client, alice_headers, subject_id)
    _override_llm(client, response=_TWO_MCQ_RESPONSE)

    gen_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/quizzes/generate", headers=alice_headers, json={"document_id": document_id},
    )
    quiz_id = gen_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/quizzes/{quiz_id}", headers=bob_headers)
    assert get_resp.status_code == 404

    attempt_resp = await client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=bob_headers)
    assert attempt_resp.status_code == 404


async def test_generate_requires_auth(client):
    resp = await client.post("/api/v1/subjects/some-id/quizzes/generate", json={"document_id": "doc-1"})
    assert resp.status_code == 403


async def test_get_quiz_requires_auth(client):
    resp = await client.get("/api/v1/quizzes/some-id")
    assert resp.status_code == 403
