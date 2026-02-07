"""
Vendor registry for early-adopter service providers.

Real provider data sourced from charter_providers_offerings_and_checklist.xlsx (2026-02-07).
These are verified early-adopter partners, not mock data.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Vendor:
    name: str
    company: str
    email: str
    phone: Optional[str] = None
    category: str = "private_aviation"
    source: str = "wattdata"
    image_url: Optional[str] = None
    # Rich fields from provider research
    website: Optional[str] = None
    provider_type: Optional[str] = None  # Operator / Broker / Platform / Services
    fleet: Optional[str] = None  # Published fleet / aircraft
    jet_sizes: Optional[str] = None  # Light / Midsize / Heavy etc.
    wifi: Optional[str] = None  # Connectivity details
    starlink: Optional[str] = None  # Starlink availability
    pricing_info: Optional[str] = None  # Pricing model
    availability: Optional[str] = None  # Lead time / availability info
    safety_certs: Optional[str] = None  # ARGUS / Wyvern / IS-BAO / Part 135
    notes: Optional[str] = None  # Caveats and notes
    source_urls: Optional[str] = None  # Public reference URLs
    last_verified: Optional[str] = None  # Date of last verification
    # Searchable text blob (auto-built)
    _search_text: Optional[str] = field(default=None, repr=False)

    def get_search_text(self) -> str:
        """Build a single searchable text blob from all fields."""
        if self._search_text:
            return self._search_text
        parts = [
            self.company, self.name, self.email,
            self.provider_type or "", self.fleet or "",
            self.jet_sizes or "", self.wifi or "",
            self.starlink or "", self.pricing_info or "",
            self.availability or "", self.safety_certs or "",
            self.notes or "", self.website or "",
        ]
        self._search_text = " ".join(p for p in parts if p).lower()
        return self._search_text

    def to_rich_dict(self) -> Dict[str, Any]:
        """Return all fields as a dict for API responses."""
        d = asdict(self)
        d.pop("_search_text", None)
        return d


# =============================================================================
# DUE DILIGENCE CHECKLIST — from checklist sheet
# =============================================================================

@dataclass
class ChecklistItem:
    category: str  # e.g. "Fleet & connectivity"
    item: str  # What to check
    why_it_matters: str
    how_to_verify: str
    must_have: bool  # Y/N from spreadsheet


CHARTER_CHECKLIST: List[ChecklistItem] = [
    # Fleet & connectivity
    ChecklistItem("Fleet & connectivity", "Aircraft type + tail number for your trip", "Confirms the exact aircraft you'll fly on — specs, range, cabin size.", "Written confirmation of tail number + spec sheet.", True),
    ChecklistItem("Fleet & connectivity", "Wi-Fi system type (ATG / Ka-band / Ku-band / Starlink)", "Determines real-world internet speed, coverage, and video-call ability.", "Ask: 'What Wi-Fi system is installed on [tail]?' + coverage map.", True),
    ChecklistItem("Fleet & connectivity", "Wi-Fi speed / latency expectations on your route", "Performance varies by system and geography.", "Speed test results or published specs; ask about video-call capability.", True),
    ChecklistItem("Fleet & connectivity", "Starlink installed? (vs. ordered or 'coming soon')", "Many operators announced Starlink but haven't installed on every tail.", "Ask for install confirmation per tail; STC status.", True),
    ChecklistItem("Fleet & connectivity", "Wi-Fi included in quote or billed separately?", "Surprise fees can add $500–$2,000+ per leg.", "Line item in the quote.", True),
    ChecklistItem("Fleet & connectivity", "Baggage capacity (volume + weight limits)", "Oversized luggage (golf bags, skis) may not fit.", "Aircraft spec sheet; ask for baggage compartment dimensions.", False),
    ChecklistItem("Fleet & connectivity", "Cabin amenities (power outlets, USB, entertainment, refreshments)", "Comfort and productivity for longer flights.", "Cabin amenities list from operator.", False),
    # Safety & compliance
    ChecklistItem("Safety & compliance", "Operating carrier name + FAA Part 135 certificate number", "Confirms who actually flies the aircraft — critical for brokers.", "FAA certificate lookup; written disclosure from broker/operator.", True),
    ChecklistItem("Safety & compliance", "Third-party safety ratings: ARGUS / Wyvern / IS-BAO", "Independent safety oversight signals maturity.", "Rating certificates / links; audit date.", True),
    ChecklistItem("Safety & compliance", "Insurance coverage limits (liability)", "Confirms adequate coverage.", "Certificate of insurance (COI).", True),
    ChecklistItem("Safety & compliance", "Maintenance program & recent inspections", "Aircraft readiness and safety.", "Maintenance status letter; last major inspection date.", True),
    ChecklistItem("Safety & compliance", "International ops capability (permits/handlers/customs)", "If international, paperwork and lead time matter.", "International handling plan; permit lead times.", False),
    ChecklistItem("Safety & compliance", "Drug/alcohol testing & safety management (SMS)", "Operational discipline.", "Policy statement; SMS overview.", False),
    # Quote & pricing
    ChecklistItem("Quote & pricing", "Is quote all-in? (fuel, crew, landing, handling, catering, Wi-Fi, de-ice)", "Avoids surprise charges.", "Line-item quote breakdown.", True),
    ChecklistItem("Quote & pricing", "Hourly rate vs trip quote; minimum daily hours", "Changes total cost; especially for multi-day trips.", "Written rate card or minimums in quote.", True),
    ChecklistItem("Quote & pricing", "Repositioning / ferry legs included?", "Can be a big cost driver.", "Positioning explanation + included/excluded legs.", True),
    ChecklistItem("Quote & pricing", "Peak-day / holiday surcharges", "Common during high demand.", "Surcharge policy.", False),
    ChecklistItem("Quote & pricing", "Overnight expenses (crew hotels/per diem) included?", "Important on multi-day itineraries.", "Overnight policy and estimates.", True),
    ChecklistItem("Quote & pricing", "De-icing & winter ops policy (if relevant)", "Can be unpredictable and expensive.", "De-ice billing policy.", False),
    ChecklistItem("Quote & pricing", "International fees (permits, navigation, overflight, customs)", "High variability; needs clarity.", "International fee schedule/estimate.", False),
    ChecklistItem("Quote & pricing", "Taxes: US Federal Excise Tax (FET) applicability", "Charter often has tax; needs to be in the quote.", "Tax line items in quote.", True),
    ChecklistItem("Quote & pricing", "Payment method & card fee policy", "Affects total cost; some add card fees.", "Payment terms and fee schedule.", True),
    ChecklistItem("Quote & pricing", "Deposit required and due date", "Secures aircraft; affects flexibility.", "Deposit terms.", True),
    ChecklistItem("Quote & pricing", "Cancellation policy (timeline-based penalties)", "Critical risk item.", "Cancellation schedule in writing.", True),
    ChecklistItem("Quote & pricing", "Change fees (time changes, airport changes)", "Itinerary changes happen; know costs upfront.", "Change policy.", True),
    ChecklistItem("Quote & pricing", "Refundability for weather/ATC delays", "Defines what you pay when ops disruptions occur.", "Irregular ops policy.", True),
    ChecklistItem("Quote & pricing", "Membership/program options (if offered): fees, lock-in, blackout dates", "Programs can be valuable but vary widely.", "Program contract + T&Cs.", False),
    # Availability & ops
    ChecklistItem("Availability & ops", "How long is the quote valid? (hold time)", "Inventory is dynamic; prevents surprises.", "Quote expiration time.", True),
    ChecklistItem("Availability & ops", "Lead time for booking confirmation", "Ensures you can commit and get tail assigned.", "Confirmation timeline in writing.", True),
    ChecklistItem("Availability & ops", "Typical cancellation due to maintenance: substitution policy", "If aircraft goes AOG, you want clear replacement rules.", "Substitution / AOG policy.", True),
    ChecklistItem("Availability & ops", "Crew duty limitations that might affect schedule", "Can force timing constraints or tech stops.", "Duty time policy summary.", False),
    ChecklistItem("Availability & ops", "Tech stops required? (fuel stops)", "Adds time; affects passenger experience.", "Routing plan with anticipated stops.", False),
    ChecklistItem("Availability & ops", "Runway performance limits at your airports", "Some aircraft can't operate from short runways or high/hot conditions.", "Performance confirmation for each airport.", True),
    ChecklistItem("Availability & ops", "Ground handling / FBO details", "Sets meet-and-greet experience and fees.", "FBO names + fees included.", False),
    # Service
    ChecklistItem("Service", "Catering included? options + cutoff times", "Quality and logistics; cutoff times can be strict.", "Catering menu; cutoff policy.", False),
    ChecklistItem("Service", "Ground transportation coordination available?", "Convenience and cost.", "Ground transport options and pricing.", False),
    ChecklistItem("Service", "Cabin attendant provided? (for heavy/ULR)", "Service level and safety on longer legs.", "Crew complement details.", False),
    ChecklistItem("Service", "Accessibility of client support 24/7", "Critical when plans change.", "Support channel + escalation path.", True),
    # Documents
    ChecklistItem("Documents", "Charter agreement (sample) before paying", "Lets you review legal terms early.", "Sample contract / terms.", True),
    ChecklistItem("Documents", "Operator Certificate (Part 135) and insurance COI", "Verifies legitimacy and coverage.", "Certificates/COI.", True),
    ChecklistItem("Documents", "Aircraft spec sheet + amenities list for quoted tail", "Avoids mismatch on expectations (Wi-Fi, seating).", "Spec sheet; photos; Wi-Fi system.", True),
    ChecklistItem("Documents", "Passenger manifest & ID requirements", "International and security compliance.", "Manifest template.", True),
    ChecklistItem("Documents", "Privacy policy for passenger data", "Protects sensitive data.", "Privacy policy link/statement.", False),
    # Trip basics
    ChecklistItem("Trip basics", "Exact passenger names needed by what deadline?", "Some operators require Secure Flight data before departure.", "Passenger data submission policy.", True),
    ChecklistItem("Trip basics", "Car seats for children: allowed types and installation support?", "Safety + compliance; varies by aircraft.", "Car seat policy.", False),
    # Aircraft & cabin
    ChecklistItem("Aircraft & cabin", "Cabin layout (club seating vs conference) preference", "Affects comfort and ability to work/dine.", "Seat map / cabin photos.", False),
    ChecklistItem("Aircraft & cabin", "Lavatory type: full flush vs belted potty; hot water availability", "Comfort and hygiene.", "Lavatory details.", False),
]


# =============================================================================
# EMAIL TEMPLATE — for automated/manual vendor outreach
# =============================================================================

CHARTER_EMAIL_TEMPLATE = {
    "subject": "Charter quote request — [Route] — [Dates] — [Passengers] — Wi-Fi/Starlink",
    "body": """Hi [Name/Team],

I'm requesting a charter quote and availability for the itinerary below. Please respond with (1) pricing breakdown, (2) tail number + operator details, and (3) connectivity details (Wi-Fi/Starlink) for each aircraft option.

ITINERARY
• Date(s): [YYYY-MM-DD] (flexible ± [X] hours)
• Route: [Departure] → [Arrival] (alternate airports OK: [list])
• Pax: [#] adults, [#] minors (ages: [..])
• Luggage: [..] standard + [..] oversize
• Pets: [None / details]

AIRCRAFT
Preferred aircraft class: [Light/Midsize/Super-midsize/Heavy]
Minimum requirements: [lav type, baggage, range, etc.]

CONNECTIVITY
Connectivity requirement: [Must-have Wi-Fi domestic/international].
If available, please specify:
• Wi-Fi system type (ATG/Ka/Ku/Starlink)
• Expected speed/latency and whether video calls work
• Coverage on this route
• Any Wi-Fi fees or usage limits

SAFETY
Please include:
• Operating carrier name (Part 135 certificate holder) + certificate number
• Tail number for each option
• Safety ratings (ARGUS/Wyvern/IS-BAO) if available
• Insurance coverage limits (COI upon booking)

QUOTE DETAILS
Please itemize:
• Trip price (all-in) including taxes (FET if applicable)
• Repositioning/ferry legs and minimums
• Landing/handling/FBO fees
• Crew overnight/per diem if multi-day
• Catering and Wi-Fi fees (if any)
• Cancellation/change policy
• Quote validity window (how long you can hold the aircraft)

Thank you — happy to jump on a quick call if needed.

Best,
[Your name]
[Phone]""",
}


# =============================================================================
# EARLY-ADOPTER PROVIDERS — from charter_providers_offerings_and_checklist.xlsx
# =============================================================================

VENDORS: dict[str, List[Vendor]] = {
    "private_aviation": [
        Vendor(
            name="Charter Team",
            company="JetRight",
            email="charter@jetrightnashville.com",
            category="private_aviation",
            image_url="https://www.google.com/s2/favicons?domain=jetrightnashville.com&sz=128",
            website="https://www.jetrightnashville.com",
            provider_type="Operator / Charter",
            fleet="Learjet 45XR; Learjet 75; Challenger 3500 (fleet page also lists specific tails).",
            jet_sizes="Light / Super-midsize",
            wifi="CL3500: 4G ATG; Ka-band availability noted. Learjet 45XR page lists Wi-Fi + satellite phone + iPad docking.",
            starlink="Not found publicly on JetRight pages reviewed.",
            pricing_info="Not published (quote-based).",
            availability="Not published; typical on-demand charter (as-available).",
            safety_certs="Not found on reviewed pages.",
            notes="Good published spec sheet for CL3500; ask if Ka-band is installed on your tail + speed/coverage.",
            source_urls="https://www.jetrightnashville.com/charter; https://www.jetrightnashville.com/fleet; https://www.jetrightnashville.com/hubfs/CL3500_071823.pdf; https://www.jetrightnashville.com/learjet-45xr",
            last_verified="2026-02-07",
        ),
        Vendor(
            name="Adnan",
            company="24/7 Jet",
            email="adnan@247jet.com",
            category="private_aviation",
            image_url="https://www.247jet.com/img/logo.png",
            website="https://www.247jet.com",
            provider_type="Operator / Charter",
            fleet="States fleet includes Bombardier, Gulfstream, Embraer; publishes aircraft pages (e.g., Gulfstream GIV, Lineage 1000E).",
            jet_sizes="Midsize to Heavy (varies)",
            wifi="Not clearly stated on pages reviewed.",
            starlink="Not found publicly on pages reviewed.",
            pricing_info="Not published (quote-based).",
            availability="Not published.",
            safety_certs="Claims ARGUS Gold and Wyvern Registered (fleet page).",
            notes="Verify which tails are Part 135 on your dates; ask for Wi-Fi details per tail.",
            source_urls="https://www.247jet.com/fleet.php; https://247jet.com/gulfstream_GIV.php",
            last_verified="2026-02-07",
        ),
        Vendor(
            name="Charter Desk",
            company="WCAS (West Coast Aviation Services)",
            email="charter@wcas.aero",
            category="private_aviation",
            image_url="https://www.google.com/s2/favicons?domain=wcas.aero&sz=128",
            website="https://www.wcas.aero",
            provider_type="Operator / Charter + Management",
            fleet="Part 135 flights on Challenger 604, Falcon 2000EX, Global Express, and G550 (operated by West Coast Worldwide).",
            jet_sizes="Heavy / Ultra-long-range (varies)",
            wifi="Not clearly stated on pages reviewed.",
            starlink="Not found publicly on pages reviewed.",
            pricing_info="Not published (quote-based).",
            availability="Not published.",
            safety_certs="Fleet page lists operator certificate: West Coast Worldwide, FAA Air Carrier Certificate #DCUA716B.",
            notes="Ask if specific aircraft are based near your departure; confirm Wi-Fi type and international coverage.",
            source_urls="https://www.wcas.aero/fleet",
            last_verified="2026-02-07",
        ),
        Vendor(
            name="C Parker",
            company="Jet Access",
            email="cparker@flyja.com",
            category="private_aviation",
            image_url="https://www.google.com/s2/favicons?domain=flyja.com&sz=128",
            website="https://www.flyjetaccess.com",
            provider_type="Operator / Charter",
            fleet="Fleet list includes Challenger 604; Falcon 2000; Citation Latitude; Citation X; Hawker (per charter fleet page).",
            jet_sizes="Midsize / Super-midsize / Heavy (varies)",
            wifi="Fleet/aircraft pages include Wi-Fi on Falcon 2000 and Citation Latitude pages (confirm per tail).",
            starlink="Not found publicly on pages reviewed.",
            pricing_info="Not published (quote-based).",
            availability="Empty legs and availability change rapidly; contact for current options.",
            safety_certs="FAR Part 135 Air Carrier (Certificate #1JAA142N); ARG/US Platinum rated; WYVERN registered (fleet page).",
            notes="Ask for home-base positioning costs and peak-day minimums.",
            source_urls="https://www.flyjetaccess.com/charter/charter-fleet/; https://www.flyjetaccess.com/fleet/falcon2000/; https://devsite.flyjetaccess.com/fleet/citation-latitude/",
            last_verified="2026-02-07",
        ),
        Vendor(
            name="Michael Morrissey",
            company="flyExclusive",
            email="mmorrissey@flyexclusive.com",
            category="private_aviation",
            image_url="https://www.google.com/s2/favicons?domain=flyexclusive.com&sz=128",
            website="https://flyexclusive.com",
            provider_type="Operator / Charter",
            fleet="Citation CJ3/CJ3+; Citation Excel/XLS; Citation Sovereign; Citation X; Challenger 350 (fleet page).",
            jet_sizes="Light / Midsize / Super-midsize",
            wifi="Challenger 350 page says WiFi enabled (and other aircraft may vary).",
            starlink="Authorized Starlink aviation dealer; announced fleet installations (tail-specific status varies).",
            pricing_info="Not published (quote-based).",
            availability="Not published.",
            safety_certs="Not found on reviewed pages.",
            notes="Ask if your specific tail has Starlink already installed + latency/speeds + coverage.",
            source_urls="https://flyexclusive.com/who-we-are/our-fleet; https://flyexclusive.com/challenger-350; https://ir.flyexclusive.com/news-events/press-releases/detail/162/flyexclusive-named-authorized-starlink-aviation-dealer",
            last_verified="2026-02-07",
        ),
        Vendor(
            name="Michael Hall",
            company="FXAIR",
            email="michael.hall@fxair.com",
            category="private_aviation",
            image_url="https://www.google.com/s2/favicons?domain=fxair.com&sz=128",
            website="https://www.fxair.com",
            provider_type="Operator / Charter + Membership programs",
            fleet="FXSelect lineup includes Phenom 300; Challenger 300; Global Express.",
            jet_sizes="Light / Super-midsize / Heavy",
            wifi="Aviator+ positioning includes complimentary domestic Wi-Fi on flights served by select operators.",
            starlink="Not found publicly on pages reviewed.",
            pricing_info="Mentions fixed hourly rates in Aviator+ positioning but rates not published (quote / program).",
            availability="Aviator+ mentions aircraft availability with as little as 120 hours' notice.",
            safety_certs="Not found on reviewed pages.",
            notes="Ask if Wi-Fi is included or billed; clarify repositioning + daily minimums for multi-leg itineraries.",
            source_urls="https://www.fxair.com/en-us/fxselect; https://www.fxair.com/en-us/news/fxair-experiences-unprecedented-growth-over-last-three-years",
            last_verified="2026-02-07",
        ),
        Vendor(
            name="J Kessler",
            company="V2 Jets",
            email="jkessler@v2jets.com",
            category="private_aviation",
            image_url="https://www.google.com/s2/favicons?domain=v2jets.com&sz=128",
            website="https://www.v2jets.com",
            provider_type="Broker",
            fleet="Publishes aircraft categories/types (not a single operated fleet). Sources aircraft from operators.",
            jet_sizes="All classes depending on sourced aircraft",
            wifi="Varies by operator/tail (must request for each option).",
            starlink="Varies by operator/tail (must request).",
            pricing_info="Varies by sourced operator/tail; broker quote.",
            availability="Varies by sourced operator/tail.",
            safety_certs="Broker — ask which operator is flying, Part 135 certificate, and safety ratings.",
            notes="Broker (not direct air carrier). Always confirm operating carrier + Part 135 certificate holder + tail number.",
            source_urls="https://www.v2jets.com/aircraft-types",
            last_verified="2026-02-07",
        ),
        Vendor(
            name="Info",
            company="Airble",
            email="info@airble.com",
            category="private_aviation",
            image_url="https://www.google.com/s2/favicons?domain=airble.com&sz=128",
            website="https://airble.com",
            provider_type="Platform / Marketplace",
            fleet="Provides booking widget and marketplace tools; operators list their fleets and set pricing.",
            jet_sizes="All classes (platform-dependent)",
            wifi="Varies by operator/tail; platform may show amenities per listing.",
            starlink="Varies by operator/tail.",
            pricing_info="Marketplace: pricing shown up front for empty legs; operators/listings vary.",
            availability="Depends on live listings/empty-legs and operator inventory.",
            safety_certs="Depends on operator (verify Part 135 and safety for each listing).",
            notes="Use as discovery; still vet operator/tail and contract terms.",
            source_urls="https://airble.com/empty-leg-flights; https://airble.com/solutions/booking-widget",
            last_verified="2026-02-07",
        ),
        Vendor(
            name="Info",
            company="Business Jet Advisors",
            email="info@businessjetadvisors.com",
            category="private_aviation",
            image_url="https://businessjetadvisors.com/wp-content/uploads/2025/08/Untitled-design.png",
            website="https://bizjetadvisors.com",
            provider_type="Services / Part 135 operational support (not a charter fleet)",
            fleet="Operational support services (DO/SMS/maintenance/safety) rather than selling charter directly.",
            jet_sizes="N/A",
            wifi="N/A",
            starlink="N/A",
            pricing_info="N/A (service business).",
            availability="N/A",
            safety_certs="N/A",
            notes="Provides Part 135 operational support — not a charter provider. Useful as a safety/compliance resource.",
            source_urls="https://bizjetadvisors.com/",
            last_verified="2026-02-07",
        ),
        Vendor(
            name="Charter Team",
            company="Peak Aviation Solutions (FlyPeak)",
            email="charter@peakaviationsolutions.com",
            category="private_aviation",
            image_url="https://www.google.com/s2/favicons?domain=flypeak.com&sz=128",
            website="https://flypeak.com",
            provider_type="Broker",
            fleet="Positions as charter broker; sources aircraft from operator network.",
            jet_sizes="All classes depending on sourced aircraft",
            wifi="Varies by operator/tail.",
            starlink="Varies by operator/tail.",
            pricing_info="Varies by sourced operator/tail; broker quote.",
            availability="Varies by sourced operator/tail.",
            safety_certs="Broker — verify operator/Part 135 certificate and safety ratings.",
            notes="Ask for who the operating carrier is + tail number + Wi-Fi + cancellation terms.",
            source_urls="https://flypeak.com/",
            last_verified="2026-02-07",
        ),
        Vendor(
            name="Fly Team",
            company="V2 Jets (Alt Contact)",
            email="fly@v2jets.com",
            category="private_aviation",
            image_url="https://www.google.com/s2/favicons?domain=v2jets.com&sz=128",
            website="https://www.v2jets.com",
            provider_type="Broker",
            fleet="Same as V2 Jets — sources aircraft from operators.",
            jet_sizes="All classes depending on sourced aircraft",
            wifi="Varies by operator/tail.",
            starlink="Varies by operator/tail.",
            pricing_info="Broker quote.",
            availability="Varies by sourced operator/tail.",
            safety_certs="Broker — confirm operating carrier.",
            notes="Alternative contact for V2 Jets.",
            source_urls="https://www.v2jets.com/aircraft-types",
            last_verified="2026-02-07",
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
