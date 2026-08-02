from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_current_user, get_quiz_service
from app.api.v1.schemas.quiz import (
    AnswerAckResponse,
    AnswerSubmitRequest,
    AttemptResponse,
    AttemptResultResponse,
    QuizGenerateRequest,
    QuizResponse,
)
from app.domain.entities.user import User
from app.services.quiz_engine.quiz_service import QuizService

router = APIRouter(tags=["quizzes"])


@router.post("/subjects/{subject_id}/quizzes/generate", response_model=QuizResponse)
async def generate_quiz(
    subject_id: str,
    body: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
) -> QuizResponse:
    quiz = await service.generate(
        user_id=current_user.id,
        subject_id=subject_id,
        document_id=body.document_id,
        count=body.count,
        difficulty=body.difficulty,
        question_types=body.question_types,
        title=body.title,
    )
    questions = await service.get_questions(quiz.id)
    return QuizResponse.from_entity(quiz, questions)


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
) -> QuizResponse:
    quiz = await service.get_owned(user_id=current_user.id, quiz_id=quiz_id)
    questions = await service.get_questions(quiz.id)
    return QuizResponse.from_entity(quiz, questions)


@router.post("/quizzes/{quiz_id}/attempts", response_model=AttemptResponse, status_code=status.HTTP_201_CREATED)
async def start_attempt(
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
) -> AttemptResponse:
    attempt = await service.start_attempt(user_id=current_user.id, quiz_id=quiz_id)
    return AttemptResponse.from_entity(attempt)


@router.post("/quiz-attempts/{attempt_id}/answers", response_model=AnswerAckResponse)
async def submit_answer(
    attempt_id: str,
    body: AnswerSubmitRequest,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
) -> AnswerAckResponse:
    answer = await service.submit_answer(
        user_id=current_user.id,
        attempt_id=attempt_id,
        question_id=body.question_id,
        answer=body.answer,
        time_spent_seconds=body.time_spent_seconds,
    )
    return AnswerAckResponse.from_entity(answer)


@router.post("/quiz-attempts/{attempt_id}/submit", response_model=AttemptResultResponse)
async def submit_attempt(
    attempt_id: str,
    current_user: User = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
) -> AttemptResultResponse:
    attempt, questions, answers = await service.submit_attempt(user_id=current_user.id, attempt_id=attempt_id)
    return AttemptResultResponse.from_entities(attempt, questions, answers)
