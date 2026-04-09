"""Centralized error handling for consistent API responses.

Provides exception handlers and error response formatters to ensure
consistent error formats across all endpoints.
"""

import logging
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

from app.validators import ErrorResponse

logger = logging.getLogger(__name__)


def create_error_response(
    error: str,
    message: str,
    status_code: int,
    detail: Optional[Any] = None
) -> JSONResponse:
    """Create standardized error response.
    
    Args:
        error: Error type or category
        message: Human-readable error message
        status_code: HTTP status code
        detail: Additional error details
        
    Returns:
        JSONResponse with consistent error format
    """
    error_response = ErrorResponse(
        error=error,
        message=message,
        detail=detail,
        status_code=status_code
    )
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict(exclude_none=True)
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error on {request.url.path}: {exc}")
    return create_error_response(
        error="validation_error",
        message="Invalid request data",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=exc.errors()
    )


async def integrity_error_handler(
    request: Request,
    exc: IntegrityError
) -> JSONResponse:
    """Handle database integrity constraint violations."""
    logger.warning(f"Integrity error on {request.url.path}: {exc}")
    return create_error_response(
        error="integrity_error",
        message="Database constraint violation",
        status_code=status.HTTP_409_CONFLICT,
        detail="The requested operation violates a database constraint"
    )


async def operational_error_handler(
    request: Request,
    exc: OperationalError
) -> JSONResponse:
    """Handle database operational errors."""
    logger.error(f"Database error on {request.url.path}: {exc}")
    return create_error_response(
        error="database_error",
        message="Database operation failed",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The database is temporarily unavailable"
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return create_error_response(
        error="internal_error",
        message="An unexpected error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=None  # Don't expose internal error details
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers with the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(OperationalError, operational_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
