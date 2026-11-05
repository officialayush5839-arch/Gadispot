"""Role-Based Access Control (RBAC) and Insecure Direct Object Reference (IDOR) Shield."""

import uuid

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token, verify_token_type
from app.models.enums import UserRoleEnum
from app.models.users import User


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None, description="Bearer access token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency extracting, validating, and hydrating the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException(
            detail="Missing or malformed Authorization header. Bearer token required.",
            code="MISSING_BEARER_TOKEN",
        )

    raw_token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(raw_token)
    verify_token_type(payload, "access")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(detail="Token subject missing", code="INVALID_TOKEN")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(detail="Malformed UUID in token subject", code="INVALID_TOKEN")

    # Fetch user from database with roles eagerly loaded
    stmt = select(User).where(User.id == user_uuid).options(selectinload(User.roles))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(detail="User no longer exists", code="USER_NOT_FOUND")

    if not user.is_active:
        raise ForbiddenException(detail="User account is deactivated", code="ACCOUNT_DEACTIVATED")

    # Attach user to request state for downstream logging/telemetry
    request.state.user = user
    return user


class RoleChecker:
    """Dependency callable verifying that the current user has at least one of the required roles."""

    def __init__(self, allowed_roles: list[UserRoleEnum]):
        self.allowed_roles: set[str] = {r.value if hasattr(r, "value") else str(r) for r in allowed_roles}
        # ADMIN always possesses superuser privileges
        self.allowed_roles.add(UserRoleEnum.ADMIN.value)

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        user_role_names = {r.role.value if hasattr(r.role, "value") else str(r.role) for r in user.roles}
        if not user_role_names.intersection(self.allowed_roles):
            raise ForbiddenException(
                detail=f"Access denied. User lacks required role. Allowed: {list(self.allowed_roles)}",
                title="Insufficient Permissions",
                code="FORBIDDEN_ROLE",
            )
        return user


def require_roles(*roles: UserRoleEnum) -> RoleChecker:
    """Convenience helper to declare role constraints on API endpoints."""
    return RoleChecker(list(roles))


def verify_resource_ownership(
    user: User,
    resource_owner_id: uuid.UUID,
    allow_privileged: bool = True,
) -> None:
    """Enforce Object-Level Authorization preventing IDOR (Insecure Direct Object Reference) attacks.

    Ensures that the authenticated user either owns the target resource or is an Operations/Admin staff.
    """
    user_role_names = {r.role.value if hasattr(r.role, "value") else str(r.role) for r in user.roles}
    is_privileged = bool(user_role_names.intersection({UserRoleEnum.ADMIN.value, UserRoleEnum.OPERATIONS.value}))

    if allow_privileged and is_privileged:
        return  # Operations and Admin have platform inspection clearance

    if user.id != resource_owner_id:
        raise ForbiddenException(
            detail="You are not authorized to access or mutate this resource.",
            title="Object Authorization Violation",
            code="IDOR_ACCESS_DENIED",
        )
