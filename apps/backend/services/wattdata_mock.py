"""
Mock WattData service for private jet demo.
Returns hardcoded vendors until real WattData MCP is ready.
"""
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Vendor:
    name: str
    company: str
    email: str
    phone: Optional[str] = None
    category: str = "private_aviation"
    source: str = "wattdata"
    image_url: Optional[str] = None


# Real charter providers for JetBid demo
MOCK_VENDORS: dict[str, List[Vendor]] = {
    "private_aviation": [
        Vendor(
            name="Charter Team",
            company="JetRight Nashville",
            email="charter@jetrightnashville.com",
            image_url="https://www.google.com/s2/favicons?domain=jetrightnashville.com&sz=128",
        ),
        Vendor(
            name="Adnan",
            company="247 Jet",
            email="adnan@247jet.com",
            image_url="https://www.247jet.com/img/logo.png",
        ),
        Vendor(
            name="Charter Desk",
            company="WCAS Aviation",
            email="charter@wcas.aero",
            image_url="https://www.google.com/s2/favicons?domain=wcas.aero&sz=128",
        ),
        Vendor(
            name="Info",
            company="Business Jet Advisors",
            email="info@businessjetadvisors.com",
            image_url="https://businessjetadvisors.com/wp-content/uploads/2025/08/Untitled-design.png",
        ),
        Vendor(
            name="Michael Morrissey",
            company="flyExclusive",
            email="mmorrissey@flyexclusive.com",
            image_url="https://www.google.com/s2/favicons?domain=flyexclusive.com&sz=128",
        ),
        Vendor(
            name="Info",
            company="Airble",
            email="info@airble.com",
            image_url="https://www.google.com/s2/favicons?domain=airble.com&sz=128",
        ),
        Vendor(
            name="J Kessler",
            company="V2 Jets",
            email="jkessler@v2jets.com",
            image_url="https://www.google.com/s2/favicons?domain=v2jets.com&sz=128",
        ),
        Vendor(
            name="Michael Hall",
            company="FX Air",
            email="michael.hall@fxair.com",
            image_url="https://www.google.com/s2/favicons?domain=fxair.com&sz=128",
        ),
        Vendor(
            name="C Parker",
            company="Jet Access",
            email="cparker@flyja.com",
            image_url="https://www.google.com/s2/favicons?domain=flyja.com&sz=128",
        ),
        Vendor(
            name="Charter Team",
            company="Peak Aviation Solutions",
            email="charter@peakaviationsolutions.com",
            image_url="https://www.google.com/s2/favicons?domain=flypeak.com&sz=128",
        ),
        Vendor(
            name="Fly Team",
            company="V2 Jets (Alt)",
            email="fly@v2jets.com",
            image_url="https://www.google.com/s2/favicons?domain=v2jets.com&sz=128",
        ),
    ],
    "roofing": [
        Vendor(
            name="Estimates",
            company="ABC Roofing",
            email="demo+abcroofing@buyanything.ai",
            phone="555-0201",
            category="roofing",
        ),
        Vendor(
            name="Sales",
            company="Top Notch Roofing",
            email="demo+topnotch@buyanything.ai",
            phone="555-0202",
            category="roofing",
        ),
        Vendor(
            name="Quotes",
            company="Superior Roofing Co",
            email="demo+superior@buyanything.ai",
            phone="555-0203",
            category="roofing",
        ),
    ],
    "hvac": [
        Vendor(
            name="Service Dept",
            company="Cool Air HVAC",
            email="demo+coolair@buyanything.ai",
            phone="555-0301",
            category="hvac",
        ),
        Vendor(
            name="Estimates",
            company="Comfort Zone Heating & Cooling",
            email="demo+comfortzone@buyanything.ai",
            phone="555-0302",
            category="hvac",
        ),
    ],
}

# Category aliases for LLM suggestions
CATEGORY_ALIASES = {
    "private jet": "private_aviation",
    "private jets": "private_aviation",
    "jet charter": "private_aviation",
    "charter flight": "private_aviation",
    "private flight": "private_aviation",
    "private aviation": "private_aviation",
    "roof": "roofing",
    "roofing": "roofing",
    "new roof": "roofing",
    "roof repair": "roofing",
    "hvac": "hvac",
    "air conditioning": "hvac",
    "heating": "hvac",
    "furnace": "hvac",
}


def normalize_category(category: str) -> str:
    """Normalize category name to match our mock data."""
    lower = category.lower().strip()
    return CATEGORY_ALIASES.get(lower, lower)


def get_vendors(category: str, limit: int = 5) -> List[Vendor]:
    """
    Get vendors for a category.
    In production, this would query WattData MCP.
    """
    normalized = normalize_category(category)
    vendors = MOCK_VENDORS.get(normalized, [])
    return vendors[:limit]


def get_vendor_suggestions(description: str) -> List[str]:
    """
    Suggest vendor categories based on description.
    In production, LLM would do this.
    """
    lower = description.lower()
    
    if any(term in lower for term in ["jet", "flight", "charter", "aviation", "fly", "plane"]):
        vendors = MOCK_VENDORS.get("private_aviation", [])
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


def get_vendors_as_results(category: str) -> List[dict]:
    """
    Get vendors formatted as search result tiles.
    Returns list of dicts that match the Bid/offer format.
    """
    vendors = get_vendors(category, limit=10)
    results = []
    for i, vendor in enumerate(vendors):
        results.append({
            "title": vendor.company,
            "description": f"Charter service provider - {vendor.name}",
            "price": None,  # Service providers don't have fixed prices
            "url": f"mailto:{vendor.email}",
            "image_url": vendor.image_url,
            "source": "JetBid",
            "is_service_provider": True,
            "vendor_email": vendor.email,
            "vendor_name": vendor.name,
            "vendor_company": vendor.company,
        })
    return results
