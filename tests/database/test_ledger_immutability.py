"""
Tests for Ledger Immutability, Journal Balancing & Mutation Rejection Triggers.
Verifies PostgreSQL 16 triggers: fn_verify_journal_balance, fn_prevent_posted_lines_modification,
and fn_prevent_posted_journal_modification under canonical 14-table schema.
"""

import pytest
import asyncpg
from asyncpg.exceptions import RaiseError


async def create_draft_journal(conn, ref="REF-001"):
    row = await conn.fetchrow(
        """
        INSERT INTO journal_entries (journal_number, transaction_reference, transaction_type, description)
        VALUES ($1, $2, 'PARKING_PAYMENT', $3)
        RETURNING id
        """,
        f"JN-{ref}",
        ref,
        f"Test Journal {ref}",
    )
    return row["id"]


async def insert_line(conn, j_id, line_no, account, side, amount):
    await conn.execute(
        """
        INSERT INTO journal_lines (journal_id, line_number, account_code, entry_side, amount_in_paise, description)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        j_id,
        line_no,
        account,
        side,
        amount,
        f"Line {line_no}",
    )


async def test_balanced_journal_posts_successfully(pg_pool):
    """Balanced journal (Debits == Credits, lines >= 2) must transition to POSTED."""
    async with pg_pool.acquire() as conn:
        j_id = await create_draft_journal(conn, "BAL-001")
        await insert_line(conn, j_id, 1, "1010", "DEBIT", 9000)
        await insert_line(conn, j_id, 2, "2010", "CREDIT", 9000)

        # Post journal
        await conn.execute(
            "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1",
            j_id,
        )

        entry = await conn.fetchrow(
            "SELECT posting_status, posted_at FROM journal_entries WHERE id = $1",
            j_id,
        )
        assert entry["posting_status"] == "POSTED"
        assert entry["posted_at"] is not None


async def test_unbalanced_journal_rejected(pg_pool):
    """Unbalanced journal must be rejected with exception containing 'does not balance'."""
    async with pg_pool.acquire() as conn:
        j_id = await create_draft_journal(conn, "UNBAL-001")
        await insert_line(conn, j_id, 1, "1010", "DEBIT", 9000)
        await insert_line(conn, j_id, 2, "2010", "CREDIT", 8500)

        with pytest.raises(RaiseError) as exc_info:
            await conn.execute(
                "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1",
                j_id,
            )

        assert "does not balance" in str(exc_info.value)


async def test_single_line_journal_rejected(pg_pool):
    """Single-line journal must be rejected with message 'Must contain at least 2 lines'."""
    async with pg_pool.acquire() as conn:
        j_id = await create_draft_journal(conn, "SINGLE-001")
        await insert_line(conn, j_id, 1, "1010", "DEBIT", 5000)

        with pytest.raises(RaiseError) as exc_info:
            await conn.execute(
                "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1",
                j_id,
            )

        assert "Must contain at least 2 lines" in str(exc_info.value)


async def test_cannot_modify_posted_journal_entry(pg_pool):
    """Modifying metadata on a POSTED journal must be rejected."""
    async with pg_pool.acquire() as conn:
        j_id = await create_draft_journal(conn, "IMMUT-001")
        await insert_line(conn, j_id, 1, "1010", "DEBIT", 5000)
        await insert_line(conn, j_id, 2, "2010", "CREDIT", 5000)
        await conn.execute(
            "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1",
            j_id,
        )

        with pytest.raises(RaiseError) as exc_info:
            await conn.execute(
                "UPDATE journal_entries SET description = 'Tampered' WHERE id = $1",
                j_id,
            )

        assert "Immutable Ledger Violation: Posted journal" in str(exc_info.value)


async def test_cannot_delete_posted_journal_entry(pg_pool):
    """Deleting a POSTED journal entry must be rejected."""
    async with pg_pool.acquire() as conn:
        j_id = await create_draft_journal(conn, "DEL-001")
        await insert_line(conn, j_id, 1, "1010", "DEBIT", 5000)
        await insert_line(conn, j_id, 2, "2010", "CREDIT", 5000)
        await conn.execute(
            "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1",
            j_id,
        )

        with pytest.raises(RaiseError) as exc_info:
            await conn.execute(
                "DELETE FROM journal_entries WHERE id = $1", j_id
            )

        assert "Immutable Ledger Violation: Posted journal" in str(exc_info.value)


async def test_cannot_insert_line_into_posted_journal(pg_pool):
    """Inserting new lines into an already POSTED journal must be rejected."""
    async with pg_pool.acquire() as conn:
        j_id = await create_draft_journal(conn, "INS-001")
        await insert_line(conn, j_id, 1, "1010", "DEBIT", 5000)
        await insert_line(conn, j_id, 2, "2010", "CREDIT", 5000)
        await conn.execute(
            "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1",
            j_id,
        )

        with pytest.raises(RaiseError) as exc_info:
            await insert_line(conn, j_id, 3, "1020", "DEBIT", 1000)

        assert "Cannot insert lines into POSTED journal" in str(exc_info.value)


async def test_cannot_update_line_on_posted_journal(pg_pool):
    """Updating amount or account on a line belonging to a POSTED journal must be rejected."""
    async with pg_pool.acquire() as conn:
        j_id = await create_draft_journal(conn, "UPD-001")
        await insert_line(conn, j_id, 1, "1010", "DEBIT", 5000)
        await insert_line(conn, j_id, 2, "2010", "CREDIT", 5000)
        await conn.execute(
            "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1",
            j_id,
        )

        with pytest.raises(RaiseError) as exc_info:
            await conn.execute(
                "UPDATE journal_lines SET amount_in_paise = 9999 WHERE journal_id = $1 AND line_number = 1",
                j_id,
            )

        assert "Cannot update lines on POSTED journal" in str(exc_info.value)


async def test_cannot_delete_line_from_posted_journal(pg_pool):
    """Deleting lines from a POSTED journal must be rejected."""
    async with pg_pool.acquire() as conn:
        j_id = await create_draft_journal(conn, "DELLINE-001")
        await insert_line(conn, j_id, 1, "1010", "DEBIT", 5000)
        await insert_line(conn, j_id, 2, "2010", "CREDIT", 5000)
        await conn.execute(
            "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1",
            j_id,
        )

        with pytest.raises(RaiseError) as exc_info:
            await conn.execute(
                "DELETE FROM journal_lines WHERE journal_id = $1 AND line_number = 1",
                j_id,
            )

        assert "Cannot delete lines from POSTED journal" in str(exc_info.value)


async def test_cannot_move_line_out_of_or_into_posted_journal(pg_pool):
    """Moving a line from a POSTED journal into a DRAFT journal or vice versa must be rejected."""
    async with pg_pool.acquire() as conn:
        j_posted = await create_draft_journal(conn, "MOVE-POSTED")
        await insert_line(conn, j_posted, 1, "1010", "DEBIT", 5000)
        await insert_line(conn, j_posted, 2, "2010", "CREDIT", 5000)
        await conn.execute(
            "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1",
            j_posted,
        )

        j_draft = await create_draft_journal(conn, "MOVE-DRAFT")
        await insert_line(conn, j_draft, 1, "1010", "DEBIT", 2000)

        # 1. Attempt to move line from posted to draft
        with pytest.raises(RaiseError) as exc_info1:
            await conn.execute(
                "UPDATE journal_lines SET journal_id = $1 WHERE journal_id = $2 AND line_number = 1",
                j_draft,
                j_posted,
            )
        assert "Cannot move line into or out of POSTED journal" in str(exc_info1.value)

        # 2. Attempt to move line from draft into posted
        with pytest.raises(RaiseError) as exc_info2:
            await conn.execute(
                "UPDATE journal_lines SET journal_id = $1 WHERE journal_id = $2 AND line_number = 1",
                j_posted,
                j_draft,
            )
        assert "Cannot move line into or out of POSTED journal" in str(exc_info2.value)
