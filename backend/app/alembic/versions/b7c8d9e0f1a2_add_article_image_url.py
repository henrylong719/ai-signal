"""Add article image_url

Revision ID: b7c8d9e0f1a2
Revises: a4b9c2d3e4f5
Create Date: 2026-05-02 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b7c8d9e0f1a2"
down_revision = "a4b9c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("articles", sa.Column("image_url", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("articles", "image_url")
