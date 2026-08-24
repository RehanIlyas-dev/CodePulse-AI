import logging
import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Configure error logging for internal monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("codepulse_error_logger")


def _cors_headers(request: Request) -> dict:
    # Starlette's error middleware sits OUTSIDE CORSMiddleware, so responses
    # produced by these handlers would reach browsers without CORS headers and
    # get misreported as network failures ("Failed to fetch") instead of the
    # real status code. Echo the origin back when it is allow-listed.
    origin = request.headers.get("origin")
    if not origin:
        return {}
    allowed = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    if origin in allowed:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


def register_exception_handlers(app: FastAPI) -> None:

    # --> Register global exception handlers for the FastAPI application

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Unprocessable Entity",
                "details": exc.errors(),
                "status_code": 422
            },
            headers=_cors_headers(request),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Log the exception details for internal monitoring
        logger.error(f"Unhandled exception at path {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred while processing your analysis. Please try again later.",
                "status_code": 500
            },
            headers=_cors_headers(request),
        )
