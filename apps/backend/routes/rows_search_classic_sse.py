"""Classic (non-agent) streaming SSE pipeline for search results."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, List, Any, AsyncGenerator

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Row, Bid, User
from routes.bookmarks import _normalize_bookmark_url
from sourcing import SearchResult, ProviderStatusSnapshot
from routes.rows_search_helpers import (
    load_search_state_for_bids,
    _parse_intent_payload,
)
from routes.rows_search_coverage import (
    record_vendor_coverage_gap_if_needed,
    _build_vendor_coverage_user_message,
)
from sourcing.normalizers import normalize_generic_results
from sourcing.scorer import filter_vendor_results, score_results
from sourcing.service import SourcingService
from sourcing.discovery.classifier import classify_search_path
from sourcing.choice_filter import should_exclude_by_choices
from sourcing.messaging import determine_search_user_message
from routes.rows_search_discovery_sse import vendor_discovery_sse

logger = logging.getLogger(__name__)


async def generate_classic_sse(
    *,
    session: AsyncSession,
    row: Row,
    row_id: int,
    user_id: int,
    is_guest: bool,
    requester: Optional[User],
    sanitized_query: str,
    vendor_query: str,
    providers: Optional[List[str]],
    min_price_filter: Optional[float],
    max_price_filter: Optional[float],
    choice_constraints: dict,
    sourcing_service: SourcingService,
    sourcing_repo: Any,
) -> AsyncGenerator[str, None]:
    """Generate SSE events as each provider completes (classic pipeline)."""
    all_results: List[SearchResult] = []
    all_statuses: List[ProviderStatusSnapshot] = []
    all_persisted_bid_ids: set[int] = set()
    db_lock = asyncio.Lock()

    parsed_intent = _parse_intent_payload(row.search_intent)
    search_path = classify_search_path(parsed_intent, row)

    # Auto-set routing_mode for trust-metric analysis
    _STREAM_PATH_TO_MODE = {
        "commodity_marketplace_path": "affiliate_only",
        "vendor_discovery_path": "sourcing_only",
    }
    _resolved_mode = _STREAM_PATH_TO_MODE.get(search_path, "affiliate_plus_sourcing")
    if row.routing_mode != _resolved_mode:
        row.routing_mode = _resolved_mode
        session.add(row)
        await session.commit()

    intent_payload = parsed_intent.model_dump() if parsed_intent else None
    query_embedding = None
    quantum_reranker = None
    try:
        from sourcing.vendor_provider import build_query_embedding

        query_embedding = await build_query_embedding(
            vendor_query or sanitized_query,
            context_query=sanitized_query,
            intent_payload=intent_payload,
        )
    except Exception as e:
        logger.warning(f"[SEARCH STREAM] Query embedding failed: {e}")

    # Initialize quantum reranker (uses the shared query embedding)
    if query_embedding:
        try:
            from sourcing.quantum.reranker import QuantumReranker
            quantum_reranker = QuantumReranker()
            if not quantum_reranker.is_available():
                quantum_reranker = None
        except Exception as e:
            logger.warning(f"[SEARCH STREAM] Quantum reranker init failed (graceful degradation): {e}")

    if parsed_intent and search_path == "vendor_discovery_path":
        async for event_str in vendor_discovery_sse(
            session=session,
            row=row,
            row_id=row_id,
            user_id=user_id,
            is_guest=is_guest,
            requester=requester,
            sanitized_query=sanitized_query,
            vendor_query=vendor_query,
            min_price_filter=min_price_filter,
            max_price_filter=max_price_filter,
            sourcing_service=sourcing_service,
            parsed_intent=parsed_intent,
            intent_payload=intent_payload,
            query_embedding=query_embedding,
            all_results=all_results,
            all_statuses=all_statuses,
            all_persisted_bid_ids=all_persisted_bid_ids,
        ):
            yield event_str
        return

    generator = sourcing_repo.search_streaming(
        sanitized_query,
        providers=providers,
        min_price=min_price_filter,
        max_price=max_price_filter,
        desire_tier=row.desire_tier,
        vendor_query=vendor_query,
        intent_payload=intent_payload,
        query_embedding=query_embedding,  # shared — vendor_provider skips its own embed call
    )

    async def get_next_batch():
        try:
            return await anext(generator)
        except StopAsyncIteration:
            return None

    async def process_batch(provider_name, results, status, providers_remaining):
        from sourcing.filters import should_include_result as _should_include
        filtered_batch = []
        for r in results:
            title = getattr(r, "title", "")
            source = (getattr(r, "source", "") or "").lower()
            is_vector_searched = source == "vendor_directory"

            if not is_vector_searched and choice_constraints:
                if should_exclude_by_choices(title, choice_constraints):
                    continue

            if not _should_include(
                price=getattr(r, "price", None),
                source=getattr(r, "source", "") or "",
                desire_tier=row.desire_tier,
                min_price=min_price_filter,
                max_price=max_price_filter,
            ):
                continue
            filtered_batch.append(r)
        
        persisted_bid_ids = set()
        if filtered_batch:
            try:
                normalized_batch = normalize_generic_results(filtered_batch, provider_name)
                if normalized_batch:
                    normalized_batch = score_results(
                        normalized_batch,
                        intent=parsed_intent,
                        min_price=min_price_filter,
                        max_price=max_price_filter,
                        desire_tier=row.desire_tier,
                    )

                    # Quantum reranking: embed ALL results + score against user intent
                    if quantum_reranker and query_embedding:
                        try:
                            from sourcing.vendor_provider import _embed_texts as _batch_embed

                            results_for_quantum = []
                            texts_to_embed = []
                            for idx, res in enumerate(normalized_batch):
                                existing_emb = res.raw_data.get("embedding") if res.raw_data else None
                                rd = {"_idx": idx, "title": res.title, "embedding": existing_emb}
                                results_for_quantum.append(rd)
                                if not existing_emb:
                                    desc = ""
                                    if res.raw_data:
                                        desc = str(res.raw_data.get("snippet", "") or res.raw_data.get("description", "") or "")
                                    parts = [res.title, res.merchant_name]
                                    if desc:
                                        parts.append(desc[:200])
                                    texts_to_embed.append((idx, " | ".join(parts)))

                            if texts_to_embed:
                                embed_texts = [t for _, t in texts_to_embed]
                                new_embeddings = await _batch_embed(embed_texts)
                                if new_embeddings and len(new_embeddings) == len(texts_to_embed):
                                    for (idx, _), emb in zip(texts_to_embed, new_embeddings):
                                        results_for_quantum[idx]["embedding"] = emb

                            if any(r.get("embedding") for r in results_for_quantum):
                                reranked = await quantum_reranker.rerank_results(
                                    query_embedding=query_embedding,
                                    search_results=results_for_quantum,
                                    top_k=len(normalized_batch),
                                )
                                score_map = {}
                                for r in reranked:
                                    if r.get("quantum_reranked") and "_idx" in r:
                                        score_map[r["_idx"]] = r
                                for idx, res in enumerate(normalized_batch):
                                    if idx in score_map:
                                        qr = score_map[idx]
                                        res.provenance["quantum_score"] = qr.get("quantum_score", 0.0)
                                        res.provenance["blended_score"] = qr.get("blended_score", 0.0)
                                        res.provenance["novelty_score"] = qr.get("novelty_score", 0.0)
                                        res.provenance["coherence_score"] = qr.get("coherence_score", 0.0)
                                q_count = len(score_map)
                                emb_new = len(texts_to_embed) if texts_to_embed else 0
                                emb_reused = len(normalized_batch) - emb_new
                                logger.info(f"[SEARCH STREAM] Quantum reranked {q_count}/{len(normalized_batch)} from {provider_name} (embedded {emb_new} new, reused {emb_reused})")
                        except Exception as qe:
                            logger.warning(f"[SEARCH STREAM] Quantum reranking failed for {provider_name}: {qe}")

                    if provider_name == "vendor_directory":
                        before_count = len(normalized_batch)
                        normalized_batch = filter_vendor_results(
                            normalized_batch,
                            intent=parsed_intent,
                            is_service=row.is_service,
                            service_category=row.service_category,
                        )
                        dropped = before_count - len(normalized_batch)
                        if dropped:
                            logger.info(f"[SEARCH STREAM] Filtered {dropped} vendor results via shared vendor gate")

                    if normalized_batch:
                        async with db_lock:
                            persisted_bids = await sourcing_service._persist_results(row_id, normalized_batch)
                            persisted_bid_ids.update(b.id for b in persisted_bids if b.id)
            except Exception as err:
                logger.error(f"[SEARCH STREAM] Failed to persist results for provider {provider_name}: {err}")
                    
        return provider_name, filtered_batch, status, persisted_bid_ids

    pending_fetches = set()
    pending_fetches.add(asyncio.create_task(get_next_batch()))
    pending_processes = set()
    
    providers_completed = 0
    last_providers_remaining = len(providers) if providers else 8

    while pending_fetches or pending_processes:
        done, _ = await asyncio.wait(
            pending_fetches | pending_processes,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for task in done:
            if task in pending_fetches:
                pending_fetches.remove(task)
                try:
                    batch = await task
                    if batch is not None:
                        pending_fetches.add(asyncio.create_task(get_next_batch()))
                        
                        provider_name, results, status, providers_remaining = batch
                        last_providers_remaining = providers_remaining
                        all_statuses.append(status)
                        
                        pending_processes.add(asyncio.create_task(
                            process_batch(provider_name, results, status, providers_remaining)
                        ))
                except Exception as e:
                    logger.error(f"[SEARCH STREAM] Generator error: {e}")
                    
            elif task in pending_processes:
                pending_processes.remove(task)
                try:
                    provider_name, filtered_batch, status, persisted_bid_ids = await task
                    providers_completed += 1
                    
                    all_persisted_bid_ids.update(persisted_bid_ids)
                    all_results.extend(filtered_batch)
                    
                    actual_remaining = last_providers_remaining + len(pending_processes)
                    
                    event_data = {
                        "provider": provider_name,
                        "results": [r.model_dump() for r in filtered_batch],
                        "status": status.model_dump(),
                        "providers_remaining": actual_remaining,
                        "more_incoming": actual_remaining > 0,
                        "total_results_so_far": len(all_results),
                    }
                    
                    yield f"data: {json.dumps(event_data)}\n\n"
                except Exception as e:
                    logger.error(f"[SEARCH STREAM] Processing error: {e}")
    
    # Supersede stale bids AFTER all providers complete.
    try:
        existing_stmt = (
            select(Bid)
            .where(
                Bid.row_id == row_id,
                Bid.id.notin_(all_persisted_bid_ids) if all_persisted_bid_ids else True,
            )
            .options(selectinload(Bid.seller))
        )
        existing_res = await session.exec(existing_stmt)
        existing_bids = [bid for bid in existing_res.all() if not bid.is_superseded]
        bookmarked_vendors, bookmarked_items, _ = await load_search_state_for_bids(
            session,
            user_id,
            existing_bids,
        )
        protected_existing_ids = {
            bid.id
            for bid in existing_bids
            if bid.id is not None and (
                bid.is_selected
                or (bid.vendor_id and bid.vendor_id in bookmarked_vendors)
                or (_normalize_bookmark_url(bid.canonical_url or bid.item_url) in bookmarked_items)
            )
        }
        await sourcing_service.supersede_stale_bids(row_id, all_persisted_bid_ids | protected_existing_ids)
    except Exception as e:
        logger.error(f"[SEARCH STREAM] Failed to supersede stale bids: {e}")

    # Determine user_message based on results and statuses
    user_message = determine_search_user_message(all_results, all_statuses)

    # Update row status to reflect search completion
    try:
        from services.sdui_builder import build_ui_schema, build_zero_results_schema
        await session.refresh(row)
        if len(all_results) == 0:
            row.status = "sourcing"
            row.ui_schema = build_zero_results_schema(row)
            row.ui_schema_version = (row.ui_schema_version or 0) + 1
        else:
            row.status = "bids_arriving"
        row.updated_at = datetime.utcnow()
        session.add(row)
        await session.commit()
        coverage_assessment = await record_vendor_coverage_gap_if_needed(
            session=session,
            row=row,
            user_id=user_id,
            search_query=sanitized_query,
            results=all_results,
            provider_statuses=all_statuses,
        )
        if coverage_assessment and not user_message:
            user_message = _build_vendor_coverage_user_message(requester, is_guest)
    except Exception as e:
        logger.error(f"[SEARCH STREAM] Failed to update row status after completion: {e}")
        try:
            coverage_assessment = await record_vendor_coverage_gap_if_needed(
                session=session,
                row=row,
                user_id=user_id,
                search_query=sanitized_query,
                results=all_results,
                provider_statuses=all_statuses,
            )
            if coverage_assessment and not user_message:
                user_message = _build_vendor_coverage_user_message(requester, is_guest)
        except Exception as e:
            logger.error(f"[SEARCH STREAM] Failed to record vendor coverage gap: {e}")

    # Final event with complete status
    final_event = {
        "event": "complete",
        "total_results": len(all_results),
        "provider_statuses": [s.model_dump() for s in all_statuses],
        "more_incoming": False,
        "user_message": user_message,
    }
    yield f"data: {json.dumps(final_event)}\n\n"


