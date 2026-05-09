"""Add (user_id, saved_at desc) index on saved_articles

Revision ID: 4c5d6e7f8a9b
Revises: 3b4c5d6e7f8a
Create Date: 2026-05-09 00:00:00.000000

The /articles/saved/ endpoint reads a page of one user's saves ordered
by ``saved_at desc``. The composite primary key on (user_id, article_id)
serves the equality filter on user_id but forces a sort to satisfy the
ORDER BY. With a compound (user_id, saved_at desc) index Postgres can
serve the filter + sort + limit straight off the index, which keeps
page latency flat as a user's saved-article count grows.

The index is also useful for the new ``get_saved_articles_with_articles``
JOIN (one query instead of two), which reads the same shape.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4c5d6e7f8a9b"
down_revision = "3b4c5d6e7f8a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_saved_articles_user_saved_at",
        "saved_articles",
        ["user_id", "saved_at"],
        postgresql_using="btree",
        postgresql_ops={"saved_at": "DESC"},
    )


def downgrade():
    op.drop_index("ix_saved_articles_user_saved_at", table_name="saved_articles")
