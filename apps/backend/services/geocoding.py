"""
Geocoding service for location resolution.

Supports multiple providers with fallback:
1. Nominatim (OpenStreetMap) - free, no API key required
2. Google Geocoding API - requires GEOCODING_API_KEY env var
3. Regex fallback - basic city/state extraction
"""

import logging
import os
import re
from typing import Dict, Optional, Tuple

import httpx

from sourcing.models import LocationResolution

logger = logging.getLogger(__name__)

# Nominatim endpoints (rate-limited, but free)
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "BuyAnythingOS/1.0 (sourcing@buyanything.com)"

# Google Geocoding API
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Airport code regex (IATA 3-letter codes)
AIRPORT_CODE_PATTERN = re.compile(r'\b([A-Z]{3})\b')

# City, State patterns
CITY_STATE_PATTERNS = [
    re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\b'),  # "Nashville, TN"
    re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+([A-Z]{2})\b'),   # "Nashville TN"
    re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*(Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)\b', re.IGNORECASE),
]

# Well-known airport codes with coordinates
AIRPORT_COORDS: Dict[str, Tuple[float, float]] = {
    "SAN": (32.7338, -117.1933),  # San Diego
    "BNA": (36.1245, -86.6782),   # Nashville
    "EWR": (40.6895, -74.1745),   # Newark
    "LAX": (33.9416, -118.4085),  # Los Angeles
    "JFK": (40.6413, -73.7781),   # New York JFK
    "ORD": (41.9742, -87.9073),   # Chicago O'Hare
    "DFW": (32.8998, -97.0403),   # Dallas/Fort Worth
    "ATL": (33.6407, -84.4277),   # Atlanta
    "DEN": (39.8561, -104.6737),  # Denver
    "PHX": (33.4352, -112.0101),  # Phoenix
    "LAS": (36.0840, -115.1537),  # Las Vegas
    "MIA": (25.7959, -80.2870),   # Miami
    "SEA": (47.4502, -122.3088),  # Seattle
    "SFO": (37.6213, -122.3790),  # San Francisco
}


class GeocodingService:
    """Geocoding service with multiple provider support and fallback."""

    def __init__(self):
        self.provider = os.environ.get("GEOCODING_PROVIDER", "nominatim").lower()
        self.google_api_key = os.environ.get("GEOCODING_API_KEY")
        self.timeout = 5.0  # seconds

    async def resolve_location(
        self,
        location_str: str,
        field_name: str
    ) -> LocationResolution:
        """
        Geocode a location string to lat/lon + precision.

        Args:
            location_str: Location string (e.g., "Nashville, TN", "SAN", "Denver, CO")
            field_name: Field name from LocationTargets (origin, destination, etc.)

        Returns:
            LocationResolution with status="resolved"/"unresolved"/"ambiguous"
        """
        if not location_str or not location_str.strip():
            return LocationResolution(
                status="unresolved",
                normalized_label=location_str or None,
            )

        location_str = location_str.strip()
        logger.info(f"[Geocoding] Resolving {field_name}='{location_str}'")

        # Try airport code first (instant, no API call)
        airport_result = self._try_airport_code(location_str)
        if airport_result:
            logger.info(f"[Geocoding] Airport match: {location_str} → {airport_result.lat}, {airport_result.lon}")
            return airport_result

        # Try regex fallback for simple patterns
        regex_result = self._try_regex_extraction(location_str)
        if regex_result:
            logger.info(f"[Geocoding] Regex extraction successful: {location_str}")
            # Now geocode the extracted city/state
            try:
                if self.provider == "google" and self.google_api_key:
                    return await self._geocode_google(location_str)
                else:
                    return await self._geocode_nominatim(location_str)
            except Exception as e:
                logger.warning(f"[Geocoding] API failed for '{location_str}': {e}, using regex-only result")
                return regex_result

        # Try full geocoding via API
        try:
            if self.provider == "google" and self.google_api_key:
                return await self._geocode_google(location_str)
            else:
                return await self._geocode_nominatim(location_str)
        except Exception as e:
            logger.error(f"[Geocoding] All methods failed for '{location_str}': {e}")
            return LocationResolution(
                status="unresolved",
                normalized_label=location_str,
            )

    def _try_airport_code(self, location_str: str) -> Optional[LocationResolution]:
        """Check if location is a known airport code."""
        match = AIRPORT_CODE_PATTERN.search(location_str.upper())
        if match:
            code = match.group(1)
            if code in AIRPORT_COORDS:
                lat, lon = AIRPORT_COORDS[code]
                return LocationResolution(
                    status="resolved",
                    normalized_label=f"{code} Airport",
                    lat=lat,
                    lon=lon,
                    precision="city",
                    resolved_by="airport_code",
                )
        return None

    def _try_regex_extraction(self, location_str: str) -> Optional[LocationResolution]:
        """Extract city/state using regex patterns."""
        for pattern in CITY_STATE_PATTERNS:
            match = pattern.search(location_str)
            if match:
                city = match.group(1).strip()
                state = match.group(2).strip().upper()
                return LocationResolution(
                    status="resolved",
                    normalized_label=f"{city}, {state}",
                    precision="city",
                    resolved_by="regex",
                    # No lat/lon yet - caller should try API geocoding
                )
        return None

    async def _geocode_nominatim(self, location_str: str) -> LocationResolution:
        """Geocode using Nominatim (OpenStreetMap)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                NOMINATIM_SEARCH_URL,
                params={
                    "q": location_str,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                },
                headers={"User-Agent": NOMINATIM_USER_AGENT}
            )
            response.raise_for_status()
            data = response.json()

            if not data or len(data) == 0:
                return LocationResolution(
                    status="unresolved",
                    normalized_label=location_str,
                )

            result = data[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            display_name = result.get("display_name", location_str)

            # Determine precision from result type
            place_type = result.get("type", "").lower()
            precision = self._map_nominatim_precision(place_type, result.get("address", {}))

            return LocationResolution(
                status="resolved",
                normalized_label=display_name,
                lat=lat,
                lon=lon,
                precision=precision,
                resolved_by="nominatim",
            )

    async def _geocode_google(self, location_str: str) -> LocationResolution:
        """Geocode using Google Geocoding API."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                GOOGLE_GEOCODE_URL,
                params={
                    "address": location_str,
                    "key": self.google_api_key,
                }
            )
            response.raise_for_status()
            data = response.json()

            if data["status"] != "OK" or not data.get("results"):
                return LocationResolution(
                    status="unresolved",
                    normalized_label=location_str,
                )

            result = data["results"][0]
            location = result["geometry"]["location"]
            lat = float(location["lat"])
            lon = float(location["lng"])
            display_name = result.get("formatted_address", location_str)

            # Determine precision from result types
            precision = self._map_google_precision(result.get("types", []))

            return LocationResolution(
                status="resolved",
                normalized_label=display_name,
                lat=lat,
                lon=lon,
                precision=precision,
                resolved_by="google",
            )

    def _map_nominatim_precision(self, place_type: str, address: Dict[str, str]) -> str:
        """Map Nominatim place type to precision level."""
        if place_type in {"house", "building", "address"}:
            return "address"
        if place_type in {"postcode", "postal_code"}:
            return "postal_code"
        if place_type in {"neighbourhood", "suburb", "quarter"}:
            return "neighborhood"
        if place_type in {"city", "town", "village", "municipality"}:
            return "city"
        if place_type in {"county", "state_district"}:
            return "metro"
        if place_type in {"state", "region", "province"}:
            return "region"

        # Fallback: check address components
        if address.get("postcode"):
            return "postal_code"
        if address.get("city") or address.get("town"):
            return "city"
        if address.get("state"):
            return "region"

        return "city"  # default

    def _map_google_precision(self, types: list) -> str:
        """Map Google place types to precision level."""
        if "street_address" in types or "premise" in types:
            return "address"
        if "postal_code" in types:
            return "postal_code"
        if "neighborhood" in types or "sublocality" in types:
            return "neighborhood"
        if "locality" in types:
            return "city"
        if "administrative_area_level_2" in types:
            return "metro"
        if "administrative_area_level_1" in types:
            return "region"

        return "city"  # default
