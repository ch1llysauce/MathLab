"""Shared types and helpers for the verification engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VerificationCheck:
    """Outcome of a single verification check."""

    check_type: str  # "symbolic" | "numerical" | "substitution" | "cross_method"
    name: str
    passed: bool | None  # True=passed, False=failed/refuted, None=inconclusive/not_applicable
    message: str
    residual: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_type": self.check_type,
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "residual": self.residual,
            "details": dict(self.details),
        }
