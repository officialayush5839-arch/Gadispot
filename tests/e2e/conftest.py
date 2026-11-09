"""Shared fixtures and opaque-box test harnesses for Phase 03 E2E testing."""

import os
import sys
import uuid
from collections.abc import AsyncGenerator

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend")
)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.security import create_access_token
from app.main import app
from app.models.enums import AccountStatus, UserRoleEnum
from app.models.users import User, UserRole


@pytest.fixture
def e2e_app():
    """FastAPI application instance for opaque-box testing."""
    return app


@pytest.fixture
async def e2e_client(e2e_app) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient fixture with raise_app_exceptions=False for true HTTP status code checking."""
    transport = ASGITransport(app=e2e_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def owner_user(db_session) -> tuple[User, dict[str, str]]:
    """Create and persist an authenticated Space Owner user with valid Bearer token."""
    phone = f"+9198{uuid.uuid4().hex[:8]}"
    user = User(
        phone_number=phone,
        full_name="E2E Space Owner",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    role = UserRole(user_id=user.id, role=UserRoleEnum.OWNER)
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        subject=str(user.id),
        claims={"roles": ["OWNER", "SPACE_OWNER"], "phone_number": phone},
    )
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


@pytest.fixture
async def ops_user(db_session) -> tuple[User, dict[str, str], str]:
    """Create and persist an Operations user with TOTP secret and valid Bearer token."""
    phone = f"+9199{uuid.uuid4().hex[:8]}"
    totp_secret = pyotp.random_base32()
    user = User(
        phone_number=phone,
        full_name="E2E Operations Officer",
        status=AccountStatus.ACTIVE,
        is_active=True,
        totp_secret=totp_secret,
        totp_enabled=True,
    )
    db_session.add(user)
    await db_session.flush()

    role = UserRole(user_id=user.id, role=UserRoleEnum.OPERATIONS)
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        subject=str(user.id),
        claims={"roles": ["OPERATIONS", "OPS"], "phone_number": phone},
    )
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers, totp_secret


@pytest.fixture
async def driver_user(db_session) -> tuple[User, dict[str, str]]:
    """Create and persist an authenticated Driver user with valid Bearer token."""
    phone = f"+9197{uuid.uuid4().hex[:8]}"
    user = User(
        phone_number=phone,
        full_name="E2E Driver",
        status=AccountStatus.ACTIVE,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    role = UserRole(user_id=user.id, role=UserRoleEnum.DRIVER)
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        subject=str(user.id),
        claims={"roles": ["DRIVER"], "phone_number": phone},
    )
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


def get_current_totp(secret: str) -> str:
    """Generate current 6-digit RFC 6238 TOTP code."""
    return pyotp.TOTP(secret).now()
