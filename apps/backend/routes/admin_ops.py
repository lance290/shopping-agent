"""Admin operations routes — DB diagnostics, cleanup, vendor restore."""
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import User, VendorCoverageGap
from dependencies import require_admin
from services.email import send_vendor_coverage_report_email
import os

router = APIRouter(tags=["admin"])


def _get_ops_key() -> str:
    return os.getenv("ADMIN_OPS_KEY", "sh_ops_2026_secure_key")

def _get_restore_key() -> str:
    return os.getenv("ADMIN_RESTORE_KEY", "sh_restore_vendors_2026_secure_key")


@router.post("/admin/ops/restore-vendors")
async def restore_vendors_endpoint(
    x_restore_key: str = Header(None),
    dump_file: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Trigger vendor restoration from bundled dump file.
    Protected by X-Restore-Key header.
    """
    if x_restore_key != _get_restore_key():
        raise HTTPException(status_code=403, detail="Invalid restore key")

    from scripts.restore_vendors import restore_vendors_logic

    if dump_file is not None:
        payload = await dump_file.read()
        if not payload:
            raise HTTPException(status_code=400, detail="Uploaded dump file is empty")
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        filename = (dump_file.filename or "").lower()
        is_gzip = filename.endswith(".gz") or dump_file.content_type in {"application/gzip", "application/x-gzip"}
        json_path = data_dir / "vendors_prod_dump.json"
        gz_path = data_dir / "vendors_prod_dump.json.gz"
        if is_gzip:
            json_path.unlink(missing_ok=True)
            gz_path.write_bytes(payload)
        else:
            gz_path.unlink(missing_ok=True)
            json_path.write_bytes(payload)

    try:
        count = await restore_vendors_logic(session)
        return {"status": "success", "restored_count": count}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/ops/upsert-vendors-csv")
async def upsert_vendors_csv_endpoint(
    x_restore_key: str = Header(None),
    csv_file: Optional[UploadFile] = File(None),
    skip_embed: bool = True,
    skip_geo: bool = True,
):
    if x_restore_key != _get_restore_key():
        raise HTTPException(status_code=403, detail="Invalid restore key")
    if csv_file is None:
        raise HTTPException(status_code=400, detail="CSV file is required")

    payload = await csv_file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty")

    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    upload_path = data_dir / "vendor_upsert_upload.csv"
    upload_path.write_bytes(payload)

    from scripts.upsert_enriched_csv import upsert_csv

    try:
        result = await upsert_csv(upload_path, dry_run=False, skip_embed=skip_embed, skip_geo=skip_geo)
        return {"status": "success", **result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/ops/db-diag")
async def db_diagnostics(
    x_ops_key: str = Header(None),
):
    """DB diagnostics — disk size, table sizes, index status, vendor stats. Key-secured."""
    if x_ops_key != _get_ops_key():
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
    if x_ops_key != _get_ops_key():
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
    if x_ops_key != _get_ops_key():
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


@router.post("/admin/ops/vendor-coverage-report")
async def send_vendor_coverage_report(
    x_ops_key: str = Header(None),
    status: str = "new",
    limit: int = 25,
    mark_emailed: bool = True,
    session: AsyncSession = Depends(get_session),
):
    """Send the current vendor coverage gap queue as an email report."""
    if x_ops_key != _get_ops_key():
        raise HTTPException(status_code=403, detail="Invalid ops key")

    stmt = (
        select(VendorCoverageGap)
        .where(VendorCoverageGap.status == status)
        .order_by(VendorCoverageGap.confidence.desc(), VendorCoverageGap.last_seen_at.desc())
        .limit(limit)
    )
    result = await session.exec(stmt)
    gaps = list(result.all())
    if not gaps:
        return {"status": "noop", "count": 0, "report_status": status}

    requesters: dict[int, User] = {}
    for gap in gaps:
        if gap.user_id and gap.user_id not in requesters:
            requester = await session.get(User, gap.user_id)
            if requester:
                requesters[gap.user_id] = requester

    payload = [
        {
            "id": gap.id,
            "row_title": gap.row_title,
            "canonical_need": gap.canonical_need,
            "search_query": gap.search_query,
            "vendor_query": gap.vendor_query,
            "geo_hint": gap.geo_hint,
            "summary": gap.summary,
            "rationale": gap.rationale,
            "confidence": gap.confidence,
            "times_seen": gap.times_seen,
            "suggested_queries": gap.suggested_queries or [],
            "requester_name": requesters.get(gap.user_id).name if gap.user_id in requesters else None,
            "requester_company": requesters.get(gap.user_id).company if gap.user_id in requesters else None,
            "requester_email": requesters.get(gap.user_id).email if gap.user_id in requesters else None,
            "requester_phone": requesters.get(gap.user_id).phone_number if gap.user_id in requesters else None,
            "missing_requester_identity": [
                field
                for field, value in {
                    "name": requesters.get(gap.user_id).name if gap.user_id in requesters else None,
                    "company": requesters.get(gap.user_id).company if gap.user_id in requesters else None,
                }.items()
                if not (value or "").strip()
            ] if gap.user_id in requesters else ["name", "company"],
        }
        for gap in gaps
    ]
    email_result = await send_vendor_coverage_report_email(payload, report_label=status)
    if not email_result.success:
        raise HTTPException(status_code=500, detail=email_result.error or "Failed to send report")

    if mark_emailed:
        sent_at = datetime.utcnow()
        for gap in gaps:
            gap.status = "emailed"
            gap.email_sent_at = sent_at
            gap.emailed_count = (gap.emailed_count or 0) + 1
            session.add(gap)
        await session.commit()

    return {
        "status": "sent",
        "count": len(gaps),
        "report_status": status,
        "message_id": email_result.message_id,
    }
