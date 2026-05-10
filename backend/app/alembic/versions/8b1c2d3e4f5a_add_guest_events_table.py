"""Add guest_events table

Revision ID: 8b1c2d3e4f5a
Revises: 7a8b9c0d1e2f
Create Date: 2026-05-10 15:30:00.000000

Append-only log of anonymous funnel events from logged-out visitors
(page views, article clicks, source clicks, signup CTA clicks, signup
completions). Distinct from ``article_events``, which is aggregated and
used for personalization — this one is for product analytics in admin.

Two indexes:

  - ``(event_type, created_at)``: the admin funnel endpoint scans by
    event type filtered to a window.
  - ``(anonymous_id, created_at)``: used to attribute a guest_signup_completed
    to prior events from the same browser.

``user_id`` is nullable and only set on conversion events; ``article_id``
and the FK ``ON DELETE SET NULL`` so cleaning up the source data does
not break historical analytics rows.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8b1c2d3e4f5a"
down_revision = "7a8b9c0d1e2f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "guest_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anonymous_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_name", sa.String(length=64), nullable=True),
        sa.Column("topic", sa.String(length=64), nullable=True),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_guest_events_event_type_created_at",
        "guest_events",
        ["event_type", "created_at"],
    )
    op.create_index(
        "ix_guest_events_anonymous_id_created_at",
        "guest_events",
        ["anonymous_id", "created_at"],
    )


def downgrade():
    op.drop_index(
        "ix_guest_events_anonymous_id_created_at", table_name="guest_events"
    )
    op.drop_index("ix_guest_events_event_type_created_at", table_name="guest_events")
    op.drop_table("guest_events")
