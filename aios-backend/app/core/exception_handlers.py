"""Global exception handling.

Every `AIOSError` subclass (see `app.core.exceptions`) is translated here
into one consistent JSON error envelope. This is the single place that
decides what an error response looks like — routers and services just
raise; they never build an error response themselves.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AIOSError
from app.logging.context import get_correlation_id, get_request_id
from app.logging.setup import get_logger

logger = get_logger(__name__)


def _envelope(status_code: int, error_code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {},
                "request_id": get_request_id(),
                "correlation_id": get_correlation_id(),
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AIOSError)
    async def aios_error_handler(request: Request, exc: AIOSError) -> JSONResponse:
        logger.warning("handled_error", error_code=exc.error_code, message=exc.message, path=request.url.path)
        return _envelope(exc.status_code, exc.error_code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("request_validation_error", errors=exc.errors(), path=request.url.path)
        return _envelope(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "request_validation_error",
            "The request payload failed validation.",
            {"errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _envelope(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", error=str(exc), path=request.url.path, exc_info=True)
        return _envelope(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred. It has been logged for investigation.",
        )
