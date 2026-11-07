"""Domain exception classes and RFC 7807 Problem Details response builders."""

from datetime import datetime, timezone
from typing import Any

from fastapi.responses import JSONResponse

DEFAULT_ERROR_BASE_URI = "https://api.gadispot.in/errors"


class DomainException(Exception):
    """Base class for all business domain exceptions."""

    def __init__(
        self,
        detail: str,
        title: str = "Domain Error",
        status_code: int = 400,
        code: str = "DOMAIN_ERROR",
        type_uri: str | None = None,
        instance: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(detail)
        self.detail = detail
        self.title = title
        self.status_code = status_code
        self.code = code
        self.type_uri = type_uri or f"{DEFAULT_ERROR_BASE_URI}/{code.upper()}"
        self.instance = instance
        self.extra = extra or {}


class EntityNotFoundException(DomainException):
    """Raised when a requested resource does not exist (404 Not Found)."""

    def __init__(
        self,
        detail: str = "The requested resource was not found.",
        title: str = "Resource Not Found",
        code: str = "ENTITY_NOT_FOUND",
        instance: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            title=title,
            status_code=404,
            code=code,
            instance=instance,
            extra=extra,
        )


class ConflictException(DomainException):
    """Raised when an operation conflicts with current state or invariant (409 Conflict)."""

    def __init__(
        self,
        detail: str = "Operation conflicts with current system state.",
        title: str = "State Conflict",
        code: str = "CONFLICT",
        instance: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            title=title,
            status_code=409,
            code=code,
            instance=instance,
            extra=extra,
        )


class ValidationException(DomainException):
    """Raised when user input fails domain business validation (422 Unprocessable Entity)."""

    def __init__(
        self,
        detail: str = "Validation failed for one or more fields.",
        title: str = "Validation Error",
        code: str = "VALIDATION_ERROR",
        errors: list[dict[str, Any]] | None = None,
        instance: str | None = None,
    ):
        extra = {"errors": errors} if errors else {}
        super().__init__(
            detail=detail,
            title=title,
            status_code=422,
            code=code,
            instance=instance,
            extra=extra,
        )


class UnauthorizedException(DomainException):
    """Raised when authentication credentials are missing or invalid (401 Unauthorized)."""

    def __init__(
        self,
        detail: str = "Authentication credentials were not provided or are invalid.",
        title: str = "Unauthorized",
        code: str = "UNAUTHORIZED",
        instance: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            title=title,
            status_code=401,
            code=code,
            instance=instance,
            extra=extra,
        )


class ForbiddenException(DomainException):
    """Raised when authenticated user lacks permissions for this resource (403 Forbidden)."""

    def __init__(
        self,
        detail: str = "You do not have permission to perform this action.",
        title: str = "Forbidden",
        code: str = "FORBIDDEN",
        instance: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            title=title,
            status_code=403,
            code=code,
            instance=instance,
            extra=extra,
        )


class ServiceUnavailableException(DomainException):
    """Raised when an essential dependency (DB, Redis) is unavailable (503 Service Unavailable)."""

    def __init__(
        self,
        detail: str = "A required upstream service is currently unavailable.",
        title: str = "Service Unavailable",
        code: str = "SERVICE_UNAVAILABLE",
        instance: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(
            detail=detail,
            title=title,
            status_code=503,
            code=code,
            instance=instance,
            extra=extra,
        )


def build_problem_details_payload(
    status: int,
    title: str,
    detail: str,
    code: str,
    type_uri: str | None = None,
    instance: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct RFC 7807 problem details dictionary."""
    payload: dict[str, Any] = {
        "type": type_uri or f"{DEFAULT_ERROR_BASE_URI}/{code.upper()}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if instance:
        payload["instance"] = instance
    if extra:
        payload.update(extra)
    return payload


def create_problem_details_response(
    status: int,
    title: str,
    detail: str,
    code: str,
    type_uri: str | None = None,
    instance: str | None = None,
    extra: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build a compliant RFC 7807 JSONResponse with media type application/problem+json."""
    payload = build_problem_details_payload(
        status=status,
        title=title,
        detail=detail,
        code=code,
        type_uri=type_uri,
        instance=instance,
        extra=extra,
    )
    return JSONResponse(
        status_code=status,
        content=payload,
        media_type="application/problem+json",
        headers=headers,
    )
