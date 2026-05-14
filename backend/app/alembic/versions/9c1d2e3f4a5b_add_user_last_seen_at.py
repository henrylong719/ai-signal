"""Add last_seen_at to user

Revision ID: 9c1d2e3f4a5b
Revises: 8b1c2d3e4f5a
Create Date: 2026-05-14 10:00:00.000000

Adds a nullable timestamp updated by the auth dependency on each
authenticated request (throttled to ~5 minutes). Admins read this to
distinguish active accounts from dormant ones. NULL means the account
has not been seen since the column was introduced — we deliberately
do not back-fill so the admin UI can show "never" for accounts that
predate this feature.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9c1d2e3f4a5b"
down_revision = "8b1c2d3e4f5a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("user", "last_seen_at")
