"""Reset article and user embeddings for the OpenAI provider swap

Revision ID: c2d3e4f5a6b7
Revises: 9c1d2e3f4a5b
Create Date: 2026-05-22 10:30:00.000000

The embedding service moved from sentence-transformers/all-MiniLM-L6-v2 to
OpenAI's text-embedding-3-small (truncated to 384 dims via Matryoshka so
the pgvector column dim is unchanged). Vectors produced by the two
models live in different latent spaces, so the old values are useless
for cosine comparison and would actively poison the For-You ranker.

This migration nulls existing article embeddings and clears the user
embedding cache. The next ingest tick repopulates new articles inline;
``app.script.backfill_embeddings`` (or the admin /backfill endpoint)
re-embeds the historical corpus. User vectors rebuild lazily on the
next save/click/interest change, or on the first For-You request.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c2d3e4f5a6b7"
down_revision = "9c1d2e3f4a5b"
branch_labels = None
depends_on = None


def upgrade():
    # Plain UPDATE / DELETE; no pgvector cast needed when we're writing
    # NULL or removing rows.
    op.execute("UPDATE articles SET embedding = NULL WHERE embedding IS NOT NULL")
    op.execute("DELETE FROM user_embeddings")


def downgrade():
    # The old MiniLM vectors are unrecoverable — nothing to restore on
    # downgrade. The columns/tables themselves are untouched, so this
    # is intentionally a no-op rather than a failure.
    pass
