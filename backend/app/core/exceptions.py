import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Configure error logging for internal monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("codepulse_error_logger")

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
            }
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
            }
        )