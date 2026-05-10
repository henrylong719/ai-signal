"""Add digest + onboarding fields to user

Revision ID: 6e7f8a9b0c1d
Revises: 5d6e7f8a9b0c
Create Date: 2026-05-09 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6e7f8a9b0c1d"
down_revision = "5d6e7f8a9b0c"
branch_labels = None
depends_on = None


def upgrade():
    # IANA timezone string (e.g. "America/New_York"). Stored as text so we
    # can pass it straight to zoneinfo without a lookup table. NULL means
    # "not yet known" — the digest sender treats unset as UTC.
    op.add_column(
        "user",
        sa.Column("timezone", sa.String(length=64), nullable=True),
    )
    # Daily digest opt-in. Defaults to False so existing users are not
    # auto-subscribed to a recurring email they did not request — new
    # users opt in during the onboarding flow.
    op.add_column(
        "user",
        sa.Column(
            "daily_digest_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("user", "daily_digest_enabled", server_default=None)
    # Idempotency key for the hourly send job: prevents the same user
    # from receiving two digest emails on the same calendar day if the
    # job re-fires (process restart, scheduler glitch).
    op.add_column(
        "user",
        sa.Column(
            "last_digest_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Marks first-run onboarding complete. NULL means the modal still
    # shows on next sign-in. We do not back-fill existing users so the
    # flow runs once for accounts that pre-date the onboarding feature.
    op.add_column(
        "user",
        sa.Column(
            "onboarded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("user", "onboarded_at")
    op.drop_column("user", "last_digest_sent_at")
    op.drop_column("user", "daily_digest_enabled")
    op.drop_column("user", "timezone")
