"""
Startup migrations — lightweight, idempotent schema migrations run on every boot.

Extracted from main.py to keep it under 450 lines.
These run inside startup_event() wrapped in asyncio.timeout.
"""
import asyncio

from sqlalchemy import text


async def run_startup_migrations(engine) -> None:
    """Run all idempotent ALTER TABLE / CREATE TABLE migrations."""
    async with engine.begin() as conn:
        # Row columns
        await conn.execute(text("ALTER TABLE row ADD COLUMN IF NOT EXISTS chat_history TEXT;"))
        await conn.execute(text("ALTER TABLE row ADD COLUMN IF NOT EXISTS selected_providers TEXT;"))
        await conn.execute(text("ALTER TABLE row ADD COLUMN IF NOT EXISTS origin_channel VARCHAR;"))
        await conn.execute(text("ALTER TABLE row ADD COLUMN IF NOT EXISTS origin_message_id VARCHAR;"))
        await conn.execute(text("ALTER TABLE row ADD COLUMN IF NOT EXISTS origin_user_id INTEGER;"))

        await conn.execute(text("ALTER TABLE vendor ALTER COLUMN default_commission_rate SET DEFAULT 0.0;"))
        await conn.execute(text("UPDATE vendor SET default_commission_rate = 0.0 WHERE default_commission_rate IS DISTINCT FROM 0.0;"))

        # User columns
        await conn.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS name TEXT;'))
        await conn.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS company TEXT;'))

        # DealHandoff Phase 1+3 columns
        for col, dtype in [
            ("bid_id", "INTEGER"),
            ("vendor_id", "INTEGER"),
            ("vendor_email", "VARCHAR"),
            ("vendor_name", "VARCHAR"),
            ("acceptance_token", "VARCHAR"),
            ("buyer_accepted_at", "TIMESTAMP"),
            ("buyer_accepted_ip", "VARCHAR"),
            ("vendor_accepted_at", "TIMESTAMP"),
            ("vendor_accepted_ip", "VARCHAR"),
        ]:
            await conn.execute(text(
                f"ALTER TABLE deal_handoff ADD COLUMN IF NOT EXISTS {col} {dtype};"
            ))

        # Bid provenance
        await conn.execute(text("ALTER TABLE bid ADD COLUMN IF NOT EXISTS provenance TEXT;"))

        # Vendor SEO columns
        await conn.execute(text("ALTER TABLE vendor ADD COLUMN IF NOT EXISTS slug VARCHAR;"))
        await conn.execute(text("ALTER TABLE vendor ADD COLUMN IF NOT EXISTS seo_content JSONB;"))
        await conn.execute(text("ALTER TABLE vendor ADD COLUMN IF NOT EXISTS schema_markup JSONB;"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS vendor_slug_idx ON vendor (slug);"))

        # Vendor GEO column
        await conn.execute(text("ALTER TABLE vendor ADD COLUMN IF NOT EXISTS store_geo_location TEXT;"))

        # Drop dead service_areas column
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'vendor' AND column_name = 'service_areas'"
        ))
        if result.first() is not None:
            await conn.execute(text(
                "UPDATE vendor "
                "SET store_geo_location = COALESCE(store_geo_location, CAST(service_areas AS TEXT)) "
                "WHERE store_geo_location IS NULL"
            ))
            await conn.execute(text("ALTER TABLE vendor DROP COLUMN service_areas;"))

        # SDUI schema columns (Phase 0.2)
        await conn.execute(text("ALTER TABLE project ADD COLUMN IF NOT EXISTS ui_schema JSONB;"))
        await conn.execute(text("ALTER TABLE project ADD COLUMN IF NOT EXISTS ui_schema_version INTEGER DEFAULT 0;"))
        await conn.execute(text("ALTER TABLE row ADD COLUMN IF NOT EXISTS ui_schema JSONB;"))
        await conn.execute(text("ALTER TABLE row ADD COLUMN IF NOT EXISTS ui_schema_version INTEGER DEFAULT 0;"))
        await conn.execute(text("ALTER TABLE bid ADD COLUMN IF NOT EXISTS bid_ui_schema JSONB;"))
        await conn.execute(text("ALTER TABLE bid ADD COLUMN IF NOT EXISTS ui_schema_version INTEGER DEFAULT 0;"))

        # Project shopping mode (Ready to Shop / Edit List)
        await conn.execute(text("ALTER TABLE project ADD COLUMN IF NOT EXISTS shopping_mode BOOLEAN DEFAULT FALSE;"))

        # pg_trgm for fuzzy text search
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS vendor_name_trgm_idx ON vendor USING gin (name gin_trgm_ops);"
        ))

        # Vector similarity index on vendor embeddings.
        # IVFFlat chosen over HNSW because Railway Postgres containers have low
        # shared memory limits (~64MB) which cause HNSW builds to fail with
        # DiskFullError on the shared memory segment.
        # IVFFlat is much lighter on memory and perfectly adequate for <10k vectors.
        # lists ≈ sqrt(3700) ≈ 61
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS vendor_embedding_ivfflat_idx
            ON vendor USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 60);
        """))
        # Drop old HNSW index if it somehow exists from a previous attempt
        await conn.execute(text(
            "DROP INDEX IF EXISTS vendor_embedding_hnsw_idx;"
        ))

        # Deal Pipeline tables
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS deal (
                id SERIAL PRIMARY KEY,
                row_id INTEGER NOT NULL REFERENCES row(id),
                bid_id INTEGER REFERENCES bid(id),
                vendor_id INTEGER REFERENCES vendor(id),
                buyer_user_id INTEGER NOT NULL REFERENCES "user"(id),
                status VARCHAR NOT NULL DEFAULT 'negotiating',
                proxy_email_alias VARCHAR UNIQUE NOT NULL,
                vendor_quoted_price FLOAT,
                platform_fee_pct FLOAT NOT NULL DEFAULT 0.0,
                platform_fee_amount FLOAT,
                buyer_total FLOAT,
                currency VARCHAR NOT NULL DEFAULT 'USD',
                stripe_payment_intent_id VARCHAR,
                stripe_transfer_id VARCHAR,
                stripe_connect_account_id VARCHAR,
                agreed_terms_summary TEXT,
                fulfillment_notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP,
                terms_agreed_at TIMESTAMP,
                funded_at TIMESTAMP,
                completed_at TIMESTAMP,
                canceled_at TIMESTAMP
            );
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS deal_row_id_idx ON deal (row_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS deal_status_idx ON deal (status);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS deal_proxy_alias_idx ON deal (proxy_email_alias);"))
        await conn.execute(text("ALTER TABLE deal ALTER COLUMN platform_fee_pct SET DEFAULT 0.0;"))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS deal_message (
                id SERIAL PRIMARY KEY,
                deal_id INTEGER NOT NULL REFERENCES deal(id),
                sender_type VARCHAR NOT NULL,
                sender_email VARCHAR,
                subject VARCHAR,
                content_text TEXT NOT NULL,
                content_html TEXT,
                attachments JSONB,
                resend_message_id VARCHAR,
                ai_classification VARCHAR,
                ai_confidence FLOAT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS deal_message_deal_id_idx ON deal_message (deal_id);"))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vendor_bookmark (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES "user"(id),
                vendor_id INTEGER NOT NULL REFERENCES vendor(id),
                source_row_id INTEGER REFERENCES row(id),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS vendor_bookmark_user_id_idx ON vendor_bookmark (user_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS vendor_bookmark_vendor_id_idx ON vendor_bookmark (vendor_id);"))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS item_bookmark (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES "user"(id),
                canonical_url VARCHAR NOT NULL,
                source_row_id INTEGER REFERENCES row(id),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS item_bookmark_user_id_idx ON item_bookmark (user_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS item_bookmark_canonical_url_idx ON item_bookmark (canonical_url);"))

        # Seed test vendor (idempotent)
        await conn.execute(text("""
            INSERT INTO vendor (name, email, domain, website, category, description, specialties, status, is_verified, tier_affinity, created_at)
            SELECT 'Peak Aviation Solutions', 'lance@xcor-cto.com', 'flypeak.com', 'https://flypeak.com',
                   'Private Aviation', 'Private jet charter and aviation solutions provider',
                   'jet charter, private aviation, on-demand flights, aircraft management',
                   'unverified', false, 'ultra_high_end', NOW()
            WHERE NOT EXISTS (SELECT 1 FROM vendor WHERE domain = 'flypeak.com')
        """))

        # Pop family sharing tables
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS project_member (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES project(id),
                user_id INTEGER NOT NULL REFERENCES "user"(id),
                role VARCHAR NOT NULL DEFAULT 'member',
                channel VARCHAR NOT NULL DEFAULT 'email',
                invited_by INTEGER REFERENCES "user"(id),
                joined_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (project_id, user_id)
            );
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS project_invite (
                id VARCHAR PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES project(id),
                invited_by INTEGER NOT NULL REFERENCES "user"(id),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMP
            );
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS project_invite_project_id_idx ON project_invite (project_id);"
        ))

        # Pop swap/coupon tables
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pop_swap (
                id SERIAL PRIMARY KEY,
                category VARCHAR NOT NULL,
                target_product VARCHAR,
                swap_product_name VARCHAR NOT NULL,
                swap_product_image VARCHAR,
                swap_product_url VARCHAR,
                offer_type VARCHAR NOT NULL DEFAULT 'coupon',
                savings_cents INTEGER NOT NULL DEFAULT 0,
                discount_percent FLOAT,
                offer_description VARCHAR,
                terms VARCHAR,
                brand_name VARCHAR,
                brand_user_id INTEGER REFERENCES "user"(id),
                brand_contact_email VARCHAR,
                provider VARCHAR NOT NULL DEFAULT 'manual',
                provider_offer_id VARCHAR,
                provider_payout_cents INTEGER,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                expires_at TIMESTAMP,
                max_redemptions INTEGER,
                current_redemptions INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP
            );
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS pop_swap_category_idx ON pop_swap (category);"))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pop_swap_claim (
                id SERIAL PRIMARY KEY,
                swap_id INTEGER NOT NULL REFERENCES pop_swap(id),
                user_id INTEGER NOT NULL REFERENCES "user"(id),
                row_id INTEGER REFERENCES row(id),
                status VARCHAR NOT NULL DEFAULT 'claimed',
                claimed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                verified_at TIMESTAMP,
                paid_at TIMESTAMP,
                receipt_id VARCHAR REFERENCES receipt(id)
            );
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS pop_swap_claim_swap_id_idx ON pop_swap_claim (swap_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS pop_swap_claim_user_id_idx ON pop_swap_claim (user_id);"))

        # User zip_code
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'user' AND column_name = 'zip_code'
                ) THEN
                    ALTER TABLE "user" ADD COLUMN zip_code VARCHAR;
                END IF;
            END $$;
        """))

        print("Migration check: all startup migrations applied successfully")


async def run_data_integrity_check(engine) -> None:
    """Check vendor/user table existence and row counts."""
    async with engine.begin() as conn:
        vendor_exists = (
            await conn.execute(text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'vendor'"
                ")"
            ))
        ).scalar()
        user_exists = (
            await conn.execute(text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'user'"
                ")"
            ))
        ).scalar()

        vendor_count = (
            (await conn.execute(text('SELECT COUNT(*) FROM vendor'))).scalar() or 0
        ) if vendor_exists else 0
        user_count = (
            (await conn.execute(text('SELECT COUNT(*) FROM "user"'))).scalar() or 0
        ) if user_exists else 0

        if not vendor_exists:
            print("⚠️  WARNING: vendor table does not exist yet.")
        elif vendor_count == 0:
            print("⚠️  WARNING: vendor table is EMPTY — vendor data may be missing.")
            print("   Run: python scripts/seed_vendors.py to restore vendor records.")
        else:
            print(f"✓  Data check: {vendor_count} vendors, {user_count} users in DB")
