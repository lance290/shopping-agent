"""PRD-03 phase 2: Unify vendor model — merge seller, vendor_profile, merchant into vendor

Revision ID: s02_unify_vendor
Revises: s01_json_to_jsonb
Create Date: 2026-02-14

Merges three overlapping vendor entities into a single `vendor` table:
  1. Create `vendor` table with superset of fields
  2. Migrate `seller` rows (preserve IDs for bid FK integrity)
  3. Migrate `vendor_profile` rows (offset IDs, preserve embeddings)
  4. Migrate `merchant` rows (merge by email/domain match or insert)
  5. Add `bid.vendor_id` column, populate from `bid.seller_id`
  6. Drop `bid.seller_id`, rename constraints
  7. Drop old tables: `seller`, `vendor_profile`, `merchant`

Rollback: Recreates old tables and restores data from `vendor`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = 's02_unify_vendor'
down_revision: Union[str, Sequence[str], None] = 's01_json_to_jsonb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge seller + vendor_profile + merchant into unified vendor table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # ── Step 1: Create vendor table ─────────────────────────────────
    if 'vendor' not in tables:
        op.create_table(
            'vendor',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            # Identity
            sa.Column('name', sa.String(), nullable=False, index=True),
            sa.Column('email', sa.String(), nullable=True, index=True),
            sa.Column('domain', sa.String(), nullable=True),
            sa.Column('phone', sa.String(), nullable=True),
            sa.Column('website', sa.String(), nullable=True),
            # Classification
            sa.Column('category', sa.String(), nullable=True, index=True),
            sa.Column('service_areas', sa.JSON(), nullable=True),
            sa.Column('specialties', sa.String(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('tagline', sa.String(), nullable=True),
            sa.Column('image_url', sa.String(), nullable=True),
            # Search / embeddings
            sa.Column('profile_text', sa.Text(), nullable=True),
            sa.Column('embedding', sa.JSON(), nullable=True),
            sa.Column('embedding_model', sa.String(), nullable=True),
            sa.Column('embedded_at', sa.DateTime(), nullable=True),
            # Contact (from Seller enhanced fields)
            sa.Column('contact_name', sa.String(), nullable=True),
            # Status & trust
            sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('status', sa.String(), nullable=False, server_default='unverified'),
            # Merchant fields (preserved for active registration flow)
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
            sa.Column('stripe_account_id', sa.String(), nullable=True, index=True),
            sa.Column('stripe_onboarding_complete', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('default_commission_rate', sa.Float(), nullable=False, server_default='0.05'),
            sa.Column('verification_level', sa.String(), nullable=False, server_default='unverified'),
            sa.Column('reputation_score', sa.Float(), nullable=False, server_default='0.0'),
            # Timestamps
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            # Source tracking for migration audit
            sa.Column('_migrated_from', sa.String(), nullable=True),
        )

    # ── Step 2: Migrate seller rows (preserve IDs) ──────────────────
    if 'seller' in tables:
        conn.execute(text("""
            INSERT INTO vendor (id, name, email, domain, is_verified, image_url,
                                category, contact_name, phone, _migrated_from)
            SELECT id, name, email, domain, is_verified,
                   image_url, category, contact_name, phone, 'seller'
            FROM seller
            ON CONFLICT (id) DO NOTHING
        """))

        # Reset sequence to max seller id
        conn.execute(text("""
            SELECT setval(pg_get_serial_sequence('vendor', 'id'),
                          GREATEST((SELECT COALESCE(MAX(id), 0) FROM vendor), 1))
        """))

    # ── Step 3: Migrate vendor_profile rows (offset IDs) ────────────
    if 'vendor_profile' in tables:
        conn.execute(text("""
            INSERT INTO vendor (name, email, domain, phone, website,
                                category, service_areas, specialties,
                                description, tagline, image_url,
                                profile_text, embedding, embedding_model, embedded_at,
                                created_at, updated_at, _migrated_from)
            SELECT vp.company, vp.contact_email, vp.website, vp.contact_phone, vp.website,
                   vp.category,
                   CASE WHEN vp.service_areas IS NOT NULL THEN vp.service_areas::jsonb ELSE NULL END,
                   vp.specialties,
                   vp.description, vp.tagline, vp.image_url,
                   vp.profile_text, vp.embedding, vp.embedding_model, vp.embedded_at,
                   vp.created_at, vp.updated_at, 'vendor_profile'
            FROM vendor_profile vp
            WHERE NOT EXISTS (
                SELECT 1 FROM vendor v
                WHERE LOWER(v.email) = LOWER(vp.contact_email)
                  AND vp.contact_email IS NOT NULL
            )
        """))

    # ── Step 4: Migrate merchant rows ───────────────────────────────
    if 'merchant' in tables:
        # Update existing vendor rows that match merchants by email
        conn.execute(text("""
            UPDATE vendor v
            SET status = m.status,
                user_id = m.user_id,
                stripe_account_id = m.stripe_account_id,
                stripe_onboarding_complete = m.stripe_onboarding_complete,
                default_commission_rate = m.default_commission_rate,
                verification_level = m.verification_level,
                reputation_score = m.reputation_score,
                website = COALESCE(v.website, m.website),
                phone = COALESCE(v.phone, m.phone)
            FROM merchant m
            WHERE m.seller_id = v.id
               OR (LOWER(m.email) = LOWER(v.email) AND v.email IS NOT NULL)
        """))

        # Insert merchants that didn't match any existing vendor
        conn.execute(text("""
            INSERT INTO vendor (name, email, phone, website, status, user_id,
                                stripe_account_id, stripe_onboarding_complete,
                                default_commission_rate, verification_level,
                                reputation_score, created_at, updated_at, _migrated_from)
            SELECT m.business_name, m.email, m.phone, m.website, m.status, m.user_id,
                   m.stripe_account_id, m.stripe_onboarding_complete,
                   m.default_commission_rate, m.verification_level,
                   m.reputation_score, m.created_at, m.updated_at, 'merchant'
            FROM merchant m
            WHERE NOT EXISTS (
                SELECT 1 FROM vendor v
                WHERE m.seller_id = v.id
                   OR (LOWER(m.email) = LOWER(v.email) AND v.email IS NOT NULL)
            )
        """))

    # ── Step 5: Add bid.vendor_id, populate from seller_id ──────────
    if 'bid' in tables:
        bid_columns = [c["name"] for c in inspector.get_columns("bid")]
        if 'vendor_id' not in bid_columns:
            op.add_column('bid', sa.Column('vendor_id', sa.Integer(),
                                           sa.ForeignKey('vendor.id'), nullable=True))

        if 'seller_id' in bid_columns:
            conn.execute(text("UPDATE bid SET vendor_id = seller_id WHERE vendor_id IS NULL"))

            # Create index on new column
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bid_vendor_id ON bid (vendor_id)"))

            # Drop old FK constraint and column
            # Find the constraint name first
            conn.execute(text("""
                DO $$
                DECLARE r RECORD;
                BEGIN
                    FOR r IN (
                        SELECT tc.constraint_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.constraint_column_usage ccu
                          ON tc.constraint_name = ccu.constraint_name
                        WHERE tc.table_name = 'bid'
                          AND tc.constraint_type = 'FOREIGN KEY'
                          AND ccu.column_name = 'id'
                          AND ccu.table_name = 'seller'
                    ) LOOP
                        EXECUTE 'ALTER TABLE bid DROP CONSTRAINT ' || r.constraint_name;
                    END LOOP;
                END $$;
            """))

            # Drop old index if exists
            conn.execute(text("DROP INDEX IF EXISTS ix_bid_seller_id"))

            op.drop_column('bid', 'seller_id')

    # ── Step 6: Update merchant references ──────────────────────────
    # Update purchase_event.seller_id if it exists
    if 'purchase_event' in tables:
        pe_cols = [c["name"] for c in inspector.get_columns("purchase_event")]
        if 'seller_id' in pe_cols and 'vendor_id' not in pe_cols:
            op.add_column('purchase_event', sa.Column('vendor_id', sa.Integer(),
                                                       sa.ForeignKey('vendor.id'), nullable=True))
            conn.execute(text("UPDATE purchase_event SET vendor_id = seller_id WHERE vendor_id IS NULL"))
            op.drop_column('purchase_event', 'seller_id')

    # ── Step 7: Drop old tables ─────────────────────────────────────
    # Must drop FK constraints first, then tables
    # Drop seller_bookmark (depends on merchant) if it exists
    if 'seller_bookmark' in inspector.get_table_names():
        op.drop_table('seller_bookmark')

    # Drop remaining FK constraints pointing at old tables
    conn.execute(text("""
        DO $$
        DECLARE r RECORD;
        BEGIN
            FOR r IN (
                SELECT tc.table_name, tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu
                  ON tc.constraint_name = ccu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND ccu.table_name IN ('seller', 'merchant', 'vendor_profile')
            ) LOOP
                EXECUTE 'ALTER TABLE ' || r.table_name || ' DROP CONSTRAINT IF EXISTS ' || r.constraint_name;
            END LOOP;
        END $$;
    """))

    for tbl in ['vendor_profile', 'merchant', 'seller']:
        if tbl in inspector.get_table_names():
            op.drop_table(tbl)


def downgrade() -> None:
    """Recreate seller table and restore bid.seller_id from vendor_id.

    Note: This is a best-effort rollback. vendor_profile and merchant data
    merged into vendor cannot be perfectly separated back. The seller table
    is fully restored since IDs were preserved.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Recreate seller table
    if 'seller' not in tables:
        op.create_table(
            'seller',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('name', sa.String(), nullable=False, index=True),
            sa.Column('email', sa.String(), nullable=True, index=True),
            sa.Column('domain', sa.String(), nullable=True),
            sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('image_url', sa.String(), nullable=True),
            sa.Column('category', sa.String(), nullable=True, index=True),
            sa.Column('contact_name', sa.String(), nullable=True),
            sa.Column('phone', sa.String(), nullable=True),
        )

        # Restore seller rows from vendor where _migrated_from = 'seller'
        conn.execute(text("""
            INSERT INTO seller (id, name, email, domain, is_verified, image_url,
                                category, contact_name, phone)
            SELECT id, name, email, domain, is_verified, image_url,
                   category, contact_name, phone
            FROM vendor
            WHERE _migrated_from = 'seller'
        """))

    # Restore bid.seller_id
    if 'bid' in tables:
        bid_cols = [c["name"] for c in inspector.get_columns("bid")]
        if 'seller_id' not in bid_cols and 'vendor_id' in bid_cols:
            op.add_column('bid', sa.Column('seller_id', sa.Integer(),
                                           sa.ForeignKey('seller.id'), nullable=True))
            conn.execute(text("UPDATE bid SET seller_id = vendor_id"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bid_seller_id ON bid (seller_id)"))
            conn.execute(text("DROP INDEX IF EXISTS ix_bid_vendor_id"))
            op.drop_column('bid', 'vendor_id')

    # Drop vendor table
    if 'vendor' in tables:
        op.drop_table('vendor')
