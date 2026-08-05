import json

from app.services.knowledge_base.document_classifier import DocumentClassifier
from tests.unit.fakes import FakeCurriculumRepository, FakeDocumentRepository, FakeLLMProvider


async def _classifier(llm, confidence_threshold=0.5):
    curriculum_repo = FakeCurriculumRepository()
    document_repo = FakeDocumentRepository()
    classifier = DocumentClassifier(
        llm_provider=llm, curriculum_repo=curriculum_repo, document_repo=document_repo,
        confidence_threshold=confidence_threshold,
    )
    return classifier, curriculum_repo, document_repo


async def test_classifies_document_type_with_no_curriculum_link():
    llm = FakeLLMProvider(response=json.dumps({"document_type": "exam", "chapter": None, "lesson": None, "confidence": 0.9}))
    classifier, _curriculum_repo, document_repo = await _classifier(llm)
    document = await document_repo.create(
        document_id="doc-1", subject_id="subj-1", original_filename="exam.pdf", storage_path="p", file_type=".pdf"
    )

    await classifier.classify(document_id=document.id, curriculum_subject_id=None, source_text="Exam paper text")

    updated = await document_repo.get_by_id("doc-1")
    assert updated.document_type == "exam"
    assert updated.chapter_id is None
    assert updated.lesson_id is None
    assert updated.classified_at is not None
    # No curriculum_subject_id was given, so no chapter/lesson candidates were fetched or sent.
    assert "no chapter list available" in llm.calls[0]["prompt"]


async def test_matches_existing_chapter_and_lesson_by_exact_name():
    llm = FakeLLMProvider(
        response=json.dumps({"document_type": "td", "chapter": "Limits", "lesson": "Epsilon-delta", "confidence": 0.8})
    )
    classifier, curriculum_repo, document_repo = await _classifier(llm)
    subject = await curriculum_repo.create_subject(academic_level_id="lvl-1", section_id=None, name="Math")
    chapter = await curriculum_repo.create_chapter(curriculum_subject_id=subject.id, name="Limits", order_index=0)
    lesson = await curriculum_repo.create_lesson(chapter_id=chapter.id, name="Epsilon-delta", order_index=0)
    document = await document_repo.create(
        document_id="doc-1", subject_id="subj-1", original_filename="td.pdf", storage_path="p", file_type=".pdf"
    )

    await classifier.classify(document_id=document.id, curriculum_subject_id=subject.id, source_text="TD on limits")

    updated = await document_repo.get_by_id("doc-1")
    assert updated.document_type == "td"
    assert updated.chapter_id == chapter.id
    assert updated.lesson_id == lesson.id


async def test_chapter_not_in_candidate_list_is_dropped_not_invented():
    llm = FakeLLMProvider(
        response=json.dumps({"document_type": "cours", "chapter": "Made Up Chapter", "lesson": None, "confidence": 0.9})
    )
    classifier, curriculum_repo, document_repo = await _classifier(llm)
    subject = await curriculum_repo.create_subject(academic_level_id="lvl-1", section_id=None, name="Math")
    await curriculum_repo.create_chapter(curriculum_subject_id=subject.id, name="Real Chapter", order_index=0)
    document = await document_repo.create(
        document_id="doc-1", subject_id="subj-1", original_filename="notes.pdf", storage_path="p", file_type=".pdf"
    )

    await classifier.classify(document_id=document.id, curriculum_subject_id=subject.id, source_text="Course notes")

    updated = await document_repo.get_by_id("doc-1")
    assert updated.document_type == "cours"
    assert updated.chapter_id is None


async def test_low_confidence_match_drops_chapter_but_keeps_document_type():
    llm = FakeLLMProvider(
        response=json.dumps({"document_type": "tp", "chapter": "Limits", "lesson": None, "confidence": 0.1})
    )
    classifier, curriculum_repo, document_repo = await _classifier(llm, confidence_threshold=0.5)
    subject = await curriculum_repo.create_subject(academic_level_id="lvl-1", section_id=None, name="Math")
    await curriculum_repo.create_chapter(curriculum_subject_id=subject.id, name="Limits", order_index=0)
    document = await document_repo.create(
        document_id="doc-1", subject_id="subj-1", original_filename="tp.pdf", storage_path="p", file_type=".pdf"
    )

    await classifier.classify(document_id=document.id, curriculum_subject_id=subject.id, source_text="Lab work")

    updated = await document_repo.get_by_id("doc-1")
    assert updated.document_type == "tp"
    assert updated.chapter_id is None


async def test_malformed_json_falls_back_to_other_without_raising():
    llm = FakeLLMProvider(response="not json at all")
    classifier, _curriculum_repo, document_repo = await _classifier(llm)
    document = await document_repo.create(
        document_id="doc-1", subject_id="subj-1", original_filename="mystery.pdf", storage_path="p", file_type=".pdf"
    )

    await classifier.classify(document_id=document.id, curriculum_subject_id=None, source_text="???")

    updated = await document_repo.get_by_id("doc-1")
    assert updated.document_type == "other"


async def test_invalid_document_type_value_falls_back_to_other():
    llm = FakeLLMProvider(response=json.dumps({"document_type": "cv", "chapter": None, "lesson": None, "confidence": 0.9}))
    classifier, _curriculum_repo, document_repo = await _classifier(llm)
    document = await document_repo.create(
        document_id="doc-1", subject_id="subj-1", original_filename="doc.pdf", storage_path="p", file_type=".pdf"
    )

    await classifier.classify(document_id=document.id, curriculum_subject_id=None, source_text="Some resume-shaped doc")

    updated = await document_repo.get_by_id("doc-1")
    assert updated.document_type == "other"
