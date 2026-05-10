"""Add archived_at to articles for the cleanup pipeline

Revision ID: 7a8b9c0d1e2f
Revises: 6e7f8a9b0c1d
Create Date: 2026-05-10 00:00:00.000000

Soft-archive column for the safe article cleanup flow (see
``services.article_cleanup``). The cleanup runs in two stages:

  1. Set ``archived_at`` on old, unsaved, unengaged articles so they
     stop appearing in public feeds while the row is still recoverable.
  2. Delete archived articles that have stayed quiet for an additional
     window — saved or recently clicked articles never reach this step.

A plain b-tree index on ``archived_at`` covers both the cleanup scan
(``WHERE archived_at < cutoff``) and the public-feed filter
(``WHERE archived_at IS NULL``); the same shape serves both reads.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7a8b9c0d1e2f"
down_revision = "6e7f8a9b0c1d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "articles",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_articles_archived_at",
        "articles",
        ["archived_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_articles_archived_at", table_name="articles")
    op.drop_column("articles", "archived_at")
