import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.genai import errors as genai_errors
from openai import APIError as OpenAIAPIError
from openai import RateLimitError as OpenAIRateLimitError

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)

# Every LLM/embedding call already goes through retry_on_rate_limit (bounded
# retries with backoff) at the provider layer — these handlers are the
# backstop for when a call still fails after that: an exhausted daily quota,
# a persistent per-minute 429, or a genuine provider outage. Without them,
# such an exception reaching a route handler uncaught (e.g. ChatService's
# final answer-generation call, which unlike condense/expand/rerank has no
# local try/except — those degrade gracefully on purpose) would surface to
# the mobile app as a raw 500 with no actionable code, and depending on
# deployment config could leak provider exception internals. Registered for
# the SDKs' *base* error types so every provider (Gemini, Groq/OpenRouter/
# OpenAI-compatible) is covered by one pair of handlers, not one per call site.
_AI_RATE_LIMITED = {"detail": "The AI service is temporarily busy. Please try again shortly.", "code": "AI_RATE_LIMITED"}
_AI_UNAVAILABLE = {"detail": "The AI service is temporarily unavailable. Please try again later.", "code": "AI_UNAVAILABLE"}


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="AI Study Coach API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        content: dict = {"detail": exc.message}
        if exc.code:
            content["code"] = exc.code
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(genai_errors.APIError)
    async def gemini_error_handler(request: Request, exc: genai_errors.APIError) -> JSONResponse:
        if isinstance(exc, genai_errors.ClientError) and exc.code == 429:
            logger.warning("Gemini rate limit reached the API boundary uncaught (all retries exhausted).")
            return JSONResponse(status_code=503, content=_AI_RATE_LIMITED)
        logger.warning("Gemini provider error reached the API boundary uncaught: %s", exc)
        return JSONResponse(status_code=502, content=_AI_UNAVAILABLE)

    @app.exception_handler(OpenAIAPIError)
    async def openai_compatible_error_handler(request: Request, exc: OpenAIAPIError) -> JSONResponse:
        if isinstance(exc, OpenAIRateLimitError):
            logger.warning("Provider rate limit reached the API boundary uncaught (all retries exhausted).")
            return JSONResponse(status_code=503, content=_AI_RATE_LIMITED)
        logger.warning("Provider error reached the API boundary uncaught: %s", exc)
        return JSONResponse(status_code=502, content=_AI_UNAVAILABLE)

    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
