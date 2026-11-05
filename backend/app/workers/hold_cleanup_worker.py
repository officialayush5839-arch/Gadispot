"""Two-Tier 480s Hold Expiration Engine.

Tier 1: Periodic background worker sweep using SELECT ... FOR UPDATE SKIP LOCKED.
Tier 2: Opportunistic inline sweep executed immediately before new hold creation.

Invariant: Expired holds are transitioned to EXPIRED_HOLD, freeing the PostgreSQL
GiST temporal exclusion constraint without creating transaction lock contention.
"""

import logging
import uuid
from datetime import datetime, timezone

from app.models.enums import ReservationStatusEnum
from app.models.reservations import SpaceReservation
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("gadispot.workers.hold_cleanup")


async def sweep_expired_holds_batch(
    db: AsyncSession,
    batch_size: int = 100,
) -> int:
    """Tier 1: Background sweep transition of expired holds using FOR UPDATE SKIP LOCKED.

    Returns the number of expired holds transitioned to EXPIRED_HOLD.
    """
    now = datetime.now(timezone.utc)

    # 1. Select candidate IDs with SKIP LOCKED to prevent blocking concurrent booking transactions
    stmt = (
        select(SpaceReservation.id)
        .where(
            SpaceReservation.status == ReservationStatusEnum.ACTIVE_HOLD,
            SpaceReservation.hold_expires_at <= now,
        )
        .with_for_update(skip_locked=True)
        .limit(batch_size)
    )
    result = await db.execute(stmt)
    expired_ids = result.scalars().all()

    if not expired_ids:
        return 0

    # 2. Update status to EXPIRED_HOLD
    upd_stmt = (
        update(SpaceReservation)
        .where(SpaceReservation.id.in_(expired_ids))
        .values(
            status=ReservationStatusEnum.EXPIRED_HOLD,
            updated_at=now,
        )
    )
    await db.execute(upd_stmt)
    await db.flush()

    logger.info("Tier 1 hold sweep: transitioned %d expired holds to EXPIRED_HOLD", len(expired_ids))
    return len(expired_ids)


async def sweep_expired_holds_for_space(
    db: AsyncSession,
    parking_space_id: uuid.UUID,
) -> int:
    """Tier 2: Opportunistic inline sweep for a specific physical parking space.

    Invoked prior to new hold acquisition to instantly prune any expired hold on that space.
    """
    now = datetime.now(timezone.utc)

    stmt = (
        select(SpaceReservation.id)
        .where(
            SpaceReservation.parking_space_id == parking_space_id,
            SpaceReservation.status == ReservationStatusEnum.ACTIVE_HOLD,
            SpaceReservation.hold_expires_at <= now,
        )
        .with_for_update(skip_locked=True)
    )
    result = await db.execute(stmt)
    expired_ids = result.scalars().all()

    if not expired_ids:
        return 0

    upd_stmt = (
        update(SpaceReservation)
        .where(SpaceReservation.id.in_(expired_ids))
        .values(
            status=ReservationStatusEnum.EXPIRED_HOLD,
            updated_at=now,
        )
    )
    await db.execute(upd_stmt)
    await db.flush()

    logger.debug(
        "Tier 2 inline sweep: space %s freed (%d expired holds cleared)",
        parking_space_id,
        len(expired_ids),
    )
    return len(expired_ids)
