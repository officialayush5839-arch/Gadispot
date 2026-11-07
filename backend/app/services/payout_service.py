"""Owner payout batch processing and simulation service with double-entry ledger balance."""

from datetime import datetime, timezone
import logging
import secrets
from typing import Any
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenException
from app.models.enums import EntrySideEnum, JournalStatusEnum
from app.models.ledger import JournalEntry, JournalLine

logger = logging.getLogger("gadispot.payouts")


class PayoutService:
    """Manages host earnings payouts, batch execution, and double-entry ledger settlement."""

    @classmethod
    async def simulate_owner_payout_batch(
        cls,
        db: AsyncSession,
        owner_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Aggregate unpaid host balances (Account 2010), disburse funds, and record balanced ledger entry."""
        if settings.is_production or not settings.DEMO_PAYMENTS_ENABLED:
            raise ForbiddenException(
                detail="Payout simulation is forbidden in production environments.",
                code="PAYOUT_SIMULATION_FORBIDDEN",
            )

        # 1. Compute net outstanding owner payable balance
        query = text(
            """
            SELECT 
                COALESCE(SUM(CASE WHEN jl.entry_side = 'CREDIT' THEN jl.amount_in_paise ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN jl.entry_side = 'DEBIT' THEN jl.amount_in_paise ELSE 0 END), 0) AS net_payable_paise
            FROM journal_lines jl
            JOIN journal_entries je ON jl.journal_id = je.id
            WHERE jl.account_code = '2010' AND je.posting_status = 'POSTED'
            """
        )
        res = await db.execute(query)
        row = res.fetchone()
        net_payable = row[0] if row else 0

        now = datetime.now(timezone.utc)
        batch_id = f"PB-{secrets.token_hex(4).upper()}"

        if net_payable <= 0:
            return {
                "batch_id": batch_id,
                "amount_paise": 0,
                "currency": "INR",
                "status": "SIMULATED_SETTLED",
                "settled_at": now.isoformat(),
                "utr": None,
                "message": "No outstanding owner balances eligible for payout",
            }

        # 2. Create balanced payout journal entry
        # DEBIT Account 2010 (Owner Payable Liability)
        # CREDIT Account 1020 (Operating Bank Account)
        journal = JournalEntry(
            id=uuid.uuid4(),
            journal_number=f"JN-PAYOUT-{secrets.token_hex(4).upper()}",
            transaction_reference=batch_id,
            transaction_type="OWNER_PAYOUT",
            currency="INR",
            posting_status=JournalStatusEnum.DRAFT,
            description=f"Simulated owner payout batch disbursement for {batch_id}",
        )
        db.add(journal)
        await db.flush()

        debit_line = JournalLine(
            id=uuid.uuid4(),
            journal_id=journal.id,
            line_number=1,
            account_code="2010",
            entry_side=EntrySideEnum.DEBIT,
            amount_in_paise=net_payable,
            description=f"Debit Owner Payable Liability (Payout batch {batch_id})",
        )
        credit_line = JournalLine(
            id=uuid.uuid4(),
            journal_id=journal.id,
            line_number=2,
            account_code="1020",
            entry_side=EntrySideEnum.CREDIT,
            amount_in_paise=net_payable,
            description=f"Credit Operating Bank Account (Payout disbursement {batch_id})",
        )
        db.add(debit_line)
        db.add(credit_line)
        await db.flush()

        # 3. Post journal to trigger balance verification
        journal.posting_status = JournalStatusEnum.POSTED
        await db.flush()

        utr = f"UTR-DEMO-{secrets.token_hex(6).upper()}"
        logger.info(
            "Simulated payout batch %s settled: amount %d paise with UTR %s",
            batch_id,
            net_payable,
            utr,
        )

        return {
            "batch_id": batch_id,
            "amount_paise": net_payable,
            "currency": "INR",
            "status": "SIMULATED_SETTLED",
            "settled_at": now.isoformat(),
            "utr": utr,
            "message": f"Successfully disbursed ₹{net_payable / 100:.2f} across owner balances",
        }
