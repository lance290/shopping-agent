"""One-shot schema sync + data migration.

1. Add missing columns to the current (pgvector) DB.
2. Ensure request_spec table exists (model uses snake_case).
3. If OLD_DATABASE_URL is set, migrate data from the old managed Postgres.

Idempotent — safe to run on every boot.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "")
# One-time migration source. Intentionally empty by default.
OLD_DATABASE_URL = os.environ.get("OLD_DATABASE_URL", "").strip()
# Run legacy data migration only when explicitly requested.
RUN_LEGACY_MIGRATION = os.environ.get("RUN_LEGACY_MIGRATION", "").lower() in {"1", "true", "yes"}
# Run phone/user merge hack only when explicitly requested.
RUN_USER_PHONE_MERGE = os.environ.get("RUN_USER_PHONE_MERGE", "").lower() in {"1", "true", "yes"}

# (table, column, pg_type, default_expr_or_None)
EXPECTED_COLS = [
    ("bid", "liked_at", "TIMESTAMP", None),
    ("bid", "is_swap", "BOOLEAN", None),
    ("bid", "is_superseded", "BOOLEAN", "false"),
    ("bid", "superseded_at", "TIMESTAMP", None),
    ("bid", "vendor_id", "INTEGER", None),
    ("bid", "canonical_url", "VARCHAR", None),
    ("bid", "source_payload", "TEXT", None),
    ("bid", "search_intent_version", "VARCHAR", None),
    ("bid", "normalized_at", "TIMESTAMP", None),
    ("row", "last_engaged_at", "TIMESTAMP", None),
    ("row", "desire_tier", "VARCHAR(20)", None),
    ("row", "structured_constraints", "TEXT", None),
    ("row", "is_service", "BOOLEAN", "false"),
    ("project", "anonymous_session_id", "VARCHAR", None),
    ("project", "shopping_mode", "VARCHAR", None),
    ("project", "ui_schema_updated_at", "TIMESTAMP", None),
    ("row", "anonymous_session_id", "VARCHAR", None),
    ("row", "brand_name", "VARCHAR", None),
    ("row", "retailer_sku", "VARCHAR", None),
    ("wallet_transaction", "campaign_id", "INTEGER", None),
    ("row", "service_category", "VARCHAR", None),
    ("row", "origin_channel", "VARCHAR", None),
    ("row", "origin_message_id", "VARCHAR", None),
    ("row", "origin_user_id", "INTEGER", None),
    ("auth_session", "expires_at", "TIMESTAMP", None),
    ("auth_session", "last_activity_at", "TIMESTAMP", "NOW()"),
    ("outreach_event", "status", "VARCHAR", "'pending'"),
    ("outreach_event", "timeout_hours", "INTEGER", "48"),
    ("outreach_event", "expired_at", "TIMESTAMP", None),
    ("outreach_event", "followup_sent_at", "TIMESTAMP", None),
    ("deal_handoff", "bid_id", "INTEGER", None),
    ("deal_handoff", "vendor_id", "INTEGER", None),
    ("deal_handoff", "vendor_email", "VARCHAR", None),
    ("deal_handoff", "vendor_name", "VARCHAR", None),
    ("deal_handoff", "acceptance_token", "VARCHAR", None),
    ("deal_handoff", "buyer_accepted_at", "TIMESTAMP", None),
    ("deal_handoff", "buyer_accepted_ip", "VARCHAR", None),
    ("deal_handoff", "vendor_accepted_at", "TIMESTAMP", None),
    ("deal_handoff", "vendor_accepted_ip", "VARCHAR", None),
    # merchant table was merged into vendor by s02 migration — skip if absent
    ("project", "status", "VARCHAR", "'active'"),
    ("comment", "status", "VARCHAR", "'active'"),
    ("user", "zip_code", "VARCHAR", None),
    ("vendor", "tier_affinity", "VARCHAR(20)", None),
    ("vendor", "price_range_min", "FLOAT", None),
    ("vendor", "price_range_max", "FLOAT", None),
    ("vendor", "slug", "VARCHAR", None),
    ("vendor", "latitude", "FLOAT", None),
    ("vendor", "longitude", "FLOAT", None),

    # ClickoutEvent — Phase 4 anti-fraud + SDUI attribution (ROOT CAUSE of prod 502)
    ("clickout_event", "bid_id", "INTEGER", None),
    ("clickout_event", "is_suspicious", "BOOLEAN", "false"),
    ("clickout_event", "ip_address", "VARCHAR", None),
    ("clickout_event", "user_agent", "VARCHAR", None),

    # Bid — Phase 4 scoring dimensions
    ("bid", "combined_score", "FLOAT", None),
    ("bid", "relevance_score", "FLOAT", None),
    ("bid", "price_score", "FLOAT", None),
    ("bid", "quality_score", "FLOAT", None),
    ("bid", "diversity_bonus", "FLOAT", None),
    ("bid", "source_tier", "VARCHAR", None),
    # Bid — closing layer
    ("bid", "closing_status", "VARCHAR", None),
    ("bid", "contact_name", "VARCHAR", None),
    ("bid", "contact_email", "VARCHAR", None),
    ("bid", "contact_phone", "VARCHAR", None),
    # Bid — SDUI
    ("bid", "ui_schema_version", "INTEGER", "0"),

    # Row — SDUI + provider selection
    ("row", "selected_providers", "VARCHAR", None),
    ("row", "ui_schema_version", "INTEGER", "0"),
    # Row — outcome capture (Trust Metrics PRD §8.2)
    ("row", "row_outcome", "VARCHAR", None),
    ("row", "row_quality_assessment", "VARCHAR", None),
    ("row", "outcome_note", "VARCHAR", None),
    ("row", "routing_mode", "VARCHAR", None),

    # Project — SDUI
    ("project", "ui_schema_version", "INTEGER", "0"),

    # ShareLink — engagement metrics + permissions
    ("share_link", "permission", "VARCHAR", "'view_only'"),
    ("share_link", "access_count", "INTEGER", "0"),
    ("share_link", "unique_visitors", "INTEGER", "0"),
    ("share_link", "search_initiated_count", "INTEGER", "0"),
    ("share_link", "search_success_count", "INTEGER", "0"),
    ("share_link", "signup_conversion_count", "INTEGER", "0"),

    # User — referral + wallet + trust
    ("user", "referral_share_token", "VARCHAR", None),
    ("user", "signup_source", "VARCHAR", None),
    ("user", "referred_by_id", "INTEGER", None),
    ("user", "trust_level", "VARCHAR", "'standard'"),
    ("user", "wallet_balance_cents", "INTEGER", "0"),
    ("user", "ref_code", "VARCHAR", None),

    # AuditLog — extended fields
    ("audit_log", "timestamp", "TIMESTAMP", "NOW()"),
    ("audit_log", "session_id", "INTEGER", None),
    ("audit_log", "user_agent", "VARCHAR", None),
    ("audit_log", "resource_type", "VARCHAR", None),
    ("audit_log", "resource_id", "VARCHAR", None),
    ("audit_log", "success", "BOOLEAN", "true"),
    ("audit_log", "error_message", "VARCHAR", None),

    # OutreachCampaign — campaign v2 fields
    ("outreach_campaign", "user_id", "INTEGER", None),
    ("outreach_campaign", "request_summary", "VARCHAR", None),
    ("outreach_campaign", "structured_constraints", "VARCHAR", None),
    ("outreach_campaign", "action_budget", "INTEGER", "20"),
    ("outreach_campaign", "actions_used", "INTEGER", "0"),

    # OutreachMessage — full message fields
    ("outreach_message", "body_html", "VARCHAR", None),
    ("outreach_message", "from_address", "VARCHAR", None),
    ("outreach_message", "to_address", "VARCHAR", None),
    ("outreach_message", "reply_to_address", "VARCHAR", None),
    ("outreach_message", "sent_at", "TIMESTAMP", None),
    ("outreach_message", "opened_at", "TIMESTAMP", None),
    ("outreach_message", "replied_at", "TIMESTAMP", None),
    ("outreach_message", "metadata_json", "VARCHAR", None),

    # OutreachQuote — quote v2 fields
    ("outreach_quote", "entry_method", "VARCHAR", None),
    ("outreach_quote", "availability", "VARCHAR", None),
    ("outreach_quote", "terms", "VARCHAR", None),
    ("outreach_quote", "expiration_date", "VARCHAR", None),
    ("outreach_quote", "structured_data", "VARCHAR", None),
    ("outreach_quote", "confidence", "FLOAT", None),
    ("outreach_quote", "is_finalist", "BOOLEAN", "false"),

    # PopSwap — full coupon/swap fields
    ("pop_swap", "target_product", "VARCHAR", None),
    ("pop_swap", "swap_product_name", "VARCHAR", None),
    ("pop_swap", "swap_product_image", "VARCHAR", None),
    ("pop_swap", "swap_product_url", "VARCHAR", None),
    ("pop_swap", "offer_type", "VARCHAR", "'coupon'"),
    ("pop_swap", "discount_percent", "FLOAT", None),
    ("pop_swap", "offer_description", "VARCHAR", None),
    ("pop_swap", "brand_user_id", "INTEGER", None),
    ("pop_swap", "brand_contact_email", "VARCHAR", None),
    ("pop_swap", "provider_payout_cents", "INTEGER", None),
    ("pop_swap", "max_redemptions", "INTEGER", None),
    ("pop_swap", "current_redemptions", "INTEGER", "0"),
    ("pop_swap", "updated_at", "TIMESTAMP", None),

    # PopSwapClaim — verification + payment timestamps
    ("pop_swap_claim", "verified_at", "TIMESTAMP", None),
    ("pop_swap_claim", "paid_at", "TIMESTAMP", None),

    # VendorCoverageGap
    ("vendor_coverage_gap", "row_id", "INTEGER", None),
    ("vendor_coverage_gap", "user_id", "INTEGER", None),
    ("vendor_coverage_gap", "row_title", "VARCHAR", None),
    ("vendor_coverage_gap", "canonical_need", "VARCHAR", None),
    ("vendor_coverage_gap", "search_query", "VARCHAR", None),
    ("vendor_coverage_gap", "vendor_query", "VARCHAR", None),
    ("vendor_coverage_gap", "geo_hint", "VARCHAR", None),
    ("vendor_coverage_gap", "desire_tier", "VARCHAR", None),
    ("vendor_coverage_gap", "service_type", "VARCHAR", None),
    ("vendor_coverage_gap", "summary", "TEXT", None),
    ("vendor_coverage_gap", "rationale", "TEXT", None),
    ("vendor_coverage_gap", "suggested_queries", "JSONB", None),
    ("vendor_coverage_gap", "assessment", "JSONB", None),
    ("vendor_coverage_gap", "supporting_context", "JSONB", None),
    ("vendor_coverage_gap", "confidence", "FLOAT", "0.0"),
    ("vendor_coverage_gap", "times_seen", "INTEGER", "1"),
    ("vendor_coverage_gap", "status", "VARCHAR", "'new'"),
    ("vendor_coverage_gap", "emailed_count", "INTEGER", "0"),
    ("vendor_coverage_gap", "email_sent_at", "TIMESTAMP", None),
    ("vendor_coverage_gap", "first_seen_at", "TIMESTAMP", "NOW()"),
    ("vendor_coverage_gap", "last_seen_at", "TIMESTAMP", "NOW()"),
]

# Tables to migrate (order matters for FK constraints)
# Use tuple (old_name, new_name) for renamed tables
MIGRATE_TABLES = [
    "user",
    "seller",
    "project",
    "row",
    ("requestspec", "request_spec"),  # renamed table
    "bid",
    "auth_login_code",
    "auth_session",
    "audit_log",
    "bug_report",
    "clickout_event",
    "comment",
    "contract",
    "deal_handoff",
    "like",
    "merchant",
    "notification",
    "outreach_event",
    "purchase_event",
    "purchaseevent",
    "seller_bookmark",
    "seller_quote",
    "share_link",
    "share_search_event",
    "user_preference",
    "user_signal",
]


async def fix_schema(conn):
    """Add missing tables/columns and ensure pgvector is set up."""
    added = 0

    # Ensure pgvector extension exists
    try:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("[SCHEMA-FIX] pgvector extension ensured.")
    except Exception as e:
        print(f"[SCHEMA-FIX] WARNING: Could not create vector extension: {e}")

    # ── Ensure vendor table exists (s02_unify_vendor migration) ──────
    vrow = await conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'vendor'"
    ))
    if vrow.first() is None:
        await conn.execute(text("""
            CREATE TABLE vendor (
                id SERIAL PRIMARY KEY,
                name VARCHAR NOT NULL,
                email VARCHAR,
                domain VARCHAR,
                phone VARCHAR,
                website VARCHAR,
                category VARCHAR,
                specialties VARCHAR,
                description TEXT,
                tagline VARCHAR,
                image_url VARCHAR,
                profile_text TEXT,
                embedding vector(1536),
                embedding_model VARCHAR,
                embedded_at TIMESTAMP,
                contact_name VARCHAR,
                is_verified BOOLEAN NOT NULL DEFAULT false,
                status VARCHAR NOT NULL DEFAULT 'unverified',
                user_id INTEGER,
                stripe_account_id VARCHAR,
                stripe_onboarding_complete BOOLEAN NOT NULL DEFAULT false,
                default_commission_rate FLOAT NOT NULL DEFAULT 0.05,
                verification_level VARCHAR NOT NULL DEFAULT 'unverified',
                reputation_score FLOAT NOT NULL DEFAULT 0.0,
                tier_affinity VARCHAR(20),
                price_range_min FLOAT,
                price_range_max FLOAT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP,
                _migrated_from VARCHAR
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vendor_name ON vendor (name)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vendor_email ON vendor (email)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vendor_category ON vendor (category)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vendor_stripe ON vendor (stripe_account_id)"))
        print("[SCHEMA-FIX] Created vendor table with indexes")
        added += 1

    # ── Ensure audit_log table exists ─────────────────────────────
    try:
        arow = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_log'"
        ))
        if arow.first() is None:
            await conn.execute(text("""
                CREATE TABLE audit_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    user_id INTEGER,
                    session_id INTEGER,
                    ip_address VARCHAR,
                    user_agent VARCHAR,
                    action VARCHAR NOT NULL,
                    resource_type VARCHAR,
                    resource_id VARCHAR,
                    details VARCHAR,
                    success BOOLEAN NOT NULL DEFAULT true,
                    error_message VARCHAR
                )
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log (timestamp)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_user_id ON audit_log (user_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_action ON audit_log (action)"))
            print("[SCHEMA-FIX] Created audit_log table with indexes")
            added += 1
    except Exception as e:
        print(f"[SCHEMA-FIX] WARNING: Could not create audit_log table: {e}")

    try:
        vg_row = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'vendor_coverage_gap'"
        ))
        if vg_row.first() is None:
            await conn.execute(text("""
                CREATE TABLE vendor_coverage_gap (
                    id SERIAL PRIMARY KEY,
                    row_id INTEGER REFERENCES row(id),
                    user_id INTEGER REFERENCES "user"(id),
                    row_title VARCHAR NOT NULL,
                    canonical_need VARCHAR NOT NULL,
                    search_query VARCHAR,
                    vendor_query VARCHAR,
                    geo_hint VARCHAR,
                    desire_tier VARCHAR,
                    service_type VARCHAR,
                    summary TEXT NOT NULL,
                    rationale TEXT,
                    suggested_queries JSONB,
                    assessment JSONB,
                    supporting_context JSONB,
                    confidence FLOAT NOT NULL DEFAULT 0.0,
                    times_seen INTEGER NOT NULL DEFAULT 1,
                    status VARCHAR NOT NULL DEFAULT 'new',
                    emailed_count INTEGER NOT NULL DEFAULT 0,
                    email_sent_at TIMESTAMP,
                    first_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    last_seen_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS vendor_coverage_gap_status_idx ON vendor_coverage_gap (status)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS vendor_coverage_gap_need_idx ON vendor_coverage_gap (canonical_need)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS vendor_coverage_gap_last_seen_idx ON vendor_coverage_gap (last_seen_at)"))
            print("[SCHEMA-FIX] Created vendor_coverage_gap table with indexes")
            added += 1
    except Exception as e:
        print(f"[SCHEMA-FIX] WARNING: Could not create vendor_coverage_gap table: {e}")

    try:
        feedback_row = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'request_feedback'"
        ))
        if feedback_row.first() is None:
            await conn.execute(text("""
                CREATE TABLE request_feedback (
                    id SERIAL PRIMARY KEY,
                    row_id INTEGER REFERENCES row(id),
                    bid_id INTEGER REFERENCES bid(id),
                    user_id INTEGER REFERENCES "user"(id),
                    feedback_type VARCHAR NOT NULL,
                    score FLOAT,
                    comment TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS request_feedback_row_id_idx ON request_feedback (row_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS request_feedback_bid_id_idx ON request_feedback (bid_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS request_feedback_user_id_idx ON request_feedback (user_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS request_feedback_type_idx ON request_feedback (feedback_type)"))
            print("[SCHEMA-FIX] Created request_feedback table with indexes")
            added += 1
    except Exception as e:
        print(f"[SCHEMA-FIX] WARNING: Could not create request_feedback table: {e}")

    try:
        event_row = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'request_event'"
        ))
        if event_row.first() is None:
            await conn.execute(text("""
                CREATE TABLE request_event (
                    id SERIAL PRIMARY KEY,
                    row_id INTEGER REFERENCES row(id),
                    bid_id INTEGER REFERENCES bid(id),
                    user_id INTEGER REFERENCES "user"(id),
                    event_type VARCHAR NOT NULL,
                    event_value VARCHAR,
                    metadata_json TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS request_event_row_id_idx ON request_event (row_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS request_event_bid_id_idx ON request_event (bid_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS request_event_user_id_idx ON request_event (user_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS request_event_type_idx ON request_event (event_type)"))
            print("[SCHEMA-FIX] Created request_event table with indexes")
            added += 1
    except Exception as e:
        print(f"[SCHEMA-FIX] WARNING: Could not create request_event table: {e}")

    try:
        source_memory_row = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'source_memory'"
        ))
        if source_memory_row.first() is None:
            await conn.execute(text("""
                CREATE TABLE source_memory (
                    id SERIAL PRIMARY KEY,
                    domain VARCHAR NOT NULL,
                    source_name VARCHAR,
                    source_type VARCHAR,
                    source_subtype VARCHAR,
                    trust_score FLOAT NOT NULL DEFAULT 0.0,
                    prestige_score FLOAT NOT NULL DEFAULT 0.0,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    surface_count INTEGER NOT NULL DEFAULT 0,
                    shortlist_count INTEGER NOT NULL DEFAULT 0,
                    contact_success_count INTEGER NOT NULL DEFAULT 0,
                    negative_count INTEGER NOT NULL DEFAULT 0,
                    last_seen_at TIMESTAMP,
                    notes VARCHAR,
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS source_memory_domain_idx ON source_memory (domain)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS source_memory_source_type_idx ON source_memory (source_type)"))
            print("[SCHEMA-FIX] Created source_memory table with indexes")
            added += 1
    except Exception as e:
        print(f"[SCHEMA-FIX] WARNING: Could not create source_memory table: {e}")

    # ── Ensure vendor.search_vector GENERATED ALWAYS column exists ──
    # Migration s12_vendor_search_vector adds this, but if the table was
    # recreated or the migration didn't apply, hybrid search silently
    # falls back to vector-only. This is a safety net.
    try:
        sv_row = await conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'vendor' AND column_name = 'search_vector'"
        ))
        if sv_row.first() is None:
            await conn.execute(text("""
                ALTER TABLE vendor
                ADD COLUMN search_vector tsvector
                GENERATED ALWAYS AS (
                    setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(tagline, '')), 'B') ||
                    setweight(to_tsvector('english', coalesce(description, '')), 'C') ||
                    setweight(to_tsvector('english', coalesce(specialties, '')), 'C') ||
                    setweight(to_tsvector('english', coalesce(category, '')), 'D')
                ) STORED
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_vendor_search_vector
                ON vendor USING GIN (search_vector)
            """))
            print("[SCHEMA-FIX] + vendor.search_vector (tsvector GENERATED ALWAYS + GIN index)")
            added += 1
        else:
            # Column exists — ensure GIN index exists too
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_vendor_search_vector
                ON vendor USING GIN (search_vector)
            """))
    except Exception as e:
        print(f"[SCHEMA-FIX] WARNING: Could not ensure vendor.search_vector: {e}")

    # Fix vendor.embedding column type: varchar -> vector(1536)
    try:
        row = await conn.execute(text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'vendor' AND column_name = 'embedding'"
        ))
        col_type = row.scalar()
        if col_type and col_type == "character varying":
            await conn.execute(text(
                "ALTER TABLE vendor ALTER COLUMN embedding "
                "TYPE vector(1536) USING CASE WHEN embedding IS NOT NULL "
                "THEN embedding::vector(1536) ELSE NULL END"
            ))
            print("[SCHEMA-FIX] Fixed vendor.embedding: varchar -> vector(1536)")
            added += 1
    except Exception as e:
        print(f"[SCHEMA-FIX] WARNING: Could not fix vendor.embedding type: {e}")

    # ── Make bid.price and bid.total_cost nullable (s05 migration) ────
    for col in ["price", "total_cost"]:
        try:
            r = await conn.execute(text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'bid' AND column_name = :c"
            ), {"c": col})
            nullable = r.scalar()
            if nullable == "NO":
                await conn.execute(text(
                    f'ALTER TABLE bid ALTER COLUMN "{col}" DROP NOT NULL'
                ))
                print(f"[SCHEMA-FIX] Made bid.{col} nullable")
                added += 1
        except Exception as e:
            print(f"[SCHEMA-FIX] WARNING: Could not fix bid.{col} nullable: {e}")

    for table, col, pgtype, default in EXPECTED_COLS:
        # Skip if the table doesn't exist (avoid crash on missing tables)
        tbl_check = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ), {"t": table})
        if tbl_check.first() is None:
            continue

        row = await conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ), {"t": table, "c": col})
        if row.first() is None:
            defstr = f" DEFAULT {default}" if default else ""
            try:
                await conn.execute(text(
                    f'ALTER TABLE "{table}" ADD COLUMN "{col}" {pgtype}{defstr}'
                ))
                print(f"[SCHEMA-FIX] + {table}.{col} ({pgtype})")
                added += 1
            except Exception as e:
                print(f"[SCHEMA-FIX] WARNING: Could not add {table}.{col}: {e}")

    # ── Add JSON/JSONB columns that need special type ──────────────────
    JSON_COLS = [
        ("row", "ui_schema", "JSONB"),
        ("project", "ui_schema", "JSONB"),
        ("bid", "bid_ui_schema", "JSONB"),       # model: ui_schema, sa_column name: bid_ui_schema
        ("bid", "provenance", "JSONB"),
        ("vendor", "seo_content", "JSONB"),
        ("vendor", "schema_markup", "JSONB"),
        ("vendor_coverage_gap", "suggested_queries", "JSONB"),
        ("vendor_coverage_gap", "assessment", "JSONB"),
        ("vendor_coverage_gap", "supporting_context", "JSONB"),
    ]
    for table, col, pgtype in JSON_COLS:
        tbl_check = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ), {"t": table})
        if tbl_check.first() is None:
            continue
        row = await conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ), {"t": table, "c": col})
        if row.first() is None:
            try:
                await conn.execute(text(
                    f'ALTER TABLE "{table}" ADD COLUMN "{col}" {pgtype}'
                ))
                print(f"[SCHEMA-FIX] + {table}.{col} ({pgtype})")
                added += 1
            except Exception as e:
                print(f"[SCHEMA-FIX] WARNING: Could not add {table}.{col}: {e}")

    # Ensure request_spec table exists (model uses __tablename__='request_spec')
    row = await conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'request_spec'"
    ))
    if row.first() is None:
        # Check if requestspec exists (old naming)
        row2 = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'requestspec'"
        ))
        if row2.first() is not None:
            await conn.execute(text('ALTER TABLE "requestspec" RENAME TO "request_spec"'))
            print("[SCHEMA-FIX] Renamed requestspec -> request_spec")
            added += 1
        else:
            await conn.execute(text("""
                CREATE TABLE request_spec (
                    id SERIAL PRIMARY KEY,
                    item_name VARCHAR NOT NULL,
                    constraints VARCHAR NOT NULL,
                    preferences VARCHAR,
                    row_id INTEGER
                )
            """))
            print("[SCHEMA-FIX] Created request_spec table")
            added += 1

    if added:
        print(f"[SCHEMA-FIX] Fixed {added} schema issue(s).")
    else:
        print("[SCHEMA-FIX] Schema is up to date.")


async def main():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")

    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await fix_schema(conn)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())


