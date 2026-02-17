import asyncio
import os
import json
import random
from typing import List, Dict, Any
from datetime import datetime

# Import database and models
import sys
# Add apps/backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import engine
from models.bids import Vendor
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

# --- CONFIGURATION ---
TOTAL_VENDORS = 1000

TIERS = {
    "commodity": {
        "weight": 0.3,
        "categories": ["Books", "Crafts", "Artisans", "Religious Shops", "Gifts"],
        "price_range": (5, 500)
    },
    "considered": {
        "weight": 0.4,
        "categories": ["Plumbers", "Landscapers", "Auto Repair", "Electricians", "HVAC"],
        "price_range": (100, 5000)
    },
    "luxury": {
        "weight": 0.2,
        "categories": ["Charter Jets", "Personal Trainers", "Yacht Rentals", "Caterers", "Fine Jewelry"],
        "price_range": (5000, 50000)
    },
    "high_value": {
        "weight": 0.07,
        "categories": ["Diamonds", "Super Cars", "Yachts", "Private Jets", "Art Dealers"],
        "price_range": (50000, 1000000)
    },
    "ultra_high_end": {
        "weight": 0.03,
        "categories": ["Gulf Stream", "Supersonic Jets", "Super Yachts", "Office Towers", "Business Acquisitions"],
        "price_range": (1000000, 500000000)
    }
}

DOMAINS = ["com", "net", "io", "org", "co", "biz", "luxury", "shop", "studio"]

# --- GENERATION LOGIC ---

def generate_vendor(tier_name: str) -> Dict[str, Any]:
    tier_info = TIERS[tier_name]
    category = random.choice(tier_info["categories"])
    
    # Generate unique name
    adjectives = ["Elite", "Global", "Artisan", "Bespoke", "Premier", "Direct", "Heritage", "Zenith", "Apex", "Custom"]
    nouns = ["Group", "Solutions", "Studios", "Works", "Collective", "Partners", "Ventures", "Boutique", "Exchange"]
    prefix = random.choice(adjectives)
    suffix = random.choice(nouns)
    name = f"{prefix} {category} {suffix} {random.randint(100, 999)}"
    
    clean_name = "".join(c for c in name if c.isalnum()).lower()
    domain = f"{clean_name}.{random.choice(DOMAINS)}"
    
    p_min, p_max = tier_info["price_range"]
    
    return {
        "name": name,
        "email": f"concierge@{domain}",
        "domain": domain,
        "website": f"https://{domain}",
        "phone": f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}",
        "category": category,
        "description": f"Top-tier provider of {category} in the {tier_name} market.",
        "tier_affinity": tier_name,
        "price_range_min": p_min,
        "price_range_max": p_max,
        "is_verified": True,
        "status": "active",
        "reputation_score": round(random.uniform(4.0, 5.0), 1),
        "profile_text": f"{name} is a premier provider specializing in {category}. We serve clients looking for excellence in the {tier_name} space.",
        "image_url": f"https://images.unsplash.com/photo-{random.randint(1000000, 2000000)}?auto=format&fit=crop&q=80&w=200&h=200"
    }

async def populate():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print(f"Starting population of {TOTAL_VENDORS} vendors...")
    
    vendors_created = 0
    async with async_session() as session:
        for tier_name, info in TIERS.items():
            count = int(TOTAL_VENDORS * info["weight"])
            print(f"Generating {count} vendors for {tier_name}...")
            
            for _ in range(count):
                v_data = generate_vendor(tier_name)
                vendor = Vendor(**v_data)
                session.add(vendor)
                vendors_created += 1
                
                if vendors_created % 100 == 0:
                    await session.commit()
                    print(f"Committed {vendors_created} vendors...")
        
        await session.commit()
        print(f"Final commit complete. Total vendors created: {vendors_created}")

if __name__ == "__main__":
    asyncio.run(populate())
