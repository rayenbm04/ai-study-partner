from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_exam_service, get_language, get_quiz_service
from app.api.v1.schemas.exam import ExamGenerateRequest
from app.api.v1.schemas.quiz import AttemptResponse, QuizResponse
from app.domain.entities.user import User
from app.services.exam_engine.exam_service import ExamService
from app.services.quiz_engine.quiz_service import QuizService

router = APIRouter(tags=["exams"])


@router.post("/subjects/{subject_id}/exams/generate", response_model=QuizResponse)
async def generate_exam(
    subject_id: str,
    body: ExamGenerateRequest,
    current_user: User = Depends(get_current_user),
    exam_service: ExamService = Depends(get_exam_service),
    quiz_service: QuizService = Depends(get_quiz_service),
    language: str = Depends(get_language),
) -> QuizResponse:
    exam = await exam_service.generate(
        user_id=current_user.id,
        subject_id=subject_id,
        document_id=body.document_id,
        count=body.count,
        difficulty=body.difficulty,
        question_types=body.question_types,
        duration_minutes=body.duration_minutes,
        style=body.style,
        title=body.title,
        language=language,
    )
    questions = await quiz_service.get_questions(exam.id)
    return QuizResponse.from_entity(exam, questions)


@router.get("/exams/{exam_id}/history", response_model=list[AttemptResponse])
async def get_exam_history(
    exam_id: str,
    current_user: User = Depends(get_current_user),
    exam_service: ExamService = Depends(get_exam_service),
) -> list[AttemptResponse]:
    attempts = await exam_service.get_history(user_id=current_user.id, exam_id=exam_id)
    return [AttemptResponse.from_entity(a) for a in attempts]
