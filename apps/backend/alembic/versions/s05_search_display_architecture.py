"""Search & Display Architecture fixes — nullable price, vendor tier fields.

Revision ID: s05_search_display
Revises: s04_outreach_tables
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa

revision = "s05_search_display"
down_revision = "s04_outreach_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Bid table: make price and total_cost nullable ---
    op.alter_column("bid", "price", existing_type=sa.Float(), nullable=True)
    op.alter_column("bid", "total_cost", existing_type=sa.Float(), nullable=True)

    # Convert vendor_directory bids with price=0 to NULL (quote-based, not free)
    op.execute(
        "UPDATE bid SET price = NULL, total_cost = NULL "
        "WHERE source = 'vendor_directory' AND (price = 0 OR price IS NULL)"
    )

    # --- Vendor table: add tier affinity and price range (idempotent) ---
    op.execute("ALTER TABLE vendor ADD COLUMN IF NOT EXISTS tier_affinity VARCHAR(20)")
    op.execute("ALTER TABLE vendor ADD COLUMN IF NOT EXISTS price_range_min FLOAT")
    op.execute("ALTER TABLE vendor ADD COLUMN IF NOT EXISTS price_range_max FLOAT")


def downgrade() -> None:
    # Revert vendor columns
    op.drop_column("vendor", "price_range_max")
    op.drop_column("vendor", "price_range_min")
    op.drop_column("vendor", "tier_affinity")

    # Revert NULL prices back to 0
    op.execute("UPDATE bid SET price = 0 WHERE price IS NULL")
    op.execute("UPDATE bid SET total_cost = 0 WHERE total_cost IS NULL")

    # Make columns non-nullable again
    op.alter_column("bid", "price", existing_type=sa.Float(), nullable=False)
    op.alter_column("bid", "total_cost", existing_type=sa.Float(), nullable=False)
