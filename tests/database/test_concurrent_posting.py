"""
Concurrent Deadlock Freedom & Multi-Worker Adversarial Testing.
Empirically tests that the Zero Child Lock Protocol and deterministic parent locking
produce ZERO deadlocks (DeadlockDetectedError) under high concurrency.
"""

import asyncio
import pytest
import asyncpg
from asyncpg.exceptions import DeadlockDetectedError, RaiseError

async def create_balanced_journal(pool, ref="CONC-001", amount=10000):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO journal_entries (transaction_reference, description) VALUES ($1, $2) RETURNING id",
            ref, f"Concurrent Journal {ref}"
        )
        j_id = row["id"]
        await conn.execute(
            """
            INSERT INTO journal_lines (journal_id, line_number, account_code, entry_side, amount_in_paise)
            VALUES 
                ($1, 1, '1010', 'DEBIT', $2),
                ($1, 2, '2010', 'CREDIT', $2)
            """,
            j_id, amount
        )
        return j_id

async def test_concurrent_posting_and_line_mutation_zero_deadlocks(pg_pool):
    """
    Launch concurrent workers simultaneously attempting to:
    1. Post a draft journal (Transaction A)
    2. Insert new lines into the draft journal (Transaction B)
    3. Update existing lines on the draft journal (Transaction C)
    
    Under the old protocol, this reliably triggered DeadlockDetectedError.
    Under the Zero Child Lock Protocol, zero deadlocks occur.
    """
    j_id = await create_balanced_journal(pg_pool, "DEADLOCK-PROBE-01", 10000)

    deadlock_errors = []
    success_postings = []
    rejected_mutations = []

    async def worker_poster():
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE journal_entries SET posting_status = 'POSTED' WHERE id = $1",
                    j_id
                )
                success_postings.append(True)
        except DeadlockDetectedError as e:
            deadlock_errors.append(e)
        except Exception as e:
            pass

    async def worker_line_updater(line_no, new_amount):
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE journal_lines SET amount_in_paise = $1 WHERE journal_id = $2 AND line_number = $3",
                    new_amount, j_id, line_no
                )
        except DeadlockDetectedError as e:
            deadlock_errors.append(e)
        except RaiseError as e:
            if "Immutable Ledger Violation" in str(e):
                rejected_mutations.append(e)
        except Exception:
            pass

    async def worker_line_inserter(line_no):
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO journal_lines (journal_id, line_number, account_code, entry_side, amount_in_paise)
                    VALUES ($1, $2, '1020', 'DEBIT', 500)
                    """,
                    j_id, line_no
                )
        except DeadlockDetectedError as e:
            deadlock_errors.append(e)
        except RaiseError as e:
            if "Immutable Ledger Violation" in str(e):
                rejected_mutations.append(e)
        except Exception:
            pass

    # Launch 10 simultaneous workers against the same journal
    tasks = [
        worker_poster(),
        worker_line_updater(1, 10500),
        worker_line_updater(2, 10500),
        worker_line_inserter(3),
        worker_line_inserter(4),
        worker_poster(),
        worker_line_updater(1, 11000),
        worker_line_updater(2, 11000),
        worker_line_inserter(5),
        worker_poster(),
    ]

    await asyncio.gather(*tasks)

    # CRITICAL INVARIANT: Zero DeadlockDetectedError occurrences!
    assert len(deadlock_errors) == 0, f"Deadlock occurred: {deadlock_errors}"

    # Verify journal final state in database
    async with pg_pool.acquire() as conn:
        status = await conn.fetchval("SELECT posting_status FROM journal_entries WHERE id = $1", j_id)
        assert status == "POSTED"

async def test_cross_journal_line_movement_concurrency_zero_deadlocks(pg_pool):
    """
    Launch opposing concurrent transactions moving lines between Journal A and Journal B.
    Deterministic parent ID sorting (OLD.journal_id < NEW.journal_id) must prevent deadlocks.
    """
    j_a = await create_balanced_journal(pg_pool, "CROSS-A", 5000)
    j_b = await create_balanced_journal(pg_pool, "CROSS-B", 5000)

    deadlock_errors = []

    async def move_a_to_b():
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE journal_lines SET journal_id = $1, line_number = 99 WHERE journal_id = $2 AND line_number = 1",
                    j_b, j_a
                )
        except DeadlockDetectedError as e:
            deadlock_errors.append(e)
        except Exception:
            pass

    async def move_b_to_a():
        try:
            async with pg_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE journal_lines SET journal_id = $1, line_number = 98 WHERE journal_id = $2 AND line_number = 1",
                    j_a, j_b
                )
        except DeadlockDetectedError as e:
            deadlock_errors.append(e)
        except Exception:
            pass

    tasks = [move_a_to_b(), move_b_to_a(), move_a_to_b(), move_b_to_a()]
    await asyncio.gather(*tasks)

    # CRITICAL INVARIANT: Zero deadlocks between opposing line moves
    assert len(deadlock_errors) == 0, f"Deadlock occurred during cross-journal moves: {deadlock_errors}"
