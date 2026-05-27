"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from geoalchemy2 import Geometry

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Run the SQL init script (extensions + tables)
    # In practice this is handled by scripts/init.sql at docker init.
    # Alembic tracks subsequent migrations only.
    op.execute("""
        DO $$ BEGIN
          CREATE TYPE entry_type AS ENUM (
            'webpage','thought','book','video','document',
            'media','person','org','place','event',
            'definition','liked','ai_conv'
          );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
          CREATE TYPE connection_type AS ENUM (
            'related','references','contradicts','extends',
            'exemplifies','authored_by','published_by',
            'located_at','occurred_at'
          );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)


def downgrade() -> None:
    pass
