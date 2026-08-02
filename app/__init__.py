import logging
import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.common.sentry_config import SentryConfig
from app.routes import ROUTES


def create_app() -> FastAPI:
    app = FastAPI(
        title="ResolveWithAI API",
        description="Backend API for ResolveWithAI - A conflict resolution platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize Sentry
    SentryConfig.init_sentry()

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        logger.info(
            "%s - %s %s",
            request.client.host if request.client else "unknown",
            request.method,
            request.url.path,
        )

        response = await call_next(request)

        time_taken = time.time() - start_time
        logger.info(
            "%s - %d %.4fs",
            request.url.path,
            response.status_code,
            time_taken,
        )

        return response

    # Include all routers
    for router in ROUTES:
        app.include_router(router)

    return app
