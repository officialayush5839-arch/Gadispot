"""
Concurrent Deadlock Freedom & Multi-Worker Adversarial Testing.
Empirically tests that the Zero Child Lock Protocol and deterministic parent locking
produce ZERO deadlocks (DeadlockDetectedError) under high concurrency without exception swallowing.
"""

import asyncio
import pytest
import asyncpg
from asyncpg.exceptions import DeadlockDetectedError, RaiseError


async def create_balanced_journal(pool, ref="CONC-001", amount=10000):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO journal_entries (journal_number, transaction_reference, transaction_type, description)
            VALUES ($1, $2, 'PARKING_PAYMENT', $3)
            RETURNING id
            """,
            f"JN-{ref}",
            ref,
            f"Concurrent Journal {ref}",
        )
        j_id = row["id"]
        await conn.execute(
            """
            INSERT INTO journal_lines (journal_id, line_number, account_code, entry_side, amount_in_paise)
            VALUES 
                ($1, 1, '1010', 'DEBIT', $2),
                ($1, 2, '2010', 'CREDIT', $2)
            """,
            j_id,
            amount,
        )
        return j_id


async def test_concurrent_posting_and_line_mutation_zero_deadlocks(pg_pool):
    """
    Launch concurrent workers simultaneously executing inside explicit transactions:
    1. Posting workers attempting to post a draft journal (Transaction A)
    2. Line updating workers modifying lines on the draft journal (Transaction B)
    3. Line inserting workers adding lines to the draft journal (Transaction C)

    Under the old V2.3.1 protocol, this reliably triggered DeadlockDetectedError.
    Under the Zero Child Lock Protocol, ZERO deadlocks occur.
    All worker outcomes are explicitly tracked and asserted — NO exception swallowing.
    """
    j_id = await create_balanced_journal(pg_pool, "DEADLOCK-PROBE-01", 10000)

    deadlock_errors = []
    unexpected_errors = []
    worker_outcomes = []

    async def worker_poster(worker_id):
        try:
            async with pg_pool.acquire() as conn:
                async with conn.transaction():
                    tag = await conn.execute(
                        "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1 AND posting_status = 'DRAFT'",
                        j_id,
                    )
                    if tag == "UPDATE 1":
                        worker_outcomes.append(("poster", worker_id, "POSTED"))
                    else:
                        worker_outcomes.append(("poster", worker_id, "ALREADY_POSTED"))
        except DeadlockDetectedError as e:
            deadlock_errors.append(e)
        except RaiseError as e:
            if "Immutable Ledger Violation" in str(e):
                worker_outcomes.append(("poster", worker_id, "REJECTED_IMMUTABLE"))
            else:
                unexpected_errors.append(("poster", worker_id, e))
        except Exception as e:
            unexpected_errors.append(("poster", worker_id, e))

    async def worker_line_updater(worker_id, line_no, new_desc):
        try:
            async with pg_pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "UPDATE journal_lines SET description = $1 WHERE journal_id = $2 AND line_number = $3",
                        new_desc,
                        j_id,
                        line_no,
                    )
                    worker_outcomes.append(("updater", worker_id, "COMMITTED"))
        except DeadlockDetectedError as e:
            deadlock_errors.append(e)
        except RaiseError as e:
            if "Immutable Ledger Violation" in str(e):
                worker_outcomes.append(("updater", worker_id, "REJECTED_IMMUTABLE"))
            else:
                unexpected_errors.append(("updater", worker_id, e))
        except Exception as e:
            unexpected_errors.append(("updater", worker_id, e))

    async def worker_line_inserter(worker_id, line_no):
        try:
            async with pg_pool.acquire() as conn:
                async with conn.transaction():
                    # Insert balanced lines
                    await conn.execute(
                        """
                        INSERT INTO journal_lines (journal_id, line_number, account_code, entry_side, amount_in_paise, description)
                        VALUES 
                            ($1, $2, '1020', 'DEBIT', 500, 'Concurrent Debit'),
                            ($1, $3, '2020', 'CREDIT', 500, 'Concurrent Credit')
                        """,
                        j_id,
                        line_no,
                        line_no + 100,
                    )
                    worker_outcomes.append(("inserter", worker_id, "COMMITTED"))
        except DeadlockDetectedError as e:
            deadlock_errors.append(e)
        except RaiseError as e:
            if "Immutable Ledger Violation" in str(e):
                worker_outcomes.append(("inserter", worker_id, "REJECTED_IMMUTABLE"))
            else:
                unexpected_errors.append(("inserter", worker_id, e))
        except Exception as e:
            unexpected_errors.append(("inserter", worker_id, e))

    # Launch 10 simultaneous workers against the same journal with explicit IDs
    tasks = [
        worker_poster(1),
        worker_line_updater(2, 1, "Desc Update 1"),
        worker_line_updater(3, 2, "Desc Update 2"),
        worker_line_inserter(4, 3),
        worker_line_inserter(5, 5),
        worker_poster(6),
        worker_line_updater(7, 1, "Desc Update 3"),
        worker_line_updater(8, 2, "Desc Update 4"),
        worker_line_inserter(9, 7),
        worker_poster(10),
    ]

    await asyncio.gather(*tasks)

    # CRITICAL INVARIANT 1: Zero DeadlockDetectedError occurrences!
    assert len(deadlock_errors) == 0, f"Deadlock occurred: {deadlock_errors}"

    # CRITICAL INVARIANT 2: Zero unexpected errors!
    assert len(unexpected_errors) == 0, f"Unexpected errors detected: {unexpected_errors}"

    # CRITICAL INVARIANT 3: Every worker finished with a known valid outcome
    assert len(worker_outcomes) == len(tasks), (
        f"Worker outcome count mismatch: finished {len(worker_outcomes)} out of {len(tasks)}"
    )

    # CRITICAL INVARIANT 4: Exactly one poster transitioned the journal to POSTED
    postings_completed = [
        res for w_type, wid, res in worker_outcomes if w_type == "poster" and res == "POSTED"
    ]
    assert len(postings_completed) == 1, (
        f"Expected exactly 1 POSTED transition, got {len(postings_completed)}: {worker_outcomes}"
    )

    # Verify journal final state in database
    async with pg_pool.acquire() as conn:
        entry = await conn.fetchrow(
            "SELECT posting_status, posted_at FROM journal_entries WHERE id = $1",
            j_id,
        )
        assert entry["posting_status"] == "POSTED"
        assert entry["posted_at"] is not None

        # Verify mathematical balance in persisted database lines
        totals = await conn.fetchrow(
            """
            SELECT 
                COALESCE(SUM(CASE WHEN entry_side = 'DEBIT' THEN amount_in_paise ELSE 0 END), 0) AS debits,
                COALESCE(SUM(CASE WHEN entry_side = 'CREDIT' THEN amount_in_paise ELSE 0 END), 0) AS credits,
                COUNT(*) AS count
            FROM journal_lines
            WHERE journal_id = $1
            """,
            j_id,
        )
        assert totals["debits"] == totals["credits"], (
            f"Debits ({totals['debits']}) do not equal Credits ({totals['credits']})"
        )
        assert totals["count"] >= 2, f"Line count {totals['count']} < 2"


async def test_cross_journal_line_movement_concurrency_zero_deadlocks(pg_pool):
    """
    Launch opposing concurrent transactions moving lines between Journal A and Journal B.
    Deterministic parent ID sorting (OLD.journal_id < NEW.journal_id) must prevent deadlocks.
    Transactions execute inside explicit transaction boundaries with full outcome tracking.
    """
    j_a = await create_balanced_journal(pg_pool, "CROSS-A", 5000)
    j_b = await create_balanced_journal(pg_pool, "CROSS-B", 5000)

    deadlock_errors = []
    unexpected_errors = []
    worker_outcomes = []

    async def move_a_to_b(worker_id):
        try:
            async with pg_pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "UPDATE journal_lines SET journal_id = $1, line_number = $2 WHERE journal_id = $3 AND line_number = 1",
                        j_b,
                        90 + worker_id,
                        j_a,
                    )
                    worker_outcomes.append(("move_a_to_b", worker_id, "COMMITTED"))
        except DeadlockDetectedError as e:
            deadlock_errors.append(e)
        except Exception as e:
            unexpected_errors.append(("move_a_to_b", worker_id, e))

    async def move_b_to_a(worker_id):
        try:
            async with pg_pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "UPDATE journal_lines SET journal_id = $1, line_number = $2 WHERE journal_id = $3 AND line_number = 1",
                        j_a,
                        80 + worker_id,
                        j_b,
                    )
                    worker_outcomes.append(("move_b_to_a", worker_id, "COMMITTED"))
        except DeadlockDetectedError as e:
            deadlock_errors.append(e)
        except Exception as e:
            unexpected_errors.append(("move_b_to_a", worker_id, e))

    tasks = [
        move_a_to_b(1),
        move_b_to_a(2),
        move_a_to_b(3),
        move_b_to_a(4),
    ]
    await asyncio.gather(*tasks)

    # CRITICAL INVARIANT: Zero deadlocks between opposing line moves
    assert len(deadlock_errors) == 0, f"Deadlock occurred during cross-journal moves: {deadlock_errors}"
    assert len(unexpected_errors) == 0, f"Unexpected error during cross-journal moves: {unexpected_errors}"
    assert len(worker_outcomes) == len(tasks)
