"""
Common error handling utilities.

Provides standardized error handling for API endpoints and services.
"""
import logging
from fastapi import HTTPException
from typing import Optional

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API-related errors."""

    def __init__(self, message: str, status_code: int = 500, detail: str = ""):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class NotFoundError(APIError):
    """Exception raised when a resource is not found."""

    def __init__(self, resource: str, identifier: str = ""):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, status_code=404)


class ValidationError(APIError):
    """Exception raised when input validation fails."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=422)
        self.details = details or {}


class ExternalAPIError(APIError):
    """Exception raised when external API call fails."""

    def __init__(self, service: str, message: str = ""):
        base_msg = f"{service} API error"
        if message:
            base_msg += f": {message}"
        super().__init__(base_msg, status_code=503)


def handle_api_error(
    e: Exception,
    context: str = "",
    status_code: int = 500,
    reraise: bool = True
) -> None:
    """
    Standardized error handling for API endpoints.

    Logs the error and optionally raises HTTPException.

    Args:
        e: The exception that occurred
        context: Additional context about where the error occurred
        status_code: HTTP status code for the error (default: 500)
        reraise: Whether to raise HTTPException (default: True)

    Raises:
        HTTPException: If reraise is True

    Usage:
        try:
            result = some_operation()
        except Exception as e:
            handle_api_error(e, context="get_players")
    """
    context_msg = f" in {context}" if context else ""
    logger.error(f"Error{context_msg}: {e}", exc_info=True)

    if reraise:
        # Extract meaningful message from exception
        detail = str(e) if str(e) else f"An error occurred{context_msg}"

        # Handle specific error types
        if isinstance(e, (NotFoundError, ValidationError, ExternalAPIError)):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        else:
            raise HTTPException(status_code=status_code, detail=detail)


def log_and_return_error(
    e: Exception,
    context: str = "",
    default_return: any = None
) -> any:
    """
    Log error and return default value without raising exception.

    Useful for background tasks and async operations where you want
    to continue execution despite errors.

    Args:
        e: The exception that occurred
        context: Additional context about where the error occurred
        default_return: Value to return (default: None)

    Returns:
        The default_return value

    Usage:
        result = log_and_return_error(e, context="sync_player", default_return=False)
    """
    context_msg = f" in {context}" if context else ""
    logger.error(f"Error{context_msg}: {e}", exc_info=True)
    return default_return
