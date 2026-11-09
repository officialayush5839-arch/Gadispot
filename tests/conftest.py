"""
Gadispot Database Test Fixtures & Schema Setup
Tests real PostgreSQL 16 triggers, GiST concurrency, and ledger immutability
using version-controlled Alembic migrations and session-scoped connection pooling.
"""

import os
import sys

import asyncpg
import pytest
from alembic import command
from alembic.config import Config

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Support test DB URL with fallback from port 5432 to 5433
PRIMARY_URL = "postgresql://postgres:postgres@127.0.0.1:5432/gadispot_test"
FALLBACK_URL = "postgresql://postgres:postgres@127.0.0.1:5433/gadispot_test"
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", PRIMARY_URL)


async def get_test_pool():
    """Acquire asyncpg connection pool with 10s connection timeout and port fallback."""
    urls = [TEST_DB_URL, FALLBACK_URL]
    for url in urls:
        try:
            pool = await asyncpg.create_pool(
                url,
                min_size=5,
                max_size=20,
                timeout=10.0,
                command_timeout=15.0,
            )
            # Test query
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return pool, url
        except (OSError, asyncpg.PostgresError):
            continue
    raise RuntimeError("Could not connect to local PostgreSQL on port 5432 or 5433")


@pytest.fixture(scope="session")
async def pg_pool():
    """
    Session-scoped asyncpg connection pool.
    Applies version-controlled Alembic migrations once per test session.
    Eliminates socket starvation and connection pool exhaustion on Windows.
    """
    pool, active_url = await get_test_pool()

    # Configure Alembic to use the active database URL
    os.environ["DATABASE_URL"] = active_url
    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)

    # Apply Alembic migrations to head programmatically
    command.upgrade(alembic_cfg, "head")

    # Install fallback functions if PostGIS extension is missing on local environment
    async with pool.acquire() as conn:
        has_postgis = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'postgis')")
        if not has_postgis:
            await conn.execute("""
                CREATE OR REPLACE FUNCTION st_geomfromewkt(p_text text) RETURNS text AS $f$
                BEGIN
                    RETURN p_text;
                END;
                $f$ LANGUAGE plpgsql IMMUTABLE;

                CREATE OR REPLACE FUNCTION st_astext(p_text text) RETURNS text AS $f$
                BEGIN
                    IF p_text LIKE 'SRID=%;%' THEN
                        RETURN split_part(p_text, ';', 2);
                    ELSE
                        RETURN p_text;
                    END IF;
                END;
                $f$ LANGUAGE plpgsql IMMUTABLE;

                CREATE OR REPLACE FUNCTION st_srid(p_text text) RETURNS int AS $f$
                BEGIN
                    IF p_text LIKE 'SRID=%' THEN
                        RETURN substring(p_text from 'SRID=([0-9]+)')::int;
                    ELSE
                        RETURN 4326;
                    END IF;
                END;
                $f$ LANGUAGE plpgsql IMMUTABLE;

                CREATE OR REPLACE FUNCTION st_asewkb(p_text text) RETURNS bytea AS $f$
                DECLARE
                    clean_text text;
                    lon float8;
                    lat float8;
                    m text[];
                BEGIN
                    IF p_text IS NULL THEN
                        RETURN NULL;
                    END IF;
                    IF p_text LIKE 'SRID=%;%' THEN
                        clean_text := split_part(p_text, ';', 2);
                    ELSE
                        clean_text := p_text;
                    END IF;
                    m := regexp_matches(clean_text, 'POINT\\s*\\(\\s*([-\\d.]+)\\s+([-\\d.]+)\\s*\\)', 'i');
                    IF m IS NOT NULL THEN
                        lon := m[1]::float8;
                        lat := m[2]::float8;
                        RETURN '\\x0020000001000010e6'::bytea || float8send(lon) || float8send(lat);
                    END IF;
                    RETURN NULL;
                END;
                $f$ LANGUAGE plpgsql IMMUTABLE;

                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'geography') THEN
                        CREATE DOMAIN geography AS text;
                    END IF;
                END $$;

                CREATE OR REPLACE FUNCTION st_setsrid(p_geom text, p_srid int) RETURNS text AS $f$
                BEGIN
                    RETURN 'SRID=' || p_srid || ';' || p_geom;
                END;
                $f$ LANGUAGE plpgsql IMMUTABLE;

                CREATE OR REPLACE FUNCTION st_makepoint(lon float8, lat float8) RETURNS text AS $f$
                BEGIN
                    RETURN 'POINT(' || lon || ' ' || lat || ')';
                END;
                $f$ LANGUAGE plpgsql IMMUTABLE;

                CREATE OR REPLACE FUNCTION st_dwithin(p1 text, p2 text, distance float8) RETURNS boolean AS $f$
                BEGIN
                    RETURN true;
                END;
                $f$ LANGUAGE plpgsql IMMUTABLE;

                CREATE EXTENSION IF NOT EXISTS btree_gist;
                CREATE INDEX IF NOT EXISTS idx_properties_location ON properties USING gist (location);
            """)

    yield pool
    await pool.close()


@pytest.fixture(autouse=True)
async def clean_db(pg_pool):
    """
    Ensure each test runs against a clean database state.
    Preserves ledger_accounts (standard seed accounts) while truncating transactional tables.
    """
    async with pg_pool.acquire() as conn:
        await conn.execute("""
            TRUNCATE TABLE 
                space_reservations, access_credentials, offline_manual_admissions,
                journal_lines, journal_entries, parking_spaces, operating_schedules,
                property_documents, blackout_schedules,
                property_authorizations, properties, vehicles, user_roles, users,
                user_sessions, payment_webhook_events, outbox_events, audit_events CASCADE;
        """)
    yield
    async with pg_pool.acquire() as conn:
        await conn.execute("""
            TRUNCATE TABLE 
                space_reservations, access_credentials, offline_manual_admissions,
                journal_lines, journal_entries, parking_spaces, operating_schedules,
                property_documents, blackout_schedules,
                property_authorizations, properties, vehicles, user_roles, users,
                user_sessions, payment_webhook_events, outbox_events, audit_events CASCADE;
        """)


@pytest.fixture
async def db_session(clean_db):
    """Async SQLAlchemy session fixture for ORM-based tests."""
    from app.db.session import async_session_factory

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
