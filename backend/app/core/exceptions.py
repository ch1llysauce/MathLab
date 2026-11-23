"""Domain and API exception definitions."""

from typing import Any


class MathLabError(Exception):
    """Base exception for all structured MathLab application errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "MATHLAB_ERROR",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class InvalidExpressionError(MathLabError):
    """Raised when an input expression fails restricted parsing or validation."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="INVALID_EXPRESSION",
            status_code=400,
            details=details,
        )


class UnsupportedOperationError(MathLabError):
    """Raised when an operation is not in the approved registry."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="UNSUPPORTED_OPERATION",
            status_code=400,
            details=details,
        )


class ComputationLimitError(MathLabError):
    """Raised when an expression or execution exceeds resource/time limits."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="COMPUTATION_LIMIT_EXCEEDED",
            status_code=422,
            details=details,
        )


class DomainError(MathLabError):
    """Raised when a mathematical operation violates domain preconditions."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="MATHEMATICAL_DOMAIN_ERROR",
            status_code=422,
            details=details,
        )


class NotFoundError(MathLabError):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="NOT_FOUND",
            status_code=404,
            details=details,
        )
