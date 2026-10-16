"""create items table

Revision ID: 0001_create_items
Revises:
Create Date: 2026-10-16
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_create_items"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(60), nullable=False, server_default="General"),
        sa.Column("asset_tag", sa.String(40), nullable=False),
        sa.Column("location", sa.String(120), nullable=False, server_default="Main lab"),
        sa.Column("condition", sa.String(20), nullable=False, server_default="GOOD"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("condition IN ('GOOD', 'FAIR', 'NEEDS_REPAIR')", name="ck_items_condition"),
    )
    op.create_index("ix_items_asset_tag", "items", ["asset_tag"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_items_asset_tag", table_name="items")
    op.drop_table("items")
