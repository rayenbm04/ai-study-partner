"""Classifies one document by type (exam, resume/summary notes, TD, TP,
cours) and — when the document's subject is linked to the curriculum catalog
— places it under the best-matching existing chapter/lesson.

Mirrors concept_tagger.py's shape: one LLM call per document, strict-JSON
response, defensive parsing, self-contained persistence. The key constraint
(agreed with the product owner) is that the LLM only ever matches chapters/
lessons already in the catalog by exact name — it never invents new ones."""
import json
import logging

from app.domain.entities.curriculum import Chapter, Lesson
from app.domain.repositories.curriculum_repository import CurriculumRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

DOCUMENT_TYPES = ("exam", "resume", "td", "tp", "cours", "other")

_SYSTEM_PROMPT = (
    "You are classifying a study document for a student. Given the document's text, decide "
    "which single type it is: 'exam' (a test/exam paper), 'resume' (condensed summary notes), "
    "'td' (travaux diriges - guided exercises), 'tp' (travaux pratiques - practical/lab work), "
    "'cours' (lecture/course notes), or 'other' if none of those fit. "
    "If a list of existing chapters (each with its lessons) is provided, also pick the single "
    "best-matching chapter and, if clear, lesson for this document - using the exact name as "
    "given, never inventing a new one. If nothing fits well, or no list was provided, use null. "
    "Respond with strict JSON only, matching this shape: "
    '{"document_type": "<one of exam|resume|td|tp|cours|other>", '
    '"chapter": "<exact chapter name from the list, or null>", '
    '"lesson": "<exact lesson name from the list, or null>", '
    '"confidence": <0-1 float, your confidence in the chapter/lesson match>}'
)


class DocumentClassifier:
    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        curriculum_repo: CurriculumRepository,
        document_repo: DocumentRepository,
        confidence_threshold: float,
    ):
        self._llm = llm_provider
        self._curriculum = curriculum_repo
        self._documents = document_repo
        self._confidence_threshold = confidence_threshold

    async def classify(self, *, document_id: str, curriculum_subject_id: str | None, source_text: str) -> None:
        chapters: list[Chapter] = []
        lessons_by_chapter: dict[str, list[Lesson]] = {}
        if curriculum_subject_id:
            chapters = await self._curriculum.list_chapters(curriculum_subject_id)
            for chapter in chapters:
                lessons_by_chapter[chapter.id] = await self._curriculum.list_lessons(chapter.id)

        response_text = await self._llm.complete(
            system=_SYSTEM_PROMPT,
            prompt=self._build_prompt(source_text, chapters, lessons_by_chapter),
            temperature=0.1,
            response_json=True,
        )
        parsed = self._parse_response(response_text)

        document_type = str((parsed or {}).get("document_type", "")).strip().lower()
        if document_type not in DOCUMENT_TYPES:
            document_type = "other"

        try:
            confidence = float((parsed or {}).get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0

        chapter_id: str | None = None
        lesson_id: str | None = None
        if parsed is not None and confidence >= self._confidence_threshold:
            chapter_name = str(parsed.get("chapter") or "").strip()
            chapter = next((c for c in chapters if c.name == chapter_name), None) if chapter_name else None
            if chapter is not None:
                chapter_id = chapter.id
                lesson_name = str(parsed.get("lesson") or "").strip()
                lesson = (
                    next((c for c in lessons_by_chapter.get(chapter.id, []) if c.name == lesson_name), None)
                    if lesson_name
                    else None
                )
                if lesson is not None:
                    lesson_id = lesson.id

        await self._documents.set_classification(
            document_id, document_type=document_type, chapter_id=chapter_id, lesson_id=lesson_id, confidence=confidence
        )

    def _build_prompt(self, source_text: str, chapters: list[Chapter], lessons_by_chapter: dict[str, list[Lesson]]) -> str:
        if not chapters:
            candidates = "(no chapter list available - only classify document_type, leave chapter/lesson null)"
        else:
            lines = []
            for chapter in chapters:
                lesson_names = ", ".join(lesson.name for lesson in lessons_by_chapter.get(chapter.id, [])) or "(no lessons)"
                lines.append(f"- {chapter.name}: {lesson_names}")
            candidates = "\n".join(lines)
        return f"Existing chapters and their lessons:\n{candidates}\n\nDocument text:\n\"\"\"\n{source_text}\n\"\"\""

    def _parse_response(self, response_text: str) -> dict | None:
        try:
            parsed = json.loads(response_text)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Document classifier got a non-JSON response: %r", response_text[:200])
            return None
        if not isinstance(parsed, dict):
            logger.warning("Document classifier got a JSON response that wasn't an object.")
            return None
        return parsed
