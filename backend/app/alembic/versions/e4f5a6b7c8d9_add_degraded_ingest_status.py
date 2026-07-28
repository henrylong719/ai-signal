"""Add degraded ingest run status

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-28 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE ingest_run_status "
        "ADD VALUE IF NOT EXISTS 'degraded' AFTER 'succeeded'"
    )


def downgrade() -> None:
    # PostgreSQL cannot remove an enum value in place. Convert any degraded
    # rows to failed, rebuild the type, and cast the column through text.
    op.execute("UPDATE ingest_runs SET status = 'failed' WHERE status = 'degraded'")
    op.execute("ALTER TYPE ingest_run_status RENAME TO ingest_run_status_old")
    op.execute(
        "CREATE TYPE ingest_run_status AS ENUM ('running', 'succeeded', 'failed')"
    )
    op.execute(
        "ALTER TABLE ingest_runs ALTER COLUMN status "
        "TYPE ingest_run_status USING status::text::ingest_run_status"
    )
    op.execute("DROP TYPE ingest_run_status_old")
