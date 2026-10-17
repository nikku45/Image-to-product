from typing import Any, Optional


class AppError(Exception):
    """Base application exception."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ImageValidationError(AppError):
    """Raised when an uploaded image fails validation (corrupt, oversized, invalid type)."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            code="IMAGE_VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )


class ExternalProviderError(AppError):
    """Raised when Gemini or SerpApi encounters an external failure or quota exhaustion."""

    def __init__(self, provider: str, message: str, status_code: int = 502, details: Optional[Any] = None):
        super().__init__(
            code=f"{provider.upper()}_PROVIDER_ERROR",
            message=message,
            status_code=status_code,
            details=details,
        )


class EntityNotFoundError(AppError):
    """Raised when a requested resource (search_id, candidate) does not exist."""

    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(
            code="NOT_FOUND",
            message=f"{entity_name} with id '{entity_id}' not found",
            status_code=404,
        )
