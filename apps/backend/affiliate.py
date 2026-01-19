"""
Affiliate Link Handler Registry

This module provides a pluggable system for transforming outbound URLs
to include affiliate tracking codes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, List
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
import os


@dataclass
class ClickContext:
    """Context passed to handlers for URL transformation."""
    user_id: Optional[int]
    row_id: Optional[int]
    offer_index: int
    source: str
    merchant_domain: str


@dataclass
class ResolvedLink:
    """Result of affiliate link resolution."""
    final_url: str
    handler_name: str
    affiliate_tag: Optional[str] = None
    rewrite_applied: bool = False
    metadata: Optional[Dict] = None


class AffiliateHandler(ABC):
    """Base class for affiliate handlers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this handler."""
        pass
    
    @property
    @abstractmethod
    def domains(self) -> List[str]:
        """List of domains this handler can process."""
        pass
    
    @abstractmethod
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        """Transform the URL to include affiliate tracking."""
        pass


class NoAffiliateHandler(AffiliateHandler):
    """Default handler that passes URL through unchanged."""
    
    @property
    def name(self) -> str:
        return "none"
    
    @property
    def domains(self) -> List[str]:
        return []  # Matches nothing, used as fallback
    
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        return ResolvedLink(
            final_url=url,
            handler_name=self.name,
            rewrite_applied=False,
        )


class AmazonAssociatesHandler(AffiliateHandler):
    """Amazon Associates affiliate handler."""
    
    def __init__(self, tag: Optional[str] = None):
        self.tag = tag or os.getenv("AMAZON_AFFILIATE_TAG", "")
    
    @property
    def name(self) -> str:
        return "amazon_associates"
    
    @property
    def domains(self) -> List[str]:
        return [
            "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
            "amazon.it", "amazon.es", "amazon.ca", "amazon.com.au",
            "amazon.co.jp", "amazon.in", "amazon.com.mx", "amazon.com.br",
        ]
    
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        if not self.tag:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False,
                metadata={"error": "No affiliate tag configured"},
            )
        
        try:
            # Parse URL and add/replace tag parameter
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            query_params['tag'] = [self.tag]
            
            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            ))
            
            return ResolvedLink(
                final_url=new_url,
                handler_name=self.name,
                affiliate_tag=self.tag,
                rewrite_applied=True,
            )
        except Exception as e:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False,
                metadata={"error": f"Transformation failed: {str(e)}"},
            )


class EbayPartnerHandler(AffiliateHandler):
    """eBay Partner Network handler (simplified rover link)."""
    
    def __init__(self, campaign_id: Optional[str] = None):
        self.campaign_id = campaign_id or os.getenv("EBAY_CAMPAIGN_ID", "")
    
    @property
    def name(self) -> str:
        return "ebay_partner"
    
    @property
    def domains(self) -> List[str]:
        return ["ebay.com", "ebay.co.uk", "ebay.de", "ebay.fr", "ebay.it", "ebay.es"]
    
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        if not self.campaign_id:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False,
                metadata={"error": "No campaign ID configured"},
            )
        
        try:
            # eBay uses rover redirect links
            # Simplified: append campaign to URL params (real impl usually uses rover.ebay.com)
            # For this implementation, we'll just append campid/toolid query params to the existing URL
            # assuming the item URL is direct.
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            query_params['campid'] = [self.campaign_id]
            query_params['toolid'] = ['10001']  # Standard tool ID
            
            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            ))
            
            return ResolvedLink(
                final_url=new_url,
                handler_name=self.name,
                affiliate_tag=self.campaign_id,
                rewrite_applied=True,
            )
        except Exception as e:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False,
                metadata={"error": f"Transformation failed: {str(e)}"},
            )


class LinkResolver:
    """
    Routes URLs to appropriate affiliate handlers.
    
    Usage:
        resolver = LinkResolver()
        result = resolver.resolve(url, context)
    """
    
    def __init__(self):
        self.handlers: Dict[str, AffiliateHandler] = {}
        self.domain_map: Dict[str, str] = {}  # domain -> handler_name
        self.default_handler = NoAffiliateHandler()
        
        # Register built-in handlers
        self._register_builtin_handlers()
    
    def _register_builtin_handlers(self):
        """Register handlers that are always available."""
        self.register(AmazonAssociatesHandler())
        self.register(EbayPartnerHandler())
    
    def register(self, handler: AffiliateHandler):
        """Register a handler and map its domains."""
        self.handlers[handler.name] = handler
        for domain in handler.domains:
            self.domain_map[domain] = handler.name
    
    def resolve(self, url: str, context: ClickContext) -> ResolvedLink:
        """
        Resolve a URL to its affiliate-transformed version.
        
        Args:
            url: The canonical merchant URL
            context: Click context (user, row, etc.)
        
        Returns:
            ResolvedLink with final_url and handler info
        """
        # Find handler for this domain
        # Try exact match first, then maybe partial (not implemented yet)
        handler_name = self.domain_map.get(context.merchant_domain)
        
        # Check for www. mismatch or similar if exact match fails
        if not handler_name:
            # Simple check: if domain is 'amazon.com' and context is 'www.amazon.com'
            # (Note: context.merchant_domain is already normalized to remove www by extract_merchant_domain)
            pass

        if handler_name and handler_name in self.handlers:
            handler = self.handlers[handler_name]
            return handler.transform(url, context)
        
        # No matching handler, use default
        return self.default_handler.transform(url, context)
    
    def list_handlers(self) -> List[Dict]:
        """List all registered handlers (for admin UI)."""
        return [
            {
                "name": h.name,
                "domains": h.domains,
                "configured": self._is_configured(h),
            }
            for h in self.handlers.values()
        ]
    
    def _is_configured(self, handler: AffiliateHandler) -> bool:
        """Check if handler has required config (e.g., API keys)."""
        if isinstance(handler, AmazonAssociatesHandler):
            return bool(handler.tag)
        if isinstance(handler, EbayPartnerHandler):
            return bool(handler.campaign_id)
        return True


# Global singleton
link_resolver = LinkResolver()
