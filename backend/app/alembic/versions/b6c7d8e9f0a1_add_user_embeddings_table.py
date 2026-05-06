"""Add user_embeddings table

Revision ID: b6c7d8e9f0a1
Revises: b8c9d0e1f2a3
Create Date: 2026-05-06 00:00:02.000000

Caches each user's semantic interest vector so the For-You feed can rank
articles without rebuilding the vector on every request. The row is keyed by
user_id and cascades with the owning user.
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b6c7d8e9f0a1"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 384


def upgrade():
    op.create_table(
        "user_embeddings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_embeddings"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    )


def downgrade():
    op.drop_table("user_embeddings")
