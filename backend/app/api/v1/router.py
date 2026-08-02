from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.subjects import router as subjects_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(subjects_router)
api_router.include_router(documents_router)
api_router.include_router(chat_router)
