from __future__ import annotations

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception that maps to a structured error response."""

    error_code: str = "INTERNAL_ERROR"
    service: str | None = None
    retryable: bool = False

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str | None = None,
        service: str | None = None,
        retryable: bool = False,
        correlation_id: str = "",
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.error_code = error_code or self.__class__.error_code
        self.service = service
        self.retryable = retryable
        self.correlation_id = correlation_id


class NotFoundError(AppException):
    error_code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found", **kwargs: object) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            **kwargs,  # type: ignore[arg-type]
        )


class UnauthorizedError(AppException):
    error_code = "UNAUTHORIZED"

    def __init__(self, message: str = "Authentication required", **kwargs: object) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            **kwargs,  # type: ignore[arg-type]
        )


class ForbiddenError(AppException):
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "Access denied", **kwargs: object) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            **kwargs,  # type: ignore[arg-type]
        )


class ConflictError(AppException):
    error_code = "CONFLICT"

    def __init__(self, message: str = "Resource conflict", **kwargs: object) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            **kwargs,  # type: ignore[arg-type]
        )


class ValidationError(AppException):
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str = "Validation failed", **kwargs: object) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            **kwargs,  # type: ignore[arg-type]
        )


class QuotaExhaustedError(AppException):
    error_code = "PROVIDER_QUOTA_EXHAUSTED"

    def __init__(
        self,
        message: str = "Service quota exhausted. Please try again later.",
        service: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            service=service,
            retryable=False,
            **kwargs,  # type: ignore[arg-type]
        )


class ServiceUnavailableError(AppException):
    error_code = "SERVICE_UNAVAILABLE"

    def __init__(
        self,
        message: str = "Service temporarily unavailable.",
        service: str | None = None,
        retryable: bool = True,
        **kwargs: object,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            service=service,
            retryable=retryable,
            **kwargs,  # type: ignore[arg-type]
        )


class NotImplementedFeatureError(AppException):
    error_code = "NOT_IMPLEMENTED"

    def __init__(
        self,
        message: str = "This feature is not yet implemented.",
        **kwargs: object,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            **kwargs,  # type: ignore[arg-type]
        )
