import logging
import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from config import settings
from logging_config import setup_logging, get_logger
from routers import assets, match, pantry, recipes, shopping_list

# Setup logging on startup
setup_logging(log_level=settings.LOG_LEVEL)
logger = get_logger(__name__)

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
)

# CORS configuration - Allow requests from Vercel frontend and local development
logger.info(f"Enabling CORS for origins: {settings.allowed_origins_list}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for request/response logging and error handling
class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """Log request details and measure response time."""
        start_time = time.time()
        request_id = request.headers.get("x-request-id", "unknown")

        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} "
                f"completed with status {response.status_code} in {duration:.3f}s"
            )

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"failed after {duration:.3f}s: {str(e)}",
                exc_info=True,
            )

            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                },
            )


# Add middleware
app.add_middleware(LoggingMiddleware)


app.include_router(assets.router, prefix="/assets", tags=["assets"])
app.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
app.include_router(pantry.router, prefix="/pantry", tags=["pantry"])
app.include_router(match.router, prefix="/match", tags=["match"])
app.include_router(shopping_list.router, prefix="/shopping-list", tags=["shopping-list"])


@app.get("/")
def health_check() -> dict:
    """Health check endpoint."""
    logger.debug("Health check called")
    return {"status": "ok", "version": "0.1.0"}
