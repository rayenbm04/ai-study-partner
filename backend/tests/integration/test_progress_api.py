"""Integration tests for the progress engine API.

Auth/ownership/empty-state checks run against the standard SQLite `client`
fixture. One deeper test runs against `pg_client` purely to reuse its
exposed `test_sessionmaker` — real evidence requires a concept that a
flashcard/quiz question can be tagged to, and concepts are only ever created
by the ingestion pipeline's concept tagger (no public "create concept"
endpoint exists), so that test seeds one directly via the same DB session
the API is using, rather than fighting ingestion's own fixed concept-tagging
LLM response (concept tagging itself is already covered by
test_concept_tagger.py).
"""
import json

from app.api.v1 import deps
from app.repositories.chunk_repo import SqlAlchemyChunkRepository
from app.repositories.concept_chunk_repo import SqlAlchemyConceptChunkRepository
from app.repositories.concept_repo import SqlAlchemyConceptRepository
from tests.unit.fakes import FakeLLMProvider

_SAMPLE_TEXT = ("Ohm's law relates voltage, current, and resistance in a circuit: V = I * R. " * 20).encode(
    "utf-8"
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


async def test_progress_empty_subject_returns_empty_list(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)

    resp = await client.get(f"/api/v1/subjects/{subject_id}/progress", headers=headers)

    assert resp.status_code == 200
    assert resp.json() == []


async def test_weak_concepts_empty_subject_returns_empty_list(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)

    resp = await client.get(f"/api/v1/subjects/{subject_id}/weak-concepts", headers=headers)

    assert resp.status_code == 200
    assert resp.json() == []


async def test_progress_requires_auth(client):
    resp = await client.get("/api/v1/subjects/some-id/progress")
    assert resp.status_code == 403


async def test_weak_concepts_requires_auth(client):
    resp = await client.get("/api/v1/subjects/some-id/weak-concepts")
    assert resp.status_code == 403


async def test_progress_404s_for_subject_not_owned(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)

    resp = await client.get(f"/api/v1/subjects/{subject_id}/progress", headers=bob_headers)
    assert resp.status_code == 404


async def test_weak_concepts_404s_for_subject_not_owned(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)

    resp = await client.get(f"/api/v1/subjects/{subject_id}/weak-concepts", headers=bob_headers)
    assert resp.status_code == 404


_ONE_FLASHCARD_RESPONSE = json.dumps(
    {
        "flashcards": [
            {"question": "What is Ohm's law?", "answer": "V = I * R", "difficulty": "easy",
             "concept_name": "Ohm's Law", "tags": []},
        ]
    }
)

_THREE_MCQ_RESPONSE = json.dumps(
    {
        "questions": [
            {"type": "mcq", "question": f"V = ? ({i})", "options": ["I*R", "I+R"], "correct_answer": "I*R",
             "explanation": "Ohm's law", "points": 1, "difficulty": "easy", "concept_name": "Ohm's Law"}
            for i in range(3)
        ]
    }
)


async def test_progress_and_weak_concepts_reflect_real_evidence(pg_client):
    headers = await _register_and_login(pg_client, "alice@example.com")
    subject_id = await _create_subject(pg_client, headers)
    document_id = await _upload_and_ingest(pg_client, headers, subject_id)

    async with pg_client.test_sessionmaker() as session:
        concept_repo = SqlAlchemyConceptRepository(session)
        concept = await concept_repo.create(subject_id=subject_id, name="Ohm's Law", description=None)
        # Flashcard/quiz generation only resolve a concept_name against concepts
        # already tagged to *this document* (list_by_document, joined through
        # concept_chunks) — link the seeded concept to one of the document's
        # chunks so it's actually visible to the generator, same as a real
        # concept-tagging pass would have done.
        chunks = await SqlAlchemyChunkRepository(session).list_by_document(document_id)
        await SqlAlchemyConceptChunkRepository(session).link(concept_id=concept.id, chunk_id=chunks[0].id, relevance=1.0)
        await session.commit()

    # FlashcardService/QuizService.generate() run on get_simple_llm_provider
    # (see app/api/v1/deps.py) — get_llm_provider is overridden too since
    # QuizService still resolves it for grading, even though this test's
    # mcq questions are graded by exact match, no LLM call.
    flashcard_llm = FakeLLMProvider(response=_ONE_FLASHCARD_RESPONSE)
    pg_client.app.dependency_overrides[deps.get_llm_provider] = lambda: flashcard_llm
    pg_client.app.dependency_overrides[deps.get_simple_llm_provider] = lambda: flashcard_llm
    gen_resp = await pg_client.post(
        f"/api/v1/subjects/{subject_id}/flashcards/generate", headers=headers, json={"document_id": document_id}
    )
    assert gen_resp.status_code == 200
    flashcard_id = gen_resp.json()[0]["id"]
    assert gen_resp.json()[0]["concept_id"] == concept.id

    review_resp = await pg_client.post(  # perfect recall -> quality 5
        f"/api/v1/flashcards/{flashcard_id}/review", headers=headers, json={"quality": 5}
    )
    assert review_resp.status_code == 200

    quiz_llm = FakeLLMProvider(response=_THREE_MCQ_RESPONSE)
    pg_client.app.dependency_overrides[deps.get_llm_provider] = lambda: quiz_llm
    pg_client.app.dependency_overrides[deps.get_simple_llm_provider] = lambda: quiz_llm
    quiz_resp = await pg_client.post(
        f"/api/v1/subjects/{subject_id}/quizzes/generate", headers=headers, json={"document_id": document_id}
    )
    assert quiz_resp.status_code == 200
    quiz = quiz_resp.json()
    assert len(quiz["questions"]) == 3
    assert quiz["questions"][0]["concept_id"] == concept.id

    attempt = (await pg_client.post(f"/api/v1/quizzes/{quiz['id']}/attempts", headers=headers)).json()
    answers = ["I*R", "I+R", "I+R"]  # one right, two wrong
    for question, answer in zip(quiz["questions"], answers):
        await pg_client.post(
            f"/api/v1/quiz-attempts/{attempt['id']}/answers", headers=headers,
            json={"question_id": question["id"], "answer": answer},
        )
    await pg_client.post(f"/api/v1/quiz-attempts/{attempt['id']}/submit", headers=headers)

    progress_resp = await pg_client.get(f"/api/v1/subjects/{subject_id}/progress", headers=headers)
    assert progress_resp.status_code == 200
    nodes = progress_resp.json()
    assert len(nodes) == 1
    node = nodes[0]
    assert node["concept_id"] == concept.id
    # flashcard signal: 5/5*100=100, quiz signal: 1/3 correct=33.3 -> average 66.7
    assert node["mastery_score"] == 66.7
    assert node["trend"] == "flat"  # first time this concept has been scored

    weak_resp = await pg_client.get(f"/api/v1/subjects/{subject_id}/weak-concepts", headers=headers)
    assert weak_resp.status_code == 200
    weak = weak_resp.json()
    # 2 wrong out of 3 = 67% error rate, above the default 50% threshold -> flagged
    assert len(weak) == 1
    assert weak[0]["concept_id"] == concept.id
    assert weak[0]["reason"] == "repeated_errors"
    assert weak[0]["status"] == "active"
