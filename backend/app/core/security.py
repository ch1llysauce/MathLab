"""Security utilities, input bounds, and controlled execution helpers."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Callable, TypeVar

from app.core.exceptions import ComputationLimitError, InvalidExpressionError

T = TypeVar("T")

MAX_EXPRESSION_LENGTH = 500
MAX_AST_DEPTH = 25
MAX_AST_NODES = 200
MAX_EXPONENT_ABS = 1000
MAX_MATRIX_DIM = 20
MAX_COMPUTATION_SECONDS = 5.0

FORBIDDEN_SUBSTRINGS = (
    "__",
    "import",
    "eval",
    "exec",
    "compile",
    "open",
    "lambda",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "breakpoint",
)


def validate_expression_bounds(expression: str) -> str:
    """Validate expression length and reject obvious code-execution patterns."""
    if not isinstance(expression, str):
        raise InvalidExpressionError("Expression must be a string.")

    cleaned = expression.strip()
    if not cleaned:
        raise InvalidExpressionError("Expression must not be empty.")

    if len(cleaned) > MAX_EXPRESSION_LENGTH:
        raise ComputationLimitError(
            f"Expression exceeds maximum length of {MAX_EXPRESSION_LENGTH} characters.",
            details={"max_length": MAX_EXPRESSION_LENGTH, "actual_length": len(cleaned)},
        )

    lowered = cleaned.lower()
    for token in FORBIDDEN_SUBSTRINGS:
        if token in lowered:
            raise InvalidExpressionError(
                f"Forbidden token '{token}' in expression.",
                details={"forbidden_token": token},
            )

    if any(ch in cleaned for ch in (";", "\n", "\r", "\\")):
        raise InvalidExpressionError("Control characters and statement separators are not allowed.")

    return cleaned


def run_with_timeout(
    func: Callable[..., T],
    *args: Any,
    timeout_seconds: float = MAX_COMPUTATION_SECONDS,
    **kwargs: Any,
) -> T:
    """Execute a computation with a bounded wait timeout."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func, *args, **kwargs)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
        future.cancel()
        raise ComputationLimitError(
            f"Computation exceeded the {timeout_seconds:.1f}s time limit.",
            details={"timeout_seconds": timeout_seconds},
        ) from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
