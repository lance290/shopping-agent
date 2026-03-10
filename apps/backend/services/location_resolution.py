"""Forward geocoding with durable cache for location-aware search."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import LocationGeocodeCache
from sourcing.location import precision_weight_multiplier
from sourcing.models import LocationResolution

logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(days=30)
NEGATIVE_CACHE_TTL = timedelta(hours=24)


def normalize_place_query(place: str) -> str:
    return " ".join((place or "").strip().lower().split())


def build_cache_key(place: str, country_hint: Optional[str] = None) -> str:
    normalized = normalize_place_query(place)
    scoped = f"{normalized}|{(country_hint or '').strip().lower()}"
    return hashlib.sha256(scoped.encode("utf-8")).hexdigest()


def _guess_precision(result: dict) -> str:
    address = result.get("address") or {}
    if address.get("house_number"):
        return "address"
    if address.get("postcode"):
        return "postal_code"
    if address.get("suburb") or address.get("neighbourhood"):
        return "neighborhood"
    if address.get("city") or address.get("town") or address.get("village"):
        return "city"
    if address.get("county") or address.get("metro"):
        return "metro"
    return "region"


class LocationResolutionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve(self, place: str, country_hint: Optional[str] = None) -> LocationResolution:
        normalized_query = normalize_place_query(place)
        if not normalized_query:
            return LocationResolution(status="unresolved")

        cache_key = build_cache_key(place, country_hint=country_hint)
        cached = await self._load_cache(cache_key)
        if cached is not None:
            return cached

        live = await self._forward_geocode(place, country_hint=country_hint)
        await self._store_cache(place, normalized_query, cache_key, live, country_hint=country_hint)
        return live

    async def _load_cache(self, cache_key: str) -> Optional[LocationResolution]:
        result = await self.session.exec(
            select(LocationGeocodeCache).where(LocationGeocodeCache.cache_key == cache_key)
        )
        cache_row = result.first()
        if not cache_row:
            return None
        if cache_row.expires_at < datetime.utcnow():
            return None

        cache_row.hit_count = (cache_row.hit_count or 0) + 1
        cache_row.updated_at = datetime.utcnow()
        self.session.add(cache_row)
        await self.session.commit()
        return LocationResolution(
            normalized_label=cache_row.normalized_label,
            lat=cache_row.lat,
            lon=cache_row.lon,
            precision=cache_row.precision,
            resolved_by=cache_row.provider,
            resolved_at=cache_row.updated_at,
            status=cache_row.status,
        )

    async def _store_cache(
        self,
        place: str,
        normalized_query: str,
        cache_key: str,
        resolution: LocationResolution,
        country_hint: Optional[str] = None,
    ) -> None:
        result = await self.session.exec(
            select(LocationGeocodeCache).where(LocationGeocodeCache.cache_key == cache_key)
        )
        cache_row = result.first() or LocationGeocodeCache(
            cache_key=cache_key,
            query_text=place,
            normalized_query=normalized_query,
            country_hint=country_hint,
            expires_at=datetime.utcnow(),
        )
        cache_row.normalized_label = resolution.normalized_label
        cache_row.lat = resolution.lat
        cache_row.lon = resolution.lon
        cache_row.precision = resolution.precision
        cache_row.status = resolution.status
        cache_row.provider = resolution.resolved_by
        cache_row.expires_at = datetime.utcnow() + (
            CACHE_TTL if resolution.status == "resolved" else NEGATIVE_CACHE_TTL
        )
        cache_row.updated_at = datetime.utcnow()
        self.session.add(cache_row)
        await self.session.commit()

    async def _forward_geocode(self, place: str, country_hint: Optional[str] = None) -> LocationResolution:
        endpoint = os.getenv("FORWARD_GEOCODE_URL", "https://nominatim.openstreetmap.org/search")
        params = {"q": place, "format": "jsonv2", "addressdetails": 1, "limit": 1}
        if country_hint:
            params["countrycodes"] = country_hint.lower()
        headers = {"User-Agent": os.getenv("FORWARD_GEOCODE_USER_AGENT", "buyanything-location-search/1.0")}
        try:
            async with httpx.AsyncClient(timeout=3.0, headers=headers) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("[LocationResolution] forward geocode failed for %r: %s", place, exc)
            return LocationResolution(status="unresolved", resolved_by="forward_geocode")

        if not isinstance(payload, list) or not payload:
            return LocationResolution(status="unresolved", resolved_by="forward_geocode")

        first = payload[0]
        try:
            lat = float(first.get("lat"))
            lon = float(first.get("lon"))
        except (TypeError, ValueError):
            return LocationResolution(status="unresolved", resolved_by="forward_geocode")
        precision = _guess_precision(first)
        return LocationResolution(
            normalized_label=first.get("display_name") or place,
            lat=lat,
            lon=lon,
            precision=precision,
            resolved_by="forward_geocode",
            resolved_at=datetime.utcnow(),
            status="resolved",
        )


__all__ = [
    "LocationResolutionService",
    "build_cache_key",
    "normalize_place_query",
    "precision_weight_multiplier",
]
