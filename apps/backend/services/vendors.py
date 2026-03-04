"""
Vendor registry for early-adopter service providers.

Real provider data sourced from charter_providers_offerings_and_checklist.xlsx (2026-02-07).
These are verified early-adopter partners, not mock data.

Models in vendors_models.py, static data in vendors_data.py.
"""
from typing import List, Optional, Dict, Any

# Re-export models for backward compatibility
from services.vendors_models import Vendor, ChecklistItem  # noqa: F401

# Import static data
from services.vendors_data import (  # noqa: F401
    VENDORS,
    CATEGORY_ALIASES,
    CHARTER_CHECKLIST,
    CHARTER_EMAIL_TEMPLATE,
)


def normalize_category(category: str) -> str:
    """Normalize category name to match our mock data."""
    lower = category.lower().strip()
    return CATEGORY_ALIASES.get(lower, lower)


def get_vendors(category: str, limit: int = 5) -> List[Vendor]:
    """
    Get vendors for a category.
    Returns registered early-adopter providers.
    """
    normalized = normalize_category(category)
    vendors = VENDORS.get(normalized, [])
    return vendors[:limit]


def get_vendor_suggestions(description: str) -> List[str]:
    """
    Suggest vendor categories based on description.
    In production, LLM would do this.
    """
    lower = description.lower()
    
    if any(term in lower for term in ["jet", "flight", "charter", "aviation", "fly", "plane"]):
        vendors = VENDORS.get("private_aviation", [])
        return [v.company for v in vendors]
    
    if any(term in lower for term in ["roof", "shingle", "gutter"]):
        return ["ABC Roofing", "Top Notch Roofing", "Superior Roofing Co"]
    
    if any(term in lower for term in ["hvac", "air condition", "heating", "furnace", "ac "]):
        return ["Cool Air HVAC", "Comfort Zone Heating & Cooling"]
    
    # Default fallback
    return []


def is_service_category(query: str) -> bool:
    """Check if a search query is for a service (vs a product)."""
    lower = query.lower()
    service_terms = [
        "jet", "charter", "flight", "aviation", "fly", "plane",
        "roof", "roofing", "hvac", "heating", "cooling", "plumb",
        "electric", "landscap", "clean", "repair", "service"
    ]
    return any(term in lower for term in service_terms)


def _build_description(vendor: Vendor) -> str:
    """Build a rich description from vendor fields."""
    parts = []
    if vendor.provider_type:
        parts.append(vendor.provider_type)
    if vendor.jet_sizes and vendor.jet_sizes != "N/A":
        parts.append(f"Aircraft: {vendor.jet_sizes}")
    if vendor.safety_certs and vendor.safety_certs != "N/A" and "Not found" not in vendor.safety_certs:
        parts.append(f"Safety: {vendor.safety_certs}")
    if vendor.wifi and vendor.wifi != "N/A" and "Not clearly" not in vendor.wifi:
        parts.append(f"Wi-Fi: {vendor.wifi}")
    if vendor.starlink and "Not found" not in vendor.starlink and vendor.starlink != "N/A":
        parts.append(f"Starlink: {vendor.starlink}")
    if not parts:
        parts.append(f"Charter service provider — {vendor.name}")
    return " | ".join(parts)


def get_vendors_as_results(category: str) -> List[dict]:
    """
    Get vendors formatted as search result tiles.
    Returns list of dicts that match the Bid/offer format.
    Now includes rich provider data for display.
    """
    vendors = get_vendors(category, limit=15)
    results = []
    for vendor in vendors:
        result = {
            "title": vendor.company,
            "description": _build_description(vendor),
            "price": None,  # Service providers don't have fixed prices
            "url": vendor.website or f"mailto:{vendor.email}",
            "image_url": vendor.image_url,
            "source": "JetBid",
            "is_service_provider": True,
            "vendor_email": vendor.email,
            "vendor_name": vendor.name,
            "vendor_company": vendor.company,
            # Rich fields for detailed view
            "provider_type": vendor.provider_type,
            "fleet": vendor.fleet,
            "jet_sizes": vendor.jet_sizes,
            "wifi": vendor.wifi,
            "starlink": vendor.starlink,
            "pricing_info": vendor.pricing_info,
            "availability": vendor.availability,
            "safety_certs": vendor.safety_certs,
            "notes": vendor.notes,
            "website": vendor.website,
            "source_urls": vendor.source_urls,
            "last_verified": vendor.last_verified,
        }
        results.append(result)
    return results


# =============================================================================
# FULL-TEXT SEARCH — search across ALL vendor fields
# =============================================================================

def search_vendors(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Full-text search across all vendor data.
    Searches company name, fleet, wifi, safety, notes, etc.
    
    Returns ranked results with match score.
    """
    terms = [t.strip().lower() for t in query.lower().split() if t.strip()]
    if not terms:
        # No query — return all vendors for category (or all)
        if category:
            return get_vendors_as_results(normalize_category(category))
        all_results = []
        for cat in VENDORS:
            all_results.extend(get_vendors_as_results(cat))
        return all_results[:limit]

    results: List[tuple] = []  # (score, vendor, category)
    
    # Determine which categories to search
    if category:
        cats = [normalize_category(category)]
    else:
        cats = list(VENDORS.keys())
    
    for cat in cats:
        for vendor in VENDORS.get(cat, []):
            text = vendor.get_search_text()
            score = 0
            for term in terms:
                count = text.count(term)
                if count > 0:
                    score += count
                    # Bonus for company name match
                    if term in (vendor.company or "").lower():
                        score += 3
                    # Bonus for fleet match
                    if vendor.fleet and term in vendor.fleet.lower():
                        score += 2
                    # Bonus for safety match
                    if vendor.safety_certs and term in vendor.safety_certs.lower():
                        score += 2
            
            if score > 0:
                results.append((score, vendor, cat))
    
    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)
    
    # Format as rich results
    output = []
    for score, vendor, cat in results[:limit]:
        result = {
            "title": vendor.company,
            "description": _build_description(vendor),
            "price": None,
            "url": vendor.website or f"mailto:{vendor.email}",
            "image_url": vendor.image_url,
            "source": "JetBid",
            "is_service_provider": True,
            "vendor_email": vendor.email,
            "vendor_name": vendor.name,
            "vendor_company": vendor.company,
            "category": cat,
            "match_score": score,
            "provider_type": vendor.provider_type,
            "fleet": vendor.fleet,
            "jet_sizes": vendor.jet_sizes,
            "wifi": vendor.wifi,
            "starlink": vendor.starlink,
            "pricing_info": vendor.pricing_info,
            "availability": vendor.availability,
            "safety_certs": vendor.safety_certs,
            "notes": vendor.notes,
            "website": vendor.website,
            "source_urls": vendor.source_urls,
            "last_verified": vendor.last_verified,
        }
        output.append(result)
    
    return output


def search_checklist(
    query: str,
    must_have_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Search the due-diligence checklist.
    Returns matching checklist items.
    """
    terms = [t.strip().lower() for t in query.lower().split() if t.strip()]
    results = []
    
    for item in CHARTER_CHECKLIST:
        if must_have_only and not item.must_have:
            continue
        
        if not terms:
            results.append({
                "category": item.category,
                "item": item.item,
                "why_it_matters": item.why_it_matters,
                "how_to_verify": item.how_to_verify,
                "must_have": item.must_have,
            })
            continue
        
        text = f"{item.category} {item.item} {item.why_it_matters} {item.how_to_verify}".lower()
        if any(term in text for term in terms):
            results.append({
                "category": item.category,
                "item": item.item,
                "why_it_matters": item.why_it_matters,
                "how_to_verify": item.how_to_verify,
                "must_have": item.must_have,
            })
    
    return results


def get_checklist_summary() -> Dict[str, Any]:
    """Get checklist organized by category with counts."""
    categories: Dict[str, Dict[str, Any]] = {}
    for item in CHARTER_CHECKLIST:
        if item.category not in categories:
            categories[item.category] = {"items": [], "must_have_count": 0, "total": 0}
        categories[item.category]["items"].append({
            "item": item.item,
            "must_have": item.must_have,
        })
        categories[item.category]["total"] += 1
        if item.must_have:
            categories[item.category]["must_have_count"] += 1
    
    total_must_have = sum(c["must_have_count"] for c in categories.values())
    total_items = sum(c["total"] for c in categories.values())
    
    return {
        "total_items": total_items,
        "total_must_have": total_must_have,
        "categories": categories,
    }


def get_email_template() -> Dict[str, str]:
    """Return the RFP email template for charter quotes."""
    return CHARTER_EMAIL_TEMPLATE


def get_vendor_detail(company_name: str) -> Optional[Dict[str, Any]]:
    """Get full detail for a specific vendor by company name."""
    lower = company_name.lower()
    for cat_vendors in VENDORS.values():
        for vendor in cat_vendors:
            if lower in vendor.company.lower():
                return vendor.to_rich_dict()
    return None
