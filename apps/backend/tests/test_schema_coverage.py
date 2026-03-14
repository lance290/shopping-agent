"""Regression test: ensure fix_schema.py covers every column in every model.

Root cause of prod 502 on 2026-03-03: clickout_event.bid_id existed in the
SQLModel class but was missing from fix_schema.py EXPECTED_COLS, so it was
never created on the Railway DB. This caused PendingRollbackError cascades
that took down the entire backend.

This test introspects SQLModel metadata and verifies that every column in
every table model is either:
  (a) covered by EXPECTED_COLS or JSON_COLS in fix_schema.py, OR
  (b) in the CREATE TABLE statements for tables fix_schema creates from scratch, OR
  (c) a core column that SQLModel.metadata.create_all() always creates (id, etc.)

If a developer adds a new column to a model but forgets to add it to
fix_schema.py, this test will fail and tell them exactly which column is
missing.
"""
import importlib
import sys
import os
import re

import pytest

# Ensure the backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_fix_schema():
    """Import fix_schema and extract EXPECTED_COLS + the JSON_COLS list."""
    import scripts.fix_schema as fs

    expected = set()
    for table, col, _pgtype, _default in fs.EXPECTED_COLS:
        expected.add((table, col))

    return expected, fs


def _get_all_model_columns():
    """Introspect SQLModel metadata to get every (table, column) pair."""
    # Force-import all models so metadata is populated
    import models  # noqa: F401
    from sqlmodel import SQLModel

    result = {}
    for table_name, table_obj in SQLModel.metadata.tables.items():
        cols = set()
        for col in table_obj.columns:
            cols.add(col.name)
        result[table_name] = cols
    return result


# Tables that fix_schema.py creates from scratch (full CREATE TABLE).
# Columns in these tables don't need to be in EXPECTED_COLS because
# the CREATE TABLE statement already includes them.
TABLES_CREATED_FROM_SCRATCH = {"vendor", "request_spec", "brand_portal_token", "campaign", "coupon_campaign", "group_thread", "receipt", "row_comment", "row_reaction", "vendor_bookmark", "item_bookmark"}

# Core columns that every table gets from SQLModel/create_all — these
# are always present on the DB and don't need fix_schema entries.
CORE_COLUMNS = {"id"}

# Columns that are part of the original table schema (created by initial
# create_all or early migrations) and don't need fix_schema entries.
# Format: (table_name, column_name)
ORIGINAL_COLUMNS = {
    # Row — original schema
    ("row", "title"), ("row", "status"), ("row", "budget_max"), ("row", "currency"),
    ("row", "created_at"), ("row", "updated_at"), ("row", "user_id"), ("row", "project_id"),
    ("row", "choice_factors"), ("row", "choice_answers"), ("row", "provider_query"),
    ("row", "search_intent"), ("row", "provider_query_map"), ("row", "outreach_status"),
    ("row", "outreach_count"), ("row", "chat_history"),
    # Project — original
    ("project", "title"), ("project", "user_id"), ("project", "created_at"), ("project", "updated_at"),
    # Bid — original
    ("bid", "row_id"), ("bid", "vendor_id"), ("bid", "price"), ("bid", "shipping_cost"),
    ("bid", "total_cost"), ("bid", "currency"), ("bid", "item_title"), ("bid", "item_url"),
    ("bid", "image_url"), ("bid", "eta_days"), ("bid", "return_policy"), ("bid", "condition"),
    ("bid", "source"), ("bid", "is_selected"), ("bid", "is_service_provider"), ("bid", "created_at"),
    ("bid", "is_liked"),
    # User — original
    ("user", "email"), ("user", "phone_number"), ("user", "name"), ("user", "company"),
    ("user", "created_at"), ("user", "is_admin"),
    # AuthLoginCode — original
    ("auth_login_code", "email"), ("auth_login_code", "phone_number"),
    ("auth_login_code", "code_hash"), ("auth_login_code", "is_active"),
    ("auth_login_code", "attempt_count"), ("auth_login_code", "locked_until"),
    ("auth_login_code", "created_at"),
    # AuthSession — original
    ("auth_session", "email"), ("auth_session", "phone_number"),
    ("auth_session", "user_id"), ("auth_session", "session_token_hash"),
    ("auth_session", "created_at"), ("auth_session", "revoked_at"),
    # AuditLog — original
    ("audit_log", "user_id"), ("audit_log", "action"), ("audit_log", "details"),
    ("audit_log", "ip_address"), ("audit_log", "created_at"),
    # Comment — original
    ("comment", "user_id"), ("comment", "row_id"), ("comment", "bid_id"),
    ("comment", "offer_url"), ("comment", "body"), ("comment", "visibility"),
    ("comment", "created_at"),
    # ShareLink — original
    ("share_link", "token"), ("share_link", "resource_type"), ("share_link", "resource_id"),
    ("share_link", "created_by"), ("share_link", "created_at"),
    # ClickoutEvent — original
    ("clickout_event", "user_id"), ("clickout_event", "session_id"),
    ("clickout_event", "row_id"), ("clickout_event", "offer_index"),
    ("clickout_event", "canonical_url"), ("clickout_event", "final_url"),
    ("clickout_event", "merchant_domain"), ("clickout_event", "handler_name"),
    ("clickout_event", "affiliate_tag"), ("clickout_event", "source"),
    ("clickout_event", "share_token"), ("clickout_event", "referral_user_id"),
    ("clickout_event", "created_at"),
    # PurchaseEvent — original
    ("purchase_event", "user_id"), ("purchase_event", "bid_id"),
    ("purchase_event", "row_id"), ("purchase_event", "amount"),
    ("purchase_event", "currency"), ("purchase_event", "merchant_domain"),
    ("purchase_event", "payment_method"), ("purchase_event", "stripe_session_id"),
    ("purchase_event", "stripe_payment_intent_id"), ("purchase_event", "clickout_event_id"),
    ("purchase_event", "share_token"), ("purchase_event", "status"),
    ("purchase_event", "platform_fee_amount"), ("purchase_event", "commission_rate"),
    ("purchase_event", "revenue_type"), ("purchase_event", "created_at"),
    # BugReport — original
    ("bug_report", "user_id"), ("bug_report", "notes"), ("bug_report", "expected"),
    ("bug_report", "actual"), ("bug_report", "severity"), ("bug_report", "category"),
    ("bug_report", "status"), ("bug_report", "classification"),
    ("bug_report", "classification_confidence"), ("bug_report", "attachments"),
    ("bug_report", "diagnostics"), ("bug_report", "github_issue_url"),
    ("bug_report", "github_pr_url"), ("bug_report", "preview_url"),
    ("bug_report", "created_at"),
    # Notification — original
    ("notification", "user_id"), ("notification", "type"), ("notification", "title"),
    ("notification", "body"), ("notification", "action_url"), ("notification", "resource_type"),
    ("notification", "resource_id"), ("notification", "read"), ("notification", "read_at"),
    ("notification", "created_at"),
    # UserSignal — original
    ("user_signal", "user_id"), ("user_signal", "bid_id"), ("user_signal", "row_id"),
    ("user_signal", "signal_type"), ("user_signal", "value"), ("user_signal", "created_at"),
    # UserPreference — original
    ("user_preference", "user_id"), ("user_preference", "preference_key"),
    ("user_preference", "preference_value"), ("user_preference", "weight"),
    ("user_preference", "updated_at"),
    # SellerQuote — original
    ("seller_quote", "row_id"), ("seller_quote", "token"), ("seller_quote", "token_expires_at"),
    ("seller_quote", "seller_email"), ("seller_quote", "seller_name"),
    ("seller_quote", "seller_company"), ("seller_quote", "seller_phone"),
    ("seller_quote", "price"), ("seller_quote", "currency"), ("seller_quote", "description"),
    ("seller_quote", "answers"), ("seller_quote", "attachments"), ("seller_quote", "status"),
    ("seller_quote", "bid_id"), ("seller_quote", "created_at"), ("seller_quote", "submitted_at"),
    # OutreachEvent — original
    ("outreach_event", "row_id"), ("outreach_event", "vendor_email"),
    ("outreach_event", "vendor_name"), ("outreach_event", "vendor_company"),
    ("outreach_event", "vendor_source"), ("outreach_event", "message_id"),
    ("outreach_event", "quote_token"), ("outreach_event", "sent_at"),
    ("outreach_event", "opened_at"), ("outreach_event", "clicked_at"),
    ("outreach_event", "quote_submitted_at"), ("outreach_event", "opt_out"),
    ("outreach_event", "created_at"),
    # DealHandoff — original
    ("deal_handoff", "row_id"), ("deal_handoff", "quote_id"),
    ("deal_handoff", "buyer_user_id"), ("deal_handoff", "buyer_email"),
    ("deal_handoff", "buyer_name"), ("deal_handoff", "buyer_phone"),
    ("deal_handoff", "deal_value"), ("deal_handoff", "currency"),
    ("deal_handoff", "buyer_email_sent_at"), ("deal_handoff", "seller_email_sent_at"),
    ("deal_handoff", "buyer_email_opened_at"), ("deal_handoff", "seller_email_opened_at"),
    ("deal_handoff", "status"), ("deal_handoff", "closed_at"), ("deal_handoff", "created_at"),
    # Contract — original
    ("contract", "bid_id"), ("contract", "row_id"), ("contract", "quote_id"),
    ("contract", "buyer_user_id"), ("contract", "buyer_email"), ("contract", "seller_email"),
    ("contract", "seller_company"), ("contract", "docusign_envelope_id"),
    ("contract", "template_id"), ("contract", "deal_value"), ("contract", "currency"),
    ("contract", "status"), ("contract", "sent_at"), ("contract", "viewed_at"),
    ("contract", "signed_at"), ("contract", "completed_at"), ("contract", "created_at"),
    # OutreachCampaign — all original
    ("outreach_campaign", "row_id"), ("outreach_campaign", "vendor_id"),
    ("outreach_campaign", "campaign_type"), ("outreach_campaign", "status"),
    ("outreach_campaign", "category"), ("outreach_campaign", "item_description"),
    ("outreach_campaign", "specs"), ("outreach_campaign", "email_subject"),
    ("outreach_campaign", "email_body"), ("outreach_campaign", "created_at"),
    ("outreach_campaign", "updated_at"), ("outreach_campaign", "sent_at"),
    # OutreachMessage — all original
    ("outreach_message", "campaign_id"), ("outreach_message", "vendor_id"),
    ("outreach_message", "bid_id"), ("outreach_message", "direction"),
    ("outreach_message", "channel"), ("outreach_message", "status"),
    ("outreach_message", "subject"), ("outreach_message", "body"),
    ("outreach_message", "from_email"), ("outreach_message", "to_email"),
    ("outreach_message", "resend_message_id"), ("outreach_message", "ai_classification"),
    ("outreach_message", "ai_confidence"), ("outreach_message", "created_at"),
    # OutreachQuote — all original
    ("outreach_quote", "campaign_id"), ("outreach_quote", "vendor_id"),
    ("outreach_quote", "message_id"), ("outreach_quote", "price"),
    ("outreach_quote", "currency"), ("outreach_quote", "description"),
    ("outreach_quote", "specs"), ("outreach_quote", "valid_until"),
    ("outreach_quote", "status"), ("outreach_quote", "bid_id"),
    ("outreach_quote", "created_at"),
    # Deal — all original
    ("deal", "row_id"), ("deal", "bid_id"), ("deal", "vendor_id"),
    ("deal", "buyer_user_id"), ("deal", "status"), ("deal", "proxy_email_alias"),
    ("deal", "vendor_quoted_price"), ("deal", "platform_fee_pct"),
    ("deal", "platform_fee_amount"), ("deal", "buyer_total"), ("deal", "currency"),
    ("deal", "stripe_payment_intent_id"), ("deal", "stripe_transfer_id"),
    ("deal", "stripe_connect_account_id"), ("deal", "agreed_terms_summary"),
    ("deal", "fulfillment_notes"), ("deal", "created_at"), ("deal", "updated_at"),
    ("deal", "terms_agreed_at"), ("deal", "funded_at"), ("deal", "completed_at"),
    ("deal", "canceled_at"),
    # DealMessage — all original
    ("deal_message", "deal_id"), ("deal_message", "sender_type"),
    ("deal_message", "sender_email"), ("deal_message", "subject"),
    ("deal_message", "content_text"), ("deal_message", "content_html"),
    ("deal_message", "attachments"), ("deal_message", "resend_message_id"),
    ("deal_message", "ai_classification"), ("deal_message", "ai_confidence"),
    ("deal_message", "created_at"),
    # ProjectMember — all original
    ("project_member", "project_id"), ("project_member", "user_id"),
    ("project_member", "role"), ("project_member", "channel"),
    ("project_member", "invited_by"), ("project_member", "joined_at"),
    # ProjectInvite — all original
    ("project_invite", "project_id"), ("project_invite", "invited_by"),
    ("project_invite", "created_at"), ("project_invite", "expires_at"),
    # Like — original
    ("like", "user_id"), ("like", "bid_id"), ("like", "row_id"),
    ("like", "offer_url"), ("like", "created_at"),
}


# Known column name mappings where sa_column uses a different name
SA_COLUMN_RENAMES = {
    ("bid", "bid_ui_schema"): ("bid", "ui_schema"),  # model field: ui_schema, DB col: bid_ui_schema
}


def test_fix_schema_covers_all_model_columns():
    """Every column in every SQLModel table must be accounted for in fix_schema.py.

    If this test fails, you need to add the missing column to
    scripts/fix_schema.py EXPECTED_COLS (for simple types) or
    JSON_COLS (for JSONB columns) in the fix_schema() function.
    """
    expected_cols, fs = _load_fix_schema()

    # Also extract JSON_COLS from the fix_schema function source
    # (they're defined inside the function, not at module level)
    import inspect
    source = inspect.getsource(fs.fix_schema)
    # Parse JSON_COLS entries from function body
    json_col_pattern = re.compile(r'\("(\w+)",\s*"(\w+)",\s*"JSONB"\)')
    json_cols = set()
    for match in json_col_pattern.finditer(source):
        json_cols.add((match.group(1), match.group(2)))

    all_covered = expected_cols | json_cols

    model_columns = _get_all_model_columns()

    missing = []
    for table_name, columns in model_columns.items():
        if table_name in TABLES_CREATED_FROM_SCRATCH:
            continue

        for col_name in columns:
            if col_name in CORE_COLUMNS:
                continue
            if (table_name, col_name) in ORIGINAL_COLUMNS:
                continue
            if (table_name, col_name) in all_covered:
                continue
            # Check SA_COLUMN_RENAMES
            if (table_name, col_name) in SA_COLUMN_RENAMES:
                continue

            missing.append(f"  {table_name}.{col_name}")

    if missing:
        missing_str = "\n".join(sorted(missing))
        pytest.fail(
            f"The following model columns are NOT covered by fix_schema.py.\n"
            f"Add them to EXPECTED_COLS or JSON_COLS to prevent production crashes:\n\n"
            f"{missing_str}\n\n"
            f"See: apps/backend/scripts/fix_schema.py"
        )


def test_fix_schema_no_duplicate_entries():
    """EXPECTED_COLS should not have duplicate (table, column) entries."""
    expected_cols, _ = _load_fix_schema()
    # _load_fix_schema returns a set, so duplicates are already collapsed.
    # Check the raw list instead.
    import scripts.fix_schema as fs
    seen = set()
    dupes = []
    for table, col, _pgtype, _default in fs.EXPECTED_COLS:
        key = (table, col)
        if key in seen:
            dupes.append(f"  {table}.{col}")
        seen.add(key)

    if dupes:
        pytest.fail(
            f"Duplicate entries in fix_schema.py EXPECTED_COLS:\n"
            + "\n".join(dupes)
        )
