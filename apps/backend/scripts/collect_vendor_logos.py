#!/usr/bin/env python3
"""
Vendor Logo Scraper

This script scrapes logo URLs from vendor websites and updates the database.
It uses multiple strategies to find logos:
1. Common logo image paths (/logo.png, /assets/logo.png, etc.)
2. favicon extraction
3. Open Graph / Twitter Card meta tags
4. CSS background images
5. Structured data (JSON-LD)

Usage:
    python scripts/collect_vendor_logos.py [--limit N] [--dry-run]
"""

import asyncio
import logging
import re
import ssl
import sys
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from urllib.parse import urljoin, urlparse
import argparse

import aiohttp
import aiofiles
from bs4 import BeautifulSoup, SoupStrainer

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_session
from models import Vendor
from sqlmodel import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logo_scraping.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Common logo file patterns
LOGO_PATTERNS = [
    r'logo\.(png|jpg|jpeg|svg|gif|webp)',
    r'assets?/.*logo\.(png|jpg|jpeg|svg|gif|webp)',
    r'images?/.*logo\.(png|jpg|jpeg|svg|gif|webp)',
    r'img/.*logo\.(png|jpg|jpeg|svg|gif|webp)',
    r'static/.*logo\.(png|jpg|jpeg|svg|gif|webp)',
    r'wp-content/.*logo\.(png|jpg|jpeg|svg|gif|webp)',
    r'_next/static/.*logo\.(png|jpg|jpeg|svg|gif|webp)',
]

# Favicon patterns
FAVICON_PATTERNS = [
    'favicon.ico',
    'favicon.png',
    'apple-touch-icon.png',
    'apple-touch-icon-precomposed.png',
]

# User agent for requests
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

class LogoScraper:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        # Create SSL context that doesn't verify certificates (for scraping)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
    async def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page."""
        try:
            headers = {'User-Agent': USER_AGENT}
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        content = await response.text()
                        # Parse only relevant parts to speed up processing
                        parse_only = SoupStrainer(['head', 'header', 'footer', 'img', 'link', 'meta'])
                        return BeautifulSoup(content, 'html.parser', parse_only=parse_only)
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_meta_logo(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract logo from Open Graph / Twitter Card meta tags."""
        meta_selectors = [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]',
            'meta[property="og:logo"]',
            'meta[name="logo"]',
            'meta[itemprop="logo"]',
        ]
        
        for selector in meta_selectors:
            meta_tag = soup.select_one(selector)
            if meta_tag and meta_tag.get('content'):
                logo_url = urljoin(base_url, meta_tag['content'])
                if self._is_likely_logo(logo_url):
                    return logo_url
        
        return None
    
    def extract_favicon(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract favicon as potential logo."""
        favicon_selectors = [
            'link[rel="icon"]',
            'link[rel="shortcut icon"]',
            'link[rel="apple-touch-icon"]',
        ]
        
        for selector in favicon_selectors:
            link = soup.select_one(selector)
            if link and link.get('href'):
                favicon_url = urljoin(base_url, link['href'])
                return favicon_url
        
        # Try common favicon paths
        for favicon in FAVICON_PATTERNS:
            favicon_url = urljoin(base_url, favicon)
            return favicon_url
        
        return None
    
    def extract_structured_data_logo(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract logo from JSON-LD structured data."""
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                if not script.string:
                    continue
                import json
                data = json.loads(script.string)
                
                # Handle single object or array
                if isinstance(data, list):
                    items = data
                else:
                    items = [data]
                
                for item in items:
                    # Look for organization/logo
                    if isinstance(item, dict):
                        logo = item.get('logo')
                        if logo:
                            if isinstance(logo, str):
                                return urljoin(base_url, logo)
                            elif isinstance(logo, dict) and logo.get('url'):
                                return urljoin(base_url, logo['url'])
            except (json.JSONDecodeError, AttributeError, TypeError):
                continue
        
        return None
    
    def extract_css_logos(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract logos from CSS background images (limited)."""
        logos = []
        
        # Look for header/logo divs with background images
        logo_selectors = [
            '.logo',
            '.brand',
            '.header-logo',
            '.site-logo',
            '[class*="logo"]',
            '[id*="logo"]',
        ]
        
        for selector in logo_selectors:
            elements = soup.select(selector)
            for element in elements:
                style = element.get('style', '')
                bg_match = re.search(r'background-image:\s*url\([\'"]?([^\'")]+)[\'"]?\)', style)
                if bg_match:
                    logo_url = urljoin(base_url, bg_match.group(1))
                    if self._is_likely_logo(logo_url):
                        logos.append(logo_url)
        
        return logos
    
    def extract_img_logos(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract logos from img tags with logo-like attributes."""
        logos = []
        
        # Look for images with logo-like attributes
        for img in soup.find_all('img'):
            # Check src, alt, class, id for logo indicators
            src = img.get('src', '')
            alt = img.get('alt', '').lower()
            class_attr = ' '.join(img.get('class', [])).lower()
            id_attr = img.get('id', '').lower()
            
            # Check if this looks like a logo
            logo_indicators = ['logo', 'brand', 'site-title', 'header-image']
            if (any(indicator in src.lower() for indicator in logo_indicators) or
                any(indicator in alt for indicator in logo_indicators) or
                any(indicator in class_attr for indicator in logo_indicators) or
                any(indicator in id_attr for indicator in logo_indicators)):
                
                logo_url = urljoin(base_url, src)
                if self._is_likely_logo(logo_url):
                    logos.append(logo_url)
        
        return logos
    
    def _is_likely_logo(self, url: str) -> bool:
        """Check if URL is likely a logo based on patterns."""
        url_lower = url.lower()
        
        # Common logo patterns
        logo_patterns = [
            r'logo',
            r'brand',
            r'site[-_]title',
            r'header[-_]image',
            r'favicon',
        ]
        
        # Exclude non-logo patterns
        exclude_patterns = [
            r'banner',
            r'hero',
            r'slider',
            r'carousel',
            r'background',
            r'pattern',
            r'texture',
            r'avatar',
            r'profile',
            r'product',
            r'thumbnail',
        ]
        
        # Check if any logo pattern matches
        if any(re.search(pattern, url_lower) for pattern in logo_patterns):
            # Ensure no exclude pattern matches
            if not any(re.search(pattern, url_lower) for pattern in exclude_patterns):
                return True
        
        return False
    
    async def find_logo_url(self, website_url: str) -> Optional[str]:
        """Find the best logo URL for a website."""
        if not website_url:
            return None
        
        # Ensure URL has scheme
        if not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url
        
        logger.info(f"Scraping logo for {website_url}")
        
        soup = await self.fetch_page(website_url)
        if not soup:
            return None
        
        # Try different extraction methods in order of preference
        logo_candidates = []
        
        # 1. Meta tags (most reliable)
        meta_logo = self.extract_meta_logo(soup, website_url)
        if meta_logo:
            logo_candidates.append(('meta', meta_logo))
        
        # 2. Structured data
        structured_logo = self.extract_structured_data_logo(soup, website_url)
        if structured_logo:
            logo_candidates.append(('structured', structured_logo))
        
        # 3. IMG tags
        img_logos = self.extract_img_logos(soup, website_url)
        for logo in img_logos[:3]:  # Limit to top 3
            logo_candidates.append(('img', logo))
        
        # 4. CSS backgrounds
        css_logos = self.extract_css_logos(soup, website_url)
        for logo in css_logos[:2]:  # Limit to top 2
            logo_candidates.append(('css', logo))
        
        # 5. Favicon (fallback)
        favicon = self.extract_favicon(soup, website_url)
        if favicon:
            logo_candidates.append(('favicon', favicon))
        
        # Return the best candidate (meta tags preferred)
        for source, logo_url in logo_candidates:
            if await self._validate_logo(logo_url):
                logger.info(f"Found logo via {source}: {logo_url}")
                return logo_url
        
        return None
    
    async def _validate_logo(self, logo_url: str) -> bool:
        """Validate that a logo URL is accessible and looks like a logo."""
        try:
            headers = {'User-Agent': USER_AGENT}
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.head(logo_url, headers=headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        return content_type.startswith('image/')
                    return False
        except Exception:
            return False

async def collect_vendor_logos(limit: Optional[int] = None, dry_run: bool = False):
    """Collect logos for all vendors in the database."""
    
    # Connect to database
    async for session in get_session():
        # Get vendors without logos
        stmt = select(Vendor).where(Vendor.website.isnot(None))
        if limit:
            stmt = stmt.limit(limit)
        
        result = await session.exec(stmt)
        vendors = result.all()
        
        logger.info(f"Processing {len(vendors)} vendors")
        
        # Create HTTP session
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=5)
        async with aiohttp.ClientSession(connector=connector) as http_session:
            scraper = LogoScraper(http_session)
            
            updated_count = 0
            for i, vendor in enumerate(vendors, 1):
                logger.info(f"Processing {i}/{len(vendors)}: {vendor.name}")
                
                # Skip if already has logo
                if vendor.image_url:
                    logger.info(f"  Already has logo: {vendor.image_url}")
                    continue
                
                # Find logo URL
                logo_url = await scraper.find_logo_url(vendor.website)
                
                if logo_url:
                    logger.info(f"  Found logo: {logo_url}")
                    if not dry_run:
                        vendor.image_url = logo_url
                        session.add(vendor)
                        updated_count += 1
                else:
                    logger.info(f"  No logo found")
                
                # Commit every 10 updates
                if i % 10 == 0 and not dry_run:
                    await session.commit()
                    logger.info(f"  Committed batch (total updated: {updated_count})")
            
            # Final commit
            if not dry_run:
                await session.commit()
                logger.info(f"Final commit completed. Total updated: {updated_count}")
        
        break  # Exit the async for loop

def main():
    parser = argparse.ArgumentParser(description='Collect vendor logos from websites')
    parser.add_argument('--limit', type=int, help='Limit number of vendors to process')
    parser.add_argument('--dry-run', action='store_true', help='Run without updating database')
    
    args = parser.parse_args()
    
    logger.info(f"Starting logo collection (limit={args.limit}, dry_run={args.dry_run})")
    
    try:
        asyncio.run(collect_vendor_logos(limit=args.limit, dry_run=args.dry_run))
        logger.info("Logo collection completed successfully")
    except KeyboardInterrupt:
        logger.info("Logo collection interrupted by user")
    except Exception as e:
        logger.error(f"Logo collection failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
