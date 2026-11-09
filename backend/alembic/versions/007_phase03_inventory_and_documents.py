"""Phase 03 schema additions: optimistic locking, documents, blackouts, and compatibility function.

Revision ID: 007_phase03_inventory_and_documents
Revises: 006_revocation_and_mfa
Create Date: 2026-11-08 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_phase03_inventory_and_documents"
down_revision: str | None = "006_revocation_and_mfa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 0. Widen alembic_version.version_num column to support revision identifiers > 32 characters
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64);")

    # 1. Update property_authorizations with optimistic concurrency locking and tracking columns
    op.add_column(
        "property_authorizations",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
            comment="Optimistic concurrency control version counter.",
        ),
    )
    op.add_column(
        "property_authorizations",
        sa.Column(
            "rejection_reason_code",
            sa.String(64),
            nullable=True,
            comment="Standardized rejection category code.",
        ),
    )
    op.add_column(
        "property_authorizations",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="Timestamp of last authorization state modification.",
        ),
    )

    # 2. Create property_documents table
    op.create_table(
        "property_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_type",
            postgresql.ENUM(name="document_type_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("s3_key", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_property_documents_property_type",
        "property_documents",
        ["property_id", "document_type"],
    )

    # 3. Create blackout_schedules table
    op.create_table(
        "blackout_schedules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parking_space_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("parking_spaces.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("start_time < end_time", name="chk_blackout_time"),
    )
    op.create_index(
        "idx_blackout_schedules_property_time",
        "blackout_schedules",
        ["property_id", "start_time", "end_time"],
    )

    # 4. Ensure PostGIS/GiST index on properties location exists and relax vehicle_id requirement
    op.execute(
        """
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS btree_gist;
            CREATE INDEX IF NOT EXISTS idx_properties_location ON properties USING gist (location);
            ALTER TABLE space_reservations ALTER COLUMN vehicle_id DROP NOT NULL;
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END $$;
        """
    )

    # 5. Create stored function fn_check_vehicle_bay_compatibility
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_check_vehicle_bay_compatibility(
            p_vehicle_category vehicle_category_enum,
            p_bay_type VARCHAR(32),
            p_bay_length_m NUMERIC,
            p_bay_width_m NUMERIC,
            p_bay_height_m NUMERIC,
            p_bay_has_ev BOOLEAN,
            p_driver_req_ev BOOLEAN
        ) RETURNS BOOLEAN AS $$
        BEGIN
            -- Check EV charging requirement
            IF p_driver_req_ev AND NOT p_bay_has_ev THEN
                RETURN FALSE;
            END IF;

            -- Physical dimension compatibility checks per vehicle category
            CASE p_vehicle_category
                WHEN 'TWO_WHEELER', 'EV_TWO_WHEELER' THEN
                    RETURN p_bay_type IN ('TWO_WHEELER', 'BIKE_BAY') 
                       AND p_bay_length_m >= 2.0 AND p_bay_width_m >= 0.8;
                       
                WHEN 'HATCHBACK' THEN
                    RETURN p_bay_type IN ('COMPACT_CAR', 'STANDARD_CAR', 'LARGE_CAR', 'SUV_BAY')
                       AND p_bay_length_m >= 3.8 AND p_bay_width_m >= 1.7;
                       
                WHEN 'SEDAN' THEN
                    RETURN p_bay_type IN ('STANDARD_CAR', 'LARGE_CAR', 'SUV_BAY')
                       AND p_bay_length_m >= 4.5 AND p_bay_width_m >= 1.8;
                       
                WHEN 'SUV', 'EV_FOUR_WHEELER' THEN
                    RETURN p_bay_type IN ('LARGE_CAR', 'SUV_BAY')
                       AND p_bay_length_m >= 4.8 AND p_bay_width_m >= 1.9 AND p_bay_height_m >= 2.0;
                       
                ELSE
                    RETURN FALSE;
            END CASE;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
        """
    )


def downgrade() -> None:
    # 1. Drop stored function fn_check_vehicle_bay_compatibility
    op.execute(
        """
        DROP FUNCTION IF EXISTS fn_check_vehicle_bay_compatibility(
            vehicle_category_enum,
            VARCHAR(32),
            NUMERIC,
            NUMERIC,
            NUMERIC,
            BOOLEAN,
            BOOLEAN
        );
        """
    )

    # 2. Drop blackout_schedules table
    op.drop_index("idx_blackout_schedules_property_time", table_name="blackout_schedules")
    op.drop_table("blackout_schedules")

    # 3. Drop property_documents table
    op.drop_index("idx_property_documents_property_type", table_name="property_documents")
    op.drop_table("property_documents")

    # 4. Drop added columns on property_authorizations
    op.drop_column("property_authorizations", "updated_at")
    op.drop_column("property_authorizations", "rejection_reason_code")
    op.drop_column("property_authorizations", "version")
