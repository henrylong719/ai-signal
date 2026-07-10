"""Add last_digest_sent_at to digest_subscribers

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-10 00:00:00.000000

Idempotency watermark for the subscriber digest send loop (see
``services.subscriber_digest``). Mirrors ``users.last_digest_sent_at``:
a subscriber whose watermark falls on the current UTC calendar day is
skipped so a re-fired scheduled tick — or the immediate welcome send on
the same day — can't deliver twice. Nullable, no backfill (NULL = never
sent, which is the correct state for every existing row).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "digest_subscribers",
        sa.Column("last_digest_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("digest_subscribers", "last_digest_sent_at")
