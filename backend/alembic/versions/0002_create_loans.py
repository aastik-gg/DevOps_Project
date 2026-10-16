"""create loans table

Revision ID: 0002_create_loans
Revises: 0001_create_items
Create Date: 2026-10-16
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_create_loans"
down_revision = "0001_create_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("borrower", sa.String(120), nullable=False),
        sa.Column("purpose", sa.String(200), nullable=False, server_default=""),
        sa.Column("borrowed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_loans_item_id", "loans", ["item_id"])
    # At most one open loan per item, enforced by the database even under concurrent checkouts.
    op.create_index(
        "uq_loans_one_open_per_item",
        "loans",
        ["item_id"],
        unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
        sqlite_where=sa.text("returned_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_loans_one_open_per_item", table_name="loans")
    op.drop_index("ix_loans_item_id", table_name="loans")
    op.drop_table("loans")
