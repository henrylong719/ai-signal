"""Add user_interests table

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-05-05 00:00:01.000000

Stores explicit onboarding interests: categories (from the fixed enum) and
free-form tags. One row per user is the right shape because (1) the row is
always read whole by the recommender, (2) writes are full-replace from the
settings UI, and (3) interests are bounded to ~10 items. If we later need
weighted interests or interest-history we'd normalize into a (user, tag)
join table.

Categories are stored as TEXT[] (not PG ENUM[]) because it sidesteps the
ENUM-membership constraint and lets the application validate against the
Category Literal. This is slightly looser at the DB level but matches how
the existing `articles.tags` column is stored.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_interests",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "categories",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    )


def downgrade():
    op.drop_table("user_interests")
