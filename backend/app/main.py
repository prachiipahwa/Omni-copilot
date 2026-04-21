from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from asgi_correlation_id import CorrelationIdMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router

setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — startup checks and graceful shutdown."""
    # ── Startup ──────────────────────────────────────────────────────────────
    missing = []
    if not settings.SECRET_KEY or settings.SECRET_KEY == "CHANGE_ME_USE_SECRETS_TOKEN_HEX_32":
        missing.append("SECRET_KEY")
    if not settings.ENCRYPTION_KEY or settings.ENCRYPTION_KEY == "CHANGE_ME_USE_FERNET_GENERATE_KEY":
        missing.append("ENCRYPTION_KEY")
    if not settings.OPENAI_API_KEY:
        logger.warning("openai_key_missing", hint="LLM and embedding calls will fail")

    if missing:
        logger.error("startup_config_error", missing_vars=missing)
        raise RuntimeError(f"Missing required environment variables: {missing}")

    logger.info("omni_copilot_started", version="4E", environment="production" if settings.COOKIE_SECURE else "development")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("omni_copilot_shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Unified AI Copilot — semantic search, grounded chat, and workspace integrations.",
    version="0.4.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# ── Middlewares ───────────────────────────────────────────────────────────────

app.add_middleware(CorrelationIdMiddleware)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "X-Request-ID"],
    )


# ── Global error handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        path=str(request.url.path),
        method=request.method,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(api_router, prefix=settings.API_V1_STR)
