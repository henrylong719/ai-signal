"""Change article author to text

Revision ID: 2d6f8a9c4b12
Revises: c5d6e7f8a9b0
Create Date: 2026-05-04 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2d6f8a9c4b12"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "articles",
        "author",
        existing_type=sa.String(length=128),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "articles",
        "author",
        existing_type=sa.Text(),
        type_=sa.String(length=128),
        existing_nullable=True,
        postgresql_using="left(author, 128)",
    )
