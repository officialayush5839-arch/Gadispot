"""Security and operational audit logging service."""

import logging
import uuid
from typing import Any

from app.models.audit import AuditEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("gadispot.audit")


class AuditService:
    """Service to record tamper-resistant security and operational events."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditEvent:
        """Create and append an immutable audit log entry."""
        event = AuditEvent(
            actor_id=actor_id,
            action=action.upper().strip(),
            resource_type=resource_type.upper().strip(),
            resource_id=str(resource_id),
            details=details or {},
            ip_address=ip_address,
        )
        db.add(event)
        await db.flush()
        logger.info(
            "AUDIT [%s] by %s on %s:%s",
            event.action,
            actor_id or "SYSTEM",
            event.resource_type,
            event.resource_id,
        )
        return event

    @staticmethod
    async def list_events_for_resource(
        db: AsyncSession,
        resource_type: str,
        resource_id: str,
        limit: int = 50,
    ) -> list[AuditEvent]:
        """Fetch audit trail history for a specific entity."""
        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.resource_type == resource_type.upper().strip(),
                AuditEvent.resource_id == str(resource_id),
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
