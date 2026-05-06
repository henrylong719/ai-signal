"""Add pgvector extension and articles.embedding column

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-05-05 00:00:02.000000

Enables semantic similarity ranking in the recommender. Each article gets
a 384-dimensional embedding from sentence-transformers/all-MiniLM-L6-v2
covering title + excerpt + category + tags + source.

The column is nullable: not every article needs an embedding immediately
(see hybrid ingestion strategy in docs/recommender.md). Articles without
embeddings are simply skipped from the semantic-similarity step in the
For-You scoring; the other signals (interests, recency, source affinity)
still rank them. Backfill fills in the gaps.

We deliberately do NOT add an HNSW or IVFFlat index in this migration.
Two reasons:
  1. With <10K articles, sequential scan is faster than the index build
     overhead. pgvector's docs explicitly recommend deferring the index
     until you have enough rows for it to pay off.
  2. HNSW indexes need to be built AFTER backfill — building an empty
     index then populating embeddings forces expensive re-balancing.
A future migration adds the index once we have enough embedded rows.
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "a5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None

# MiniLM-L6-v2 produces 384-dimensional embeddings. Constant rather
# than literal so that if we ever swap models (e.g., to OpenAI's
# text-embedding-3-small at 1536), the dimension change is one place.
EMBEDDING_DIM = 384


def upgrade():
    # CREATE EXTENSION needs superuser privileges. In dev/CI this works
    # against the standard postgres image; in managed Postgres (RDS, etc.)
    # the extension must be pre-installed by an admin. Document this in
    # the deployment notes.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "articles",
        sa.Column(
            "embedding",
            Vector(EMBEDDING_DIM),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("articles", "embedding")
    # We deliberately do not DROP EXTENSION on downgrade — other migrations
    # or applications in the same database might still need it, and
    # extensions are typically managed at the database level rather than
    # per-application.
