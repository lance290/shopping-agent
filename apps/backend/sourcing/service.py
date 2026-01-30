"""Sourcing service for orchestrating search and result persistence."""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Bid, Row, Seller
from sourcing.models import NormalizedResult, ProviderStatusSnapshot
from sourcing.repository import SourcingRepository

logger = logging.getLogger(__name__)


class SourcingService:
    def __init__(self, session: AsyncSession, sourcing_repo: SourcingRepository):
        self.session = session
        self.repo = sourcing_repo

    async def search_and_persist(
        self,
        row_id: int,
        query: str,
        providers: Optional[List[str]] = None,
    ) -> Tuple[List[Bid], List[ProviderStatusSnapshot]]:
        """
        Execute search across providers, normalize results, and persist them as Bids.
        
        Args:
            row_id: ID of the row to attach bids to
            query: Search query string
            providers: Optional list of provider IDs to use
            
        Returns:
            Tuple of (persisted_bids, provider_statuses)
        """
        # 1. Execute Search
        search_response = await self.repo.search_all_with_status(query, providers=providers)
        normalized_results = search_response.normalized_results
        provider_statuses = search_response.provider_statuses
        
        # If no normalized results (e.g. legacy providers only), fallback to normalizing raw results
        if not normalized_results and search_response.results:
            # Fallback logic if needed, or rely on repo to handle normalization
            pass

        logger.info(
            f"[SourcingService] Row {row_id}: Got {len(normalized_results)} normalized results from {len(provider_statuses)} providers"
        )

        # 2. Persist Results
        bids = await self._persist_results(row_id, normalized_results)

        return bids, provider_statuses

    async def _persist_results(self, row_id: int, results: List[NormalizedResult]) -> List[Bid]:
        """Persist normalized results as Bids, creating Sellers as needed. Returns list of Bids."""
        if not results:
            return []

        # Fetch existing bids to handle upserts (deduplication)
        # We assume canonical_url is the primary deduplication key if present, otherwise item_url
        existing_bids_stmt = select(Bid).where(Bid.row_id == row_id)
        existing_bids_res = await self.session.exec(existing_bids_stmt)
        existing_bids = existing_bids_res.all()
        
        # Map existing bids by canonical_url (preferred) and item_url (fallback)
        bids_by_canonical = {b.canonical_url: b for b in existing_bids if b.canonical_url}
        bids_by_url = {b.item_url: b for b in existing_bids if b.item_url}

        processed_bids: List[Bid] = []
        new_bids_count = 0
        updated_bids_count = 0

        for res in results:
            # 2.1 Get or Create Seller
            seller = await self._get_or_create_seller(res.merchant_name, res.merchant_domain)
            
            # 2.2 Check for existing bid
            existing_bid = None
            if res.canonical_url and res.canonical_url in bids_by_canonical:
                existing_bid = bids_by_canonical[res.canonical_url]
            elif res.url in bids_by_url:
                existing_bid = bids_by_url[res.url]

            if existing_bid:
                # Update
                existing_bid.price = res.price if res.price is not None else existing_bid.price
                existing_bid.total_cost = existing_bid.price + existing_bid.shipping_cost
                existing_bid.currency = res.currency
                existing_bid.item_title = res.title
                existing_bid.image_url = res.image_url
                existing_bid.source = res.source
                existing_bid.seller_id = seller.id
                existing_bid.canonical_url = res.canonical_url
                
                self.session.add(existing_bid)
                processed_bids.append(existing_bid)
                updated_bids_count += 1
            else:
                # Create
                new_bid = Bid(
                    row_id=row_id,
                    seller_id=seller.id,
                    price=res.price or 0.0,
                    total_cost=res.price or 0.0,
                    currency=res.currency,
                    item_title=res.title,
                    item_url=res.url,
                    image_url=res.image_url,
                    source=res.source,
                    canonical_url=res.canonical_url,
                    is_selected=False
                )
                self.session.add(new_bid)
                # Add to maps to prevent duplicates within the same batch
                if new_bid.canonical_url:
                    bids_by_canonical[new_bid.canonical_url] = new_bid
                bids_by_url[new_bid.item_url] = new_bid
                
                processed_bids.append(new_bid)
                new_bids_count += 1

        await self.session.commit()
        
        # Reload bids with eager loading to avoid MissingGreenlet error on relationship access
        if not processed_bids:
            return []
            
        bid_ids = [b.id for b in processed_bids if b.id is not None]
        if not bid_ids:
            return []
            
        stmt = select(Bid).where(Bid.id.in_(bid_ids)).options(selectinload(Bid.seller))
        result = await self.session.exec(stmt)
        reloaded_bids = result.all()
            
        logger.info(f"[SourcingService] Row {row_id}: Created {new_bids_count}, Updated {updated_bids_count} bids")
        return list(reloaded_bids)

    async def _get_or_create_seller(self, name: str, domain: str) -> Seller:
        # Simple cache could be added here if needed for batch processing
        stmt = select(Seller).where(Seller.name == name)
        result = await self.session.exec(stmt)
        seller = result.first()
        
        if not seller:
            seller = Seller(name=name, domain=domain)
            self.session.add(seller)
            await self.session.commit()
            await self.session.refresh(seller)
            
        return seller
