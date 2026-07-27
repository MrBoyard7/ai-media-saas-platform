"""Domain-level exceptions and their mapping to HTTP responses.

Keeping exceptions provider- and framework-agnostic in the `services` layer,
and translating them to HTTP only at the edge (`app.main`), keeps business
logic reusable from Celery tasks, CLI scripts and tests alike.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all business-rule violations."""

    status_code: int = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InsufficientCreditsError(DomainError):
    """Raised when a wallet does not hold enough credits to start a job."""

    status_code = 402  # Payment Required


class FeatureNotEntitledError(DomainError):
    """Raised when an organization's subscription plan does not include a feature."""

    status_code = 403


class ProviderNotAvailableError(DomainError):
    """Raised when no healthy adapter is registered for a requested capability."""

    status_code = 503


class OrganizationNotFoundError(DomainError):
    status_code = 404


class JobNotFoundError(DomainError):
    status_code = 404


class IdempotencyConflictError(DomainError):
    """Raised when a request is replayed with the same idempotency key but a different payload."""

    status_code = 409
