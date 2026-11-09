"""SQLAlchemy declarative model for append-only administrative and security audit events."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    """Immutable, append-only security and operational audit trail."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @hybrid_property
    def entity_id(self) -> str:
        return self.resource_id

    @entity_id.setter
    def entity_id(self, val: Any) -> None:
        self.resource_id = str(val)

    @entity_id.expression
    def entity_id(cls):
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import UUID

        return cast(cls.resource_id, UUID)

    __table_args__ = (
        Index("idx_audit_events_created", "created_at"),
        Index("idx_audit_events_resource", "resource_type", "resource_id"),
    )
