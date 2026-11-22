from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import RequestIdMiddleware, get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    setup_logging(
        log_level="DEBUG" if settings.debug else "INFO",
        json_logs=settings.is_production,
    )
    logger.info(
        "Starting TaskFlow API",
        extra={
            "extra_fields": {
                "version": settings.app_version,
                "environment": settings.environment,
                "git_sha": settings.git_sha,
            }
        },
    )
    yield
    logger.info("Shutting down TaskFlow API")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A production-ready task management REST API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/health/live", tags=["Health"], summary="Liveness probe")
async def health_live() -> dict[str, str]:
    """Check if the service is running."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"], summary="Readiness probe")
async def health_ready() -> dict[str, str]:
    """Check if the service is ready to accept requests."""
    from sqlalchemy import text

    from app.db.session import async_session_maker

    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(  # type: ignore[return-value]
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "detail": "Database unavailable"},
        )


@app.get("/version", tags=["Info"], summary="Get application version")
async def get_version() -> dict[str, Any]:
    """Get the current application version and build information."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "git_sha": settings.git_sha,
        "build_time": settings.build_time,
        "environment": settings.environment,
    }
