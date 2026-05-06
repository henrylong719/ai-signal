"""Add user has_password flag

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-05-06 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c6"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column(
            "has_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.execute(
        """
        UPDATE "user"
        SET has_password = false
        WHERE EXISTS (
            SELECT 1
            FROM oauth_accounts
            WHERE oauth_accounts.user_id = "user".id
              AND oauth_accounts.created_at <= "user".created_at + interval '5 minutes'
        )
        """
    )
    op.alter_column("user", "has_password", server_default=None)


def downgrade():
    op.drop_column("user", "has_password")
