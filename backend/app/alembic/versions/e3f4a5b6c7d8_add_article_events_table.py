"""Add article_events table

Revision ID: e3f4a5b6c7d8
Revises: 2d6f8a9c4b12
Create Date: 2026-05-05 00:00:00.000000

Stores user-article behavioral events (currently: clicked, dismissed) with
a (user_id, article_id, event_type) composite primary key and a `count` /
`first_at` / `last_at` triple. This is intentionally a deduped/aggregated
shape rather than an append-only event log: for recommendation purposes the
useful signal is "has this user clicked this article (and how recently)",
not the raw event stream. Storage scales as users x articles x event_types,
which is bounded.

If we ever need raw event-level analytics, we'd add an append-only sibling
table and treat this one as the materialized view of it.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e3f4a5b6c7d8"
down_revision = "2d6f8a9c4b12"
branch_labels = None
depends_on = None


# Postgres ENUM type for event_type. Created with create_type=False on the
# Column so we can manage its lifecycle explicitly in upgrade/downgrade.
ARTICLE_EVENT_TYPE = postgresql.ENUM(
    "clicked",
    "dismissed",
    name="article_event_type",
    create_type=False,
)


def upgrade():
    # Create the ENUM type first so the column can reference it.
    ARTICLE_EVENT_TYPE.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "article_events",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", ARTICLE_EVENT_TYPE, nullable=False),
        sa.Column(
            "count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("first_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "user_id", "article_id", "event_type", name="pk_article_events"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], ondelete="CASCADE"
        ),
    )

    # Supports the recommender's primary read pattern:
    # "fetch all (article_id, count) for a given user filtered by event_type".
    op.create_index(
        "ix_article_events_user_event",
        "article_events",
        ["user_id", "event_type", "article_id"],
    )


def downgrade():
    op.drop_index("ix_article_events_user_event", table_name="article_events")
    op.drop_table("article_events")
    ARTICLE_EVENT_TYPE.drop(op.get_bind(), checkfirst=True)
