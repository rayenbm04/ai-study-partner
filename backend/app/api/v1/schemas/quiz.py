from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.entities.quiz import Quiz, QuizAttempt, QuizQuestion, StudentAnswer

QuestionType = Literal["mcq", "true_false", "short_answer", "calculation", "fill_blank"]
Difficulty = Literal["easy", "medium", "hard"]


class QuizGenerateRequest(BaseModel):
    document_id: str
    count: int | None = Field(default=None, ge=1, le=50)
    difficulty: Difficulty = "medium"
    question_types: list[QuestionType] | None = None
    title: str | None = None


class QuizQuestionPublic(BaseModel):
    """What's shown before an attempt is submitted — no correct_answer or
    explanation, so a student can't just read the answer off the quiz."""

    id: str
    type: str
    question: str
    options: list[str] | None
    points: int
    difficulty: str
    concept_id: str | None

    @classmethod
    def from_entity(cls, question: QuizQuestion) -> "QuizQuestionPublic":
        return cls(
            id=question.id,
            type=question.type,
            question=question.question,
            options=question.options,
            points=question.points,
            difficulty=question.difficulty,
            concept_id=question.concept_id,
        )


class QuizResponse(BaseModel):
    id: str
    subject_id: str
    title: str
    kind: str
    difficulty: str
    topics: list[str]
    duration_minutes: int | None
    style: str | None
    created_at: datetime
    questions: list[QuizQuestionPublic]

    @classmethod
    def from_entity(cls, quiz: Quiz, questions: list[QuizQuestion]) -> "QuizResponse":
        return cls(
            id=quiz.id,
            subject_id=quiz.subject_id,
            title=quiz.title,
            kind=quiz.kind,
            difficulty=quiz.difficulty,
            topics=quiz.topics,
            duration_minutes=quiz.duration_minutes,
            style=quiz.style,
            created_at=quiz.created_at,
            questions=[QuizQuestionPublic.from_entity(q) for q in questions],
        )


class AttemptResponse(BaseModel):
    id: str
    quiz_id: str
    started_at: datetime
    completed_at: datetime | None
    score: float | None

    @classmethod
    def from_entity(cls, attempt: QuizAttempt) -> "AttemptResponse":
        return cls(
            id=attempt.id,
            quiz_id=attempt.quiz_id,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            score=attempt.score,
        )


class AnswerSubmitRequest(BaseModel):
    question_id: str
    answer: str
    time_spent_seconds: int | None = Field(default=None, ge=0)


class AnswerAckResponse(BaseModel):
    """Deliberately doesn't reveal is_correct — per-question feedback is
    withheld until the attempt is submitted (POST .../submit), so a student
    can't probe answers one at a time before committing to the attempt."""

    question_id: str
    submitted_at: datetime

    @classmethod
    def from_entity(cls, answer: StudentAnswer) -> "AnswerAckResponse":
        return cls(question_id=answer.quiz_question_id, submitted_at=answer.submitted_at)


class QuestionResult(BaseModel):
    question_id: str
    question: str
    type: str
    student_answer: str | None
    correct_answer: str
    explanation: str | None
    is_correct: bool | None
    points: int


class AttemptResultResponse(BaseModel):
    id: str
    quiz_id: str
    started_at: datetime
    completed_at: datetime | None
    score: float | None
    answers: list[QuestionResult]

    @classmethod
    def from_entities(
        cls, attempt: QuizAttempt, questions: list[QuizQuestion], answers: list[StudentAnswer]
    ) -> "AttemptResultResponse":
        answers_by_question = {a.quiz_question_id: a for a in answers}
        results = []
        for question in questions:
            answer = answers_by_question.get(question.id)
            results.append(
                QuestionResult(
                    question_id=question.id,
                    question=question.question,
                    type=question.type,
                    student_answer=answer.answer if answer else None,
                    correct_answer=question.correct_answer,
                    explanation=question.explanation,
                    is_correct=answer.is_correct if answer else None,
                    points=question.points,
                )
            )
        return cls(
            id=attempt.id,
            quiz_id=attempt.quiz_id,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            score=attempt.score,
            answers=results,
        )
