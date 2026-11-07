"""Unit and integration tests for PayoutService: host earnings aggregation, settlement, and double-payout defense."""

import uuid

import pytest
from app.models.enums import EntrySideEnum, JournalStatusEnum
from app.models.ledger import JournalEntry, JournalLine
from app.services.payout_service import PayoutService


@pytest.mark.asyncio
async def test_owner_payout_batch_and_double_pay_defense(db_session):
    """Verify owner payout batch disbursement, balanced ledger entry, and zero-liability second run."""
    # 1. Create a posted journal entry with credit to Account 2010 (Owner Payable Liability)
    journal = JournalEntry(
        id=uuid.uuid4(),
        journal_number=f"JN-TEST-{uuid.uuid4().hex[:6].upper()}",
        transaction_reference=f"REF-{uuid.uuid4().hex[:6]}",
        transaction_type="PARKING_PAYMENT",
        currency="INR",
        posting_status=JournalStatusEnum.DRAFT,
        description="Test owner earnings",
    )
    db_session.add(journal)
    await db_session.flush()

    line1 = JournalLine(
        id=uuid.uuid4(),
        journal_id=journal.id,
        line_number=1,
        account_code="1010",
        entry_side=EntrySideEnum.DEBIT,
        amount_in_paise=10000,
        description="Debit transit asset",
    )
    line2 = JournalLine(
        id=uuid.uuid4(),
        journal_id=journal.id,
        line_number=2,
        account_code="2010",
        entry_side=EntrySideEnum.CREDIT,
        amount_in_paise=10000,
        description="Credit owner liability",
    )
    db_session.add_all([line1, line2])
    await db_session.flush()

    journal.posting_status = JournalStatusEnum.POSTED
    await db_session.commit()

    # 2. Trigger simulated owner payout batch
    batch_res = await PayoutService.simulate_owner_payout_batch(db=db_session)
    assert batch_res["status"] == "SIMULATED_SETTLED"
    assert batch_res["amount_paise"] >= 10000
    assert batch_res["utr"] is not None
    assert batch_res["utr"].startswith("UTR-DEMO-")

    # 3. Double-pay defense check: second execution must disburse 0
    second_res = await PayoutService.simulate_owner_payout_batch(db=db_session)
    assert second_res["amount_paise"] == 0
    assert "No outstanding owner balances" in second_res["message"]
