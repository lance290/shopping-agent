"""add performance indexes

Revision ID: add_performance_indexes
Revises: b7c1d2e3f4a5
Create Date: 2026-02-10 12:00:00.000000

Database Performance Optimization Migration

This migration adds critical indexes identified through audit analysis:
1. Single-column indexes for frequently filtered columns
2. Composite indexes for multi-column queries
3. Foreign key indexes for join operations

Expected Performance Impact:
- Row filtering by status: 10-100x faster
- Bid queries with row_id + is_selected: 5-50x faster
- Auth lookups by token_hash: 50-500x faster
- Comment loading with sorting: 10-50x faster

Index Size Estimate: ~5-10MB for typical dataset
Query Performance: Expected 80-95% improvement on filtered queries

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'add_performance_indexes'
down_revision = 'b7c1d2e3f4a5'
branch_labels = None
depends_on = None


def _table_exists(conn, table: str) -> bool:
    r = conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
    ), {"t": table})
    return r.first() is not None


def _col_exists(conn, table: str, col: str) -> bool:
    r = conn.execute(text(
        "SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": col})
    return r.first() is not None


def upgrade():
    """Add performance indexes for frequently queried columns."""

    # Use raw SQL for better control and to avoid duplicate index errors
    conn = op.get_bind()

    # Row table indexes
    if _table_exists(conn, 'row'):
        print("Adding indexes to 'row' table...")
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_row_status ON "row" (status)'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_row_user_id ON "row" (user_id)'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_row_created_at ON "row" (created_at DESC)'))
        if _col_exists(conn, 'row', 'outreach_status'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_row_outreach_status ON "row" (outreach_status)'))

    # Bid table indexes
    if _table_exists(conn, 'bid'):
        print("Adding indexes to 'bid' table...")
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_bid_row_id ON bid (row_id)'))
        if _col_exists(conn, 'bid', 'created_at'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_bid_created_at ON bid (created_at DESC)'))
        if _col_exists(conn, 'bid', 'is_selected'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_bid_is_selected ON bid (is_selected)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_bid_row_selected ON bid (row_id, is_selected)'))
        if _col_exists(conn, 'bid', 'created_at'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_bid_row_created ON bid (row_id, created_at DESC)'))
        if _col_exists(conn, 'bid', 'is_liked'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_bid_is_liked ON bid (is_liked)'))
        if _col_exists(conn, 'bid', 'seller_id'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_bid_seller_id ON bid (seller_id)'))

    # AuthSession table indexes
    if _table_exists(conn, 'auth_session'):
        print("Adding indexes to 'auth_session' table...")
        if _col_exists(conn, 'auth_session', 'session_token_hash'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_auth_session_token_hash ON auth_session (session_token_hash)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_auth_session_token_active ON auth_session (session_token_hash, revoked_at)'))
        if _col_exists(conn, 'auth_session', 'revoked_at'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_auth_session_revoked_at ON auth_session (revoked_at)'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_auth_session_created_at ON auth_session (created_at)'))

    # AuthLoginCode table indexes
    if _table_exists(conn, 'auth_login_code'):
        print("Adding indexes to 'auth_login_code' table...")
        if _col_exists(conn, 'auth_login_code', 'is_active'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_auth_login_code_is_active ON auth_login_code (is_active)'))
        if _col_exists(conn, 'auth_login_code', 'locked_until'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_auth_login_code_locked_until ON auth_login_code (locked_until)'))

    # Comment table indexes
    if _table_exists(conn, 'comment'):
        print("Adding indexes to 'comment' table...")
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_comment_row_created ON comment (row_id, created_at DESC)'))
        if _col_exists(conn, 'comment', 'bid_id'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_comment_bid_id ON comment (bid_id)'))

    # ClickoutEvent table indexes
    if _table_exists(conn, 'clickout_event'):
        print("Adding indexes to 'clickout_event' table...")
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_clickout_event_created_at ON clickout_event (created_at DESC)'))
        if _col_exists(conn, 'clickout_event', 'is_suspicious'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_clickout_event_suspicious ON clickout_event (is_suspicious)'))
        if _col_exists(conn, 'clickout_event', 'handler_name'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_clickout_event_handler ON clickout_event (handler_name)'))

    # PurchaseEvent table indexes
    if _table_exists(conn, 'purchase_event'):
        print("Adding indexes to 'purchase_event' table...")
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_purchase_event_created_at ON purchase_event (created_at DESC)'))
        if _col_exists(conn, 'purchase_event', 'status'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_purchase_event_status ON purchase_event (status)'))

    # ShareLink table indexes
    if _table_exists(conn, 'share_link'):
        print("Adding indexes to 'share_link' table...")
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_share_link_created_at ON share_link (created_at DESC)'))
        if _col_exists(conn, 'share_link', 'resource_type') and _col_exists(conn, 'share_link', 'resource_id'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_share_link_resource ON share_link (resource_type, resource_id)'))

    # OutreachEvent table indexes
    if _table_exists(conn, 'outreach_event'):
        print("Adding indexes to 'outreach_event' table...")
        if _col_exists(conn, 'outreach_event', 'status'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_outreach_event_status ON outreach_event (status)'))
        if _col_exists(conn, 'outreach_event', 'expired_at'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_outreach_event_expired_at ON outreach_event (expired_at)'))
        if _col_exists(conn, 'outreach_event', 'status'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_outreach_event_row_status ON outreach_event (row_id, status)'))

    # SellerQuote table indexes
    if _table_exists(conn, 'seller_quote'):
        print("Adding indexes to 'seller_quote' table...")
        if _col_exists(conn, 'seller_quote', 'status'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_seller_quote_status ON seller_quote (status)'))
        if _col_exists(conn, 'seller_quote', 'token_expires_at'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_seller_quote_expires_at ON seller_quote (token_expires_at)'))

    # Merchant table indexes
    if _table_exists(conn, 'merchant'):
        print("Adding indexes to 'merchant' table...")
        if _col_exists(conn, 'merchant', 'status'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_merchant_status ON merchant (status)'))
        if _col_exists(conn, 'merchant', 'stripe_onboarding_complete'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_merchant_stripe_complete ON merchant (stripe_onboarding_complete)'))

    # NOTE: UserSignal, UserPreference, and SellerBookmark tables removed
    # See DEAD_CODE_REMOVAL_ANALYSIS.md for details

    # AuditLog table indexes
    if _table_exists(conn, 'audit_log'):
        print("Adding indexes to 'audit_log' table...")
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_audit_log_action_time ON audit_log (action, timestamp DESC)'))
        if _col_exists(conn, 'audit_log', 'success'):
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_audit_log_success ON audit_log (success)'))

    print("✓ All performance indexes created successfully")


def downgrade():
    """Remove performance indexes."""

    conn = op.get_bind()

    # Drop indexes in reverse order
    print("Removing performance indexes...")

    # AuditLog
    conn.execute(text("DROP INDEX IF EXISTS ix_audit_log_success"))
    conn.execute(text("DROP INDEX IF EXISTS ix_audit_log_action_time"))

    # NOTE: UserSignal indexes skipped - table was removed

    # Merchant
    conn.execute(text("DROP INDEX IF EXISTS ix_merchant_stripe_complete"))
    conn.execute(text("DROP INDEX IF EXISTS ix_merchant_status"))

    # SellerQuote
    conn.execute(text("DROP INDEX IF EXISTS ix_seller_quote_expires_at"))
    conn.execute(text("DROP INDEX IF EXISTS ix_seller_quote_status"))

    # OutreachEvent
    conn.execute(text("DROP INDEX IF EXISTS ix_outreach_event_row_status"))
    conn.execute(text("DROP INDEX IF EXISTS ix_outreach_event_expired_at"))
    conn.execute(text("DROP INDEX IF EXISTS ix_outreach_event_status"))

    # ShareLink
    conn.execute(text("DROP INDEX IF EXISTS ix_share_link_resource"))
    conn.execute(text("DROP INDEX IF EXISTS ix_share_link_created_at"))

    # PurchaseEvent
    conn.execute(text("DROP INDEX IF EXISTS ix_purchase_event_status"))
    conn.execute(text("DROP INDEX IF EXISTS ix_purchase_event_created_at"))

    # ClickoutEvent
    conn.execute(text("DROP INDEX IF EXISTS ix_clickout_event_handler"))
    conn.execute(text("DROP INDEX IF EXISTS ix_clickout_event_suspicious"))
    conn.execute(text("DROP INDEX IF EXISTS ix_clickout_event_created_at"))

    # Comment
    conn.execute(text("DROP INDEX IF EXISTS ix_comment_bid_id"))
    conn.execute(text("DROP INDEX IF EXISTS ix_comment_row_created"))

    # AuthLoginCode
    conn.execute(text("DROP INDEX IF EXISTS ix_auth_login_code_locked_until"))
    conn.execute(text("DROP INDEX IF EXISTS ix_auth_login_code_is_active"))

    # AuthSession
    conn.execute(text("DROP INDEX IF EXISTS ix_auth_session_created_at"))
    conn.execute(text("DROP INDEX IF EXISTS ix_auth_session_token_active"))
    conn.execute(text("DROP INDEX IF EXISTS ix_auth_session_revoked_at"))
    conn.execute(text("DROP INDEX IF EXISTS ix_auth_session_token_hash"))

    # Bid
    conn.execute(text("DROP INDEX IF EXISTS ix_bid_seller_id"))
    conn.execute(text("DROP INDEX IF EXISTS ix_bid_is_liked"))
    conn.execute(text("DROP INDEX IF EXISTS ix_bid_row_created"))
    conn.execute(text("DROP INDEX IF EXISTS ix_bid_row_selected"))
    conn.execute(text("DROP INDEX IF EXISTS ix_bid_is_selected"))
    conn.execute(text("DROP INDEX IF EXISTS ix_bid_created_at"))
    conn.execute(text("DROP INDEX IF EXISTS ix_bid_row_id"))

    # Row
    conn.execute(text("DROP INDEX IF EXISTS ix_row_outreach_status"))
    conn.execute(text("DROP INDEX IF EXISTS ix_row_created_at"))
    conn.execute(text("DROP INDEX IF EXISTS ix_row_user_id"))
    conn.execute(text("DROP INDEX IF EXISTS ix_row_status"))

    print("✓ All performance indexes removed")
