"""Add articles table

Revision ID: a4b9c2d3e4f5
Revises: fe56fa70289e
Create Date: 2026-05-01 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a4b9c2d3e4f5"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "articles",
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=128), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(op.f("ix_articles_category"), "articles", ["category"], unique=False)
    op.create_index(
        "ix_articles_published_at_desc",
        "articles",
        [sa.text("published_at DESC")],
        unique=False,
    )
    op.create_index(op.f("ix_articles_source"), "articles", ["source"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_articles_source"), table_name="articles")
    op.drop_index("ix_articles_published_at_desc", table_name="articles")
    op.drop_index(op.f("ix_articles_category"), table_name="articles")
    op.drop_table("articles")
