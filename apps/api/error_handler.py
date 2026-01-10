"""
Error handling utilities for RecipeNow API.
Provides standardized error logging and response formatting.
"""
import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class APIError:
    """Standardized API error handler."""

    @staticmethod
    def handle_database_error(
        operation: str,
        error: Exception,
        user_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> HTTPException:
        """
        Handle database errors with detailed logging.

        Args:
            operation: Description of the database operation
            error: The exception that occurred
            user_id: Optional user ID for context
            extra_context: Additional context to log

        Returns:
            HTTPException with appropriate status code
        """
        context = {
            "operation": operation,
            "user_id": user_id,
            **(extra_context or {}),
        }

        logger.error(
            f"Database error during {operation}: {str(error)}",
            extra=context,
            exc_info=True,
        )

        return HTTPException(
            status_code=500,
            detail=f"Database error during {operation}",
        )

    @staticmethod
    def handle_validation_error(
        operation: str,
        error: Exception,
        user_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> HTTPException:
        """
        Handle validation errors with detailed logging.

        Args:
            operation: Description of the operation
            error: The validation error
            user_id: Optional user ID for context
            extra_context: Additional context to log

        Returns:
            HTTPException with validation error details
        """
        context = {
            "operation": operation,
            "user_id": user_id,
            **(extra_context or {}),
        }

        logger.warning(
            f"Validation error during {operation}: {str(error)}",
            extra=context,
        )

        return HTTPException(
            status_code=400,
            detail=f"Validation error: {str(error)}",
        )

    @staticmethod
    def handle_not_found_error(
        resource: str,
        resource_id: str,
        user_id: Optional[str] = None,
    ) -> HTTPException:
        """
        Handle not found errors with detailed logging.

        Args:
            resource: Type of resource (e.g., 'Recipe', 'PantryItem')
            resource_id: ID of the resource
            user_id: Optional user ID for context

        Returns:
            HTTPException with not found error
        """
        logger.warning(
            f"{resource} not found: {resource_id}",
            extra={"resource_id": resource_id, "user_id": user_id},
        )

        return HTTPException(
            status_code=404,
            detail=f"{resource} not found",
        )

    @staticmethod
    def handle_generic_error(
        operation: str,
        error: Exception,
        user_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> HTTPException:
        """
        Handle generic/unexpected errors with detailed logging.

        Args:
            operation: Description of the operation
            error: The exception that occurred
            user_id: Optional user ID for context
            extra_context: Additional context to log

        Returns:
            HTTPException with generic error message
        """
        context = {
            "operation": operation,
            "user_id": user_id,
            **(extra_context or {}),
        }

        logger.exception(
            f"Unexpected error during {operation}: {str(error)}",
            extra=context,
        )

        return HTTPException(
            status_code=500,
            detail="An unexpected error occurred",
        )

    @staticmethod
    def log_operation_start(
        operation: str,
        user_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log the start of an operation."""
        context = {
            "operation": operation,
            "user_id": user_id,
            **(extra_context or {}),
        }
        logger.debug(f"Starting operation: {operation}", extra=context)

    @staticmethod
    def log_operation_success(
        operation: str,
        user_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log successful operation completion."""
        context = {
            "operation": operation,
            "user_id": user_id,
            **(extra_context or {}),
        }
        logger.info(f"Operation successful: {operation}", extra=context)
