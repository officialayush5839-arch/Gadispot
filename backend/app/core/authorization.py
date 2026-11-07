"""Role-Based Access Control (RBAC) and Insecure Direct Object Reference (IDOR) Shield."""

import uuid

from fastapi import Depends

from app.core.dependencies import get_current_user
from app.core.exceptions import ForbiddenException
from app.models.enums import UserRoleEnum
from app.models.users import User

# Canonical role alias mapping reconciling PRD terminology with database schema enums
ROLE_ALIASES: dict[str, str] = {
    "SPACE_OWNER": "OWNER",
    "SECURITY_GUARD": "GUARD",
    "OPS": "OPERATIONS",
    "OWNER": "OWNER",
    "GUARD": "GUARD",
    "OPERATIONS": "OPERATIONS",
    "DRIVER": "DRIVER",
    "ADMIN": "ADMIN",
}


class RoleChecker:
    """Dependency callable verifying that the current user has at least one of the explicitly required roles."""

    def __init__(self, allowed_roles: list[UserRoleEnum | str]):
        self.allowed_roles: set[str] = set()
        for r in allowed_roles:
            val = r.value if hasattr(r, "value") else str(r)
            self.allowed_roles.add(val)
            if val in ROLE_ALIASES:
                self.allowed_roles.add(ROLE_ALIASES[val])

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        user_role_names = {r.role.value if hasattr(r.role, "value") else str(r.role) for r in user.roles}
        user_role_names.update({ROLE_ALIASES.get(r, r) for r in user_role_names})
        if not user_role_names.intersection(self.allowed_roles):
            raise ForbiddenException(
                detail=f"Access denied. User lacks required role. Allowed: {sorted(self.allowed_roles)}",
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
    user_role_names.update({ROLE_ALIASES.get(r, r) for r in user_role_names})
    is_privileged = bool(user_role_names.intersection({UserRoleEnum.ADMIN.value, UserRoleEnum.OPERATIONS.value}))

    if allow_privileged and is_privileged:
        return  # Operations and Admin have platform inspection clearance

    if user.id != resource_owner_id:
        raise ForbiddenException(
            detail="You are not authorized to access or mutate this resource.",
            title="Object Authorization Violation",
            code="IDOR_ACCESS_DENIED",
        )
