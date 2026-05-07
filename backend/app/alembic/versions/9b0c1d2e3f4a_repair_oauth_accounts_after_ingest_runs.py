"""Repair OAuth accounts after ingest run migration

Revision ID: 9b0c1d2e3f4a
Revises: 86bc09927088
Create Date: 2026-05-06 22:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9b0c1d2e3f4a"
down_revision = "86bc09927088"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    oauth_accounts_exists = inspector.has_table("oauth_accounts")
    if not oauth_accounts_exists:
        op.create_table(
            "oauth_accounts",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("provider_user_id", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("email_verified", sa.Boolean(), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=True),
            sa.Column("avatar_url", sa.String(length=2048), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id", name="pk_oauth_accounts"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "provider",
                "provider_user_id",
                name="uq_oauth_accounts_provider_provider_user_id",
            ),
        )
        op.create_index(
            "ix_oauth_accounts_user_id",
            "oauth_accounts",
            ["user_id"],
        )
    else:
        oauth_indexes = {
            index["name"] for index in inspector.get_indexes("oauth_accounts")
        }
        if "ix_oauth_accounts_user_id" not in oauth_indexes:
            op.create_index(
                "ix_oauth_accounts_user_id",
                "oauth_accounts",
                ["user_id"],
            )

    if inspector.has_table("article_events"):
        article_event_indexes = {
            index["name"] for index in inspector.get_indexes("article_events")
        }
        if "ix_article_events_user_event" not in article_event_indexes:
            op.create_index(
                "ix_article_events_user_event",
                "article_events",
                ["user_id", "event_type", "article_id"],
            )


def downgrade():
    pass
