"""Core backend module containing configuration, security, exceptions, and logging."""

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db, get_redis
from app.core.exceptions import (
    ConflictException,
    DomainException,
    EntityNotFoundException,
    ForbiddenException,
    ServiceUnavailableException,
    UnauthorizedException,
    ValidationException,
    create_problem_details_response,
)
from app.core.logging import logger, setup_logging
from app.core.security import generate_request_id, is_valid_uuid

__all__ = [
    "ConflictException",
    "DomainException",
    "EntityNotFoundException",
    "ForbiddenException",
    "ServiceUnavailableException",
    "Settings",
    "UnauthorizedException",
    "ValidationException",
    "create_problem_details_response",
    "generate_request_id",
    "get_db",
    "get_redis",
    "get_settings",
    "is_valid_uuid",
    "logger",
    "setup_logging",
]
