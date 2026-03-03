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
    ("row", "service_category", "VARCHAR", None),
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
    arow = await conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_log'"
    ))
    if arow.first() is None:
        await conn.execute(text("""
            CREATE TABLE audit_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                user_id INTEGER REFERENCES "user"(id),
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


async def migrate_data():
    """Copy data from old managed Postgres to current pgvector DB."""
    if not OLD_DATABASE_URL:
        print("[MIGRATE] OLD_DATABASE_URL not set, skipping migration.")
        return

    if not RUN_LEGACY_MIGRATION:
        print("[MIGRATE] RUN_LEGACY_MIGRATION is disabled, skipping migration.")
        return

    from database import engine as target_engine

    # Skip if migration fully completed (user 1 has phone AND request_spec has data)
    async with target_engine.begin() as tconn:
        row = await tconn.execute(text(
            "SELECT phone_number FROM \"user\" WHERE id = 1"
        ))
        u1 = row.first()
        rs = await tconn.execute(text("SELECT COUNT(*) FROM request_spec"))
        rs_count = rs.scalar() or 0
        if u1 and u1[0] == "+16503398297" and rs_count > 0:
            print(f"[MIGRATE] Migration already complete (user 1 has phone, {rs_count} request_specs). Skipping.")
            return

    # Normalize old URL for asyncpg
    old_url = OLD_DATABASE_URL
    if old_url.startswith("postgresql://"):
        old_url = old_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    old_engine = create_async_engine(old_url, pool_size=5)

    print("[MIGRATE] Connecting to old database...")
    try:
        async with old_engine.begin() as oconn:
            row = await oconn.execute(text('SELECT COUNT(*) FROM "row"'))
            old_count = row.scalar()
            print(f"[MIGRATE] Old DB has {old_count} rows.")
    except Exception as e:
        print(f"[MIGRATE] ERROR connecting to old DB: {e}")
        await old_engine.dispose()
        return

    # Migrate each table in its own transaction to avoid one failure killing all
    for entry in MIGRATE_TABLES:
        # Support tuple (old_name, new_name) for renamed tables
        if isinstance(entry, tuple):
            src_table, dst_table = entry
        else:
            src_table = dst_table = entry

        try:
            # Read from old DB
            async with old_engine.begin() as oconn:
                cols_result = await oconn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :t ORDER BY ordinal_position"
                ), {"t": src_table})
                old_cols = [r[0] for r in cols_result.fetchall()]
                if not old_cols:
                    continue

                # Read target columns in separate connection
                async with target_engine.begin() as tconn:
                    tcols_result = await tconn.execute(text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :t ORDER BY ordinal_position"
                    ), {"t": dst_table})
                    target_cols = set(r[0] for r in tcols_result.fetchall())

                if not target_cols:
                    print(f"[MIGRATE] Table {dst_table} doesn't exist in target, skipping.")
                    continue

                common_cols = [c for c in old_cols if c in target_cols]
                if not common_cols:
                    continue

                col_list = ", ".join(f'"{c}"' for c in common_cols)

                # Fetch all data from old DB
                rows = await oconn.execute(text(f'SELECT {col_list} FROM "{src_table}"'))
                all_rows = rows.fetchall()

            # Write to target DB — NEVER delete existing data
            async with target_engine.begin() as tconn:
                await tconn.execute(text("SET session_replication_role = 'replica'"))

                inserted = 0
                if all_rows:
                    placeholders = ", ".join(f":c{i}" for i in range(len(common_cols)))
                    insert_sql = (
                        f'INSERT INTO "{dst_table}" ({col_list}) VALUES ({placeholders}) '
                        f'ON CONFLICT DO NOTHING'
                    )
                    for row_data in all_rows:
                        params = {f"c{i}": v for i, v in enumerate(row_data)}
                        res = await tconn.execute(text(insert_sql), params)
                        inserted += res.rowcount

                # Fix sequence for this table
                try:
                    await tconn.execute(text(f"""
                        SELECT setval(pg_get_serial_sequence('"{dst_table}"', 'id'),
                               COALESCE((SELECT MAX(id) FROM "{dst_table}"), 1))
                    """))
                except Exception:
                    pass

                await tconn.execute(text("SET session_replication_role = 'origin'"))

            label = f"{src_table}->{dst_table}" if src_table != dst_table else dst_table
            skipped = len(all_rows) - inserted if all_rows else 0
            print(f"[MIGRATE] {label}: {inserted} inserted, {skipped} already existed")

        except Exception as e:
            print(f"[MIGRATE] {dst_table}: ERROR - {e}")

    await old_engine.dispose()
    print("[MIGRATE] Data migration complete!")


async def merge_phone_to_user1():
    """Ensure phone +16503398297 is on user 1 (lance@xcor-cto.com), not user 6."""
    from database import engine
    async with engine.begin() as conn:
        # Log current state
        row = await conn.execute(text(
            "SELECT id, email, phone_number FROM \"user\" WHERE id IN (1, 6) ORDER BY id"
        ))
        users = row.fetchall()
        for u in users:
            print(f"[MERGE] User {u[0]}: email={u[1]}, phone={u[2]}")

        # Always force: clear phone from ALL users except user 1
        await conn.execute(text(
            "UPDATE \"user\" SET phone_number = NULL WHERE phone_number = '+16503398297' AND id != 1"
        ))
        # Set phone on user 1
        await conn.execute(text(
            "UPDATE \"user\" SET phone_number = '+16503398297' WHERE id = 1"
        ))

        # Reassign user 6's rows, projects, sessions to user 1
        for tbl in ["row", "project", "auth_session", "auth_login_code"]:
            try:
                res = await conn.execute(text(
                    f'UPDATE "{tbl}" SET user_id = 1 WHERE user_id = 6'
                ))
                if res.rowcount > 0:
                    print(f"[MERGE] Reassigned {res.rowcount} {tbl} rows from user 6 -> 1")
            except Exception as e:
                print(f"[MERGE] {tbl}: {e}")

        # Verify
        row = await conn.execute(text(
            "SELECT phone_number FROM \"user\" WHERE id = 1"
        ))
        u1 = row.first()
        print(f"[MERGE] Done. User 1 phone = {u1[0] if u1 else 'NOT FOUND'}")


async def reset_vendor_sequence():
    """Reset vendor id sequence to MAX(id) to prevent UniqueViolationError after restore."""
    from database import engine
    async with engine.begin() as conn:
        await conn.execute(text(
            "SELECT setval(pg_get_serial_sequence('vendor','id'), "
            "COALESCE((SELECT MAX(id) FROM vendor), 1))"
        ))
    print("[FIX] vendor id sequence reset to MAX(id).")


async def main():
    from database import engine
    async with engine.begin() as conn:
        await fix_schema(conn)
    await reset_vendor_sequence()
    await migrate_data()
    if RUN_USER_PHONE_MERGE:
        await merge_phone_to_user1()
    else:
        print("[MERGE] RUN_USER_PHONE_MERGE is disabled, skipping phone merge step.")


if __name__ == "__main__":
    asyncio.run(main())
