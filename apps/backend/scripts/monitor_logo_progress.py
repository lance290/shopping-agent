#!/usr/bin/env python3
"""
Monitor Logo Scraping Progress

This script monitors the progress of the logo scraping process.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_session
from models import Vendor
from sqlmodel import select

async def monitor_progress():
    """Monitor logo scraping progress."""
    
    async for session in get_session():
        # Total vendors
        total_stmt = select(Vendor)
        result = await session.exec(total_stmt)
        total_vendors = len(result.all())
        
        # Vendors with websites
        website_stmt = select(Vendor).where(Vendor.website.isnot(None))
        result = await session.exec(website_stmt)
        website_vendors = len(result.all())
        
        # Vendors with logos
        logo_stmt = select(Vendor).where(Vendor.image_url.isnot(None))
        result = await session.exec(logo_stmt)
        logo_vendors = len(result.all())
        
        # Vendors with Google favicon logos (likely from previous runs)
        favicon_stmt = select(Vendor).where(Vendor.image_url.like('%google.com/s2/favicons%'))
        result = await session.exec(favicon_stmt)
        favicon_vendors = len(result.all())
        
        # Custom logos (non-favicon)
        custom_logo_stmt = select(Vendor).where(
            Vendor.image_url.isnot(None),
            ~Vendor.image_url.like('%google.com/s2/favicons%')
        )
        result = await session.exec(custom_logo_stmt)
        custom_logo_vendors = len(result.all())
        
        print(f"\n=== Logo Scraping Progress ===")
        print(f"Total vendors: {total_vendors}")
        print(f"Vendors with websites: {website_vendors}")
        print(f"Vendors with logos: {logo_vendors}")
        print(f"  - Custom logos: {custom_logo_vendors}")
        print(f"  - Google favicons: {favicon_vendors}")
        print(f"Progress vs websites: {logo_vendors}/{website_vendors} ({logo_vendors/website_vendors*100:.1f}%)")
        print(f"Progress vs total: {logo_vendors}/{total_vendors} ({logo_vendors/total_vendors*100:.1f}%)")
        
        # Show some recent logo examples
        recent_stmt = select(Vendor).where(
            Vendor.image_url.isnot(None),
            ~Vendor.image_url.like('%google.com/s2/favicons%')
        ).limit(5)
        result = await session.exec(recent_stmt)
        recent_vendors = result.all()
        
        if recent_vendors:
            print(f"\nRecent custom logos found:")
            for vendor in recent_vendors:
                print(f"  - {vendor.name}: {vendor.image_url}")
        
        break

if __name__ == '__main__':
    asyncio.run(monitor_progress())
