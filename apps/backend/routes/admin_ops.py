"""Admin operations routes — DB diagnostics, cleanup, vendor restore."""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import User
from dependencies import require_admin

router = APIRouter(tags=["admin"])

OPS_KEY = "sh_ops_2026_secure_key"


@router.post("/admin/ops/restore-vendors")
async def restore_vendors_endpoint(
    x_restore_key: str = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Trigger vendor restoration from bundled dump file.
    Protected by X-Restore-Key header.
    """
    if x_restore_key != "sh_restore_vendors_2026_secure_key":
        raise HTTPException(status_code=403, detail="Invalid restore key")

    from scripts.restore_vendors import restore_vendors_logic
    
    try:
        count = await restore_vendors_logic(session)
        return {"status": "success", "restored_count": count}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/ops/db-diag")
async def db_diagnostics(
    x_ops_key: str = Header(None),
):
    """DB diagnostics — disk size, table sizes, index status, vendor stats. Key-secured."""
    if x_ops_key != OPS_KEY:
        raise HTTPException(status_code=403, detail="Invalid ops key")

    from database import engine

    async with engine.connect() as conn:
        db_size = (await conn.execute(text(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        ))).scalar()

        top_tables = (await conn.execute(text(
            "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS size, "
            "pg_total_relation_size(relid) AS bytes "
            "FROM pg_catalog.pg_statio_user_tables "
            "ORDER BY pg_total_relation_size(relid) DESC LIMIT 15"
        ))).fetchall()

        vendor_stats = (await conn.execute(text(
            "SELECT COUNT(*) AS total, COUNT(embedding) AS with_emb, "
            "COUNT(*) - COUNT(embedding) AS without_emb FROM vendor"
        ))).first()

        ivfflat_exists = (await conn.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE indexname = 'vendor_embedding_ivfflat_idx'"
        ))).first()

        hnsw_exists = (await conn.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE indexname = 'vendor_embedding_hnsw_idx'"
        ))).first()

        trgm_exists = (await conn.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE indexname = 'vendor_name_trgm_idx'"
        ))).first()

        cleanup_tables = []
        for tbl, col in [("audit_log", "created_at"), ("clickout_event", "created_at"),
                         ("outreach_event", "created_at"), ("auth_login_code", "created_at")]:
            try:
                row = (await conn.execute(text(
                    f'SELECT COUNT(*) AS total, '
                    f'pg_size_pretty(pg_total_relation_size(\'{tbl}\')) AS size '
                    f'FROM "{tbl}"'
                ))).first()
                cleanup_tables.append({"table": tbl, "rows": row[0], "size": row[1]})
            except Exception:
                cleanup_tables.append({"table": tbl, "error": "not found"})

    return {
        "db_size": db_size,
        "top_tables": [{"name": r[0], "size": r[1], "bytes": r[2]} for r in top_tables],
        "vendors": {"total": vendor_stats[0], "with_embedding": vendor_stats[1], "without": vendor_stats[2]},
        "indexes": {
            "ivfflat_vector": bool(ivfflat_exists),
            "hnsw_vector": bool(hnsw_exists),
            "trgm_name": bool(trgm_exists),
        },
        "cleanup_candidates": cleanup_tables,
    }


@router.post("/admin/ops/create-vector-index")
async def create_vector_index(
    x_ops_key: str = Header(None),
):
    """Manually create the IVFFlat vector index if startup migrations were skipped."""
    if x_ops_key != OPS_KEY:
        raise HTTPException(status_code=403, detail="Invalid ops key")

    from database import engine
    import time

    t0 = time.monotonic()
    async with engine.begin() as conn:
        # Drop old HNSW if it exists
        await conn.execute(text("DROP INDEX IF EXISTS vendor_embedding_hnsw_idx;"))
        # Create IVFFlat (idempotent)
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS vendor_embedding_ivfflat_idx
            ON vendor USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 60);
        """))

    elapsed = round(time.monotonic() - t0, 2)

    # Verify
    async with engine.connect() as conn:
        exists = (await conn.execute(text(
            "SELECT indexname FROM pg_indexes WHERE indexname = 'vendor_embedding_ivfflat_idx'"
        ))).first()

    return {"status": "ok" if exists else "failed", "index": "vendor_embedding_ivfflat_idx", "elapsed_seconds": elapsed}


@router.post("/admin/ops/db-cleanup")
async def db_cleanup(
    x_ops_key: str = Header(None),
    days: int = 90,
):
    """Delete old audit/event rows older than N days + VACUUM. Key-secured."""
    if x_ops_key != OPS_KEY:
        raise HTTPException(status_code=403, detail="Invalid ops key")

    from database import engine

    cutoff = datetime.utcnow() - timedelta(days=days)
    deleted = {}

    async with engine.begin() as conn:
        for tbl, col in [("audit_log", "created_at"), ("clickout_event", "created_at"),
                         ("outreach_event", "created_at"), ("auth_login_code", "created_at")]:
            try:
                count = (await conn.execute(text(
                    f'SELECT COUNT(*) FROM "{tbl}" WHERE {col} < :cutoff'
                ), {"cutoff": cutoff})).scalar() or 0
                if count > 0:
                    await conn.execute(text(
                        f'DELETE FROM "{tbl}" WHERE {col} < :cutoff'
                    ), {"cutoff": cutoff})
                deleted[tbl] = count
            except Exception as e:
                deleted[tbl] = f"error: {e}"

    # VACUUM outside transaction
    async with engine.connect() as conn:
        await conn.execute(text("COMMIT"))
        for tbl, _ in [("audit_log", ""), ("clickout_event", ""),
                       ("outreach_event", ""), ("auth_login_code", "")]:
            try:
                await conn.execute(text(f'VACUUM "{tbl}"'))
            except Exception:
                pass

    # Check new size
    async with engine.connect() as conn:
        new_size = (await conn.execute(text(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        ))).scalar()

    return {"deleted": deleted, "days_kept": days, "db_size_after": new_size}
