from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.exams import router as exams_router
from app.api.v1.routes.flashcards import router as flashcards_router
from app.api.v1.routes.quizzes import router as quizzes_router
from app.api.v1.routes.subjects import router as subjects_router
from app.api.v1.routes.summaries import router as summaries_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(subjects_router)
api_router.include_router(documents_router)
api_router.include_router(chat_router)
api_router.include_router(summaries_router)
api_router.include_router(flashcards_router)
api_router.include_router(quizzes_router)
api_router.include_router(exams_router)
