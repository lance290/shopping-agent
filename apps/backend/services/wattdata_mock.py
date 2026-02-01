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


# Hardcoded vendors for demo - use demo+* email aliases
MOCK_VENDORS: dict[str, List[Vendor]] = {
    "private_aviation": [
        Vendor(
            name="Sales Team",
            company="NetJets",
            email="demo+netjets@buyanything.ai",
            phone="555-0101",
        ),
        Vendor(
            name="Charter Desk",
            company="Wheels Up",
            email="demo+wheelsup@buyanything.ai",
            phone="555-0102",
        ),
        Vendor(
            name="Booking Team",
            company="XO",
            email="demo+xo@buyanything.ai",
            phone="555-0103",
        ),
        Vendor(
            name="Client Services",
            company="VistaJet",
            email="demo+vistajet@buyanything.ai",
            phone="555-0104",
        ),
        Vendor(
            name="Charter Sales",
            company="Flexjet",
            email="demo+flexjet@buyanything.ai",
            phone="555-0105",
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
    
    if any(term in lower for term in ["jet", "flight", "charter", "aviation", "fly"]):
        return ["NetJets", "Wheels Up", "XO", "VistaJet", "Flexjet"]
    
    if any(term in lower for term in ["roof", "shingle", "gutter"]):
        return ["ABC Roofing", "Top Notch Roofing", "Superior Roofing Co"]
    
    if any(term in lower for term in ["hvac", "air condition", "heating", "furnace", "ac "]):
        return ["Cool Air HVAC", "Comfort Zone Heating & Cooling"]
    
    # Default fallback
    return []
