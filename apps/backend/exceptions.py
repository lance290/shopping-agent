"""
Custom exception hierarchy for Shopping Agent backend.

This module provides a standardized exception hierarchy for consistent error
handling throughout the application. All exceptions inherit from a base
ShoppingAgentError class for easy catching and logging.

Exception Hierarchy:
    ShoppingAgentError (base)
    ├── ValidationError
    ├── AuthenticationError
    ├── AuthorizationError
    ├── ResourceNotFoundError
    ├── RateLimitError
    ├── ExternalServiceError
    │   ├── LLMError
    │   ├── SearchProviderError
    │   ├── EmailServiceError
    │   └── StorageServiceError
    └── DatabaseError

Usage:
    from exceptions import ValidationError, AuthorizationError

    # Raise with simple message
    raise ValidationError("Invalid input")

    # Raise with detail dict
    raise ValidationError("Invalid input", detail={"field": "email"})

    # Catch specific exceptions
    try:
        do_something()
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
    except ShoppingAgentError as e:
        logger.error(f"Application error: {e}")
"""

from typing import Optional, Dict, Any


class ShoppingAgentError(Exception):
    """
    Base exception for all Shopping Agent application errors.

    Attributes:
        message: Human-readable error message
        detail: Optional dict with additional error context
        status_code: Suggested HTTP status code (for API errors)
    """

    def __init__(
        self,
        message: str,
        *,
        detail: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ):
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.status_code = status_code

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a dictionary for JSON serialization."""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
        }
        if self.detail:
            result["detail"] = self.detail
        return result


class ValidationError(ShoppingAgentError):
    """
    Raised when input validation fails.

    Examples:
        raise ValidationError("Email is required")
        raise ValidationError("Invalid format", detail={"field": "phone"})
    """

    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, detail=detail, status_code=400)


class AuthenticationError(ShoppingAgentError):
    """
    Raised when authentication fails.

    Examples:
        raise AuthenticationError("Invalid session token")
        raise AuthenticationError("Session expired")
    """

    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, detail=detail, status_code=401)


class AuthorizationError(ShoppingAgentError):
    """
    Raised when user lacks permissions for an action.

    Examples:
        raise AuthorizationError("Insufficient permissions")
        raise AuthorizationError("Cannot access project", detail={"project_id": 123})
    """

    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, detail=detail, status_code=403)


class ResourceNotFoundError(ShoppingAgentError):
    """
    Raised when a requested resource doesn't exist.

    Examples:
        raise ResourceNotFoundError("Row not found", detail={"row_id": 123})
        raise ResourceNotFoundError("User does not exist")
    """

    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, detail=detail, status_code=404)


class RateLimitError(ShoppingAgentError):
    """
    Raised when rate limit is exceeded.

    Examples:
        raise RateLimitError("Too many requests")
        raise RateLimitError("Rate limit exceeded", detail={"retry_after": 60})
    """

    def __init__(
        self,
        message: str,
        *,
        detail: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ):
        if retry_after and detail is None:
            detail = {"retry_after": retry_after}
        elif retry_after and detail:
            detail["retry_after"] = retry_after

        super().__init__(message, detail=detail, status_code=429)


class DatabaseError(ShoppingAgentError):
    """
    Raised when database operations fail.

    Examples:
        raise DatabaseError("Failed to save row")
        raise DatabaseError("Constraint violation", detail={"constraint": "unique_email"})
    """

    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, detail=detail, status_code=500)


class ExternalServiceError(ShoppingAgentError):
    """
    Base exception for external service failures.

    This is a parent class for specific service errors (LLM, Search, etc.)
    """

    def __init__(
        self,
        message: str,
        *,
        detail: Optional[Dict[str, Any]] = None,
        service_name: Optional[str] = None,
    ):
        if service_name and detail is None:
            detail = {"service": service_name}
        elif service_name and detail:
            detail["service"] = service_name

        super().__init__(message, detail=detail, status_code=502)


class LLMError(ExternalServiceError):
    """
    Raised when LLM service (OpenAI, Anthropic, etc.) fails.

    Examples:
        raise LLMError("OpenAI API timeout")
        raise LLMError("Invalid API key", detail={"provider": "openai"})
    """

    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, detail=detail, service_name="llm")


class SearchProviderError(ExternalServiceError):
    """
    Raised when search provider (eBay, Amazon, etc.) fails.

    Examples:
        raise SearchProviderError("eBay API timeout")
        raise SearchProviderError("Rate limited", detail={"provider": "amazon"})
    """

    def __init__(
        self,
        message: str,
        *,
        detail: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
    ):
        if provider and detail is None:
            detail = {"provider": provider}
        elif provider and detail:
            detail["provider"] = provider

        super().__init__(message, detail=detail, service_name="search_provider")


class EmailServiceError(ExternalServiceError):
    """
    Raised when email service (Resend, SMTP, etc.) fails.

    Examples:
        raise EmailServiceError("Failed to send email")
        raise EmailServiceError("Invalid recipient", detail={"email": "test@example.com"})
    """

    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, detail=detail, service_name="email")


class StorageServiceError(ExternalServiceError):
    """
    Raised when storage service (S3, etc.) fails.

    Examples:
        raise StorageServiceError("Failed to upload file")
        raise StorageServiceError("Bucket not found", detail={"bucket": "uploads"})
    """

    def __init__(self, message: str, *, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, detail=detail, service_name="storage")
