"""Role-Based Access Control (RBAC) and Insecure Direct Object Reference (IDOR) Shield."""

import uuid

from fastapi import Depends

from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.exceptions import ForbiddenException
from app.models.enums import UserRoleEnum
from app.models.users import User


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
