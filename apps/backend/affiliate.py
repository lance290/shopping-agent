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
    """eBay Partner Network handler (EPN tracking link format)."""
    
    def __init__(
        self,
        campaign_id: Optional[str] = None,
        rotation_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        event_type: Optional[str] = None,
        tool_id: Optional[str] = None,
        custom_id: Optional[str] = None,
    ):
        self.campaign_id = campaign_id or os.getenv("EBAY_CAMPAIGN_ID", "")
        # Per eBay docs: mkrid is the rotation ID for the marketplace.
        self.rotation_id = rotation_id or os.getenv("EBAY_ROTATION_ID", "")
        # Per eBay docs: mkcid is the channel ID. Default commonly 1 (EPN).
        self.channel_id = channel_id or os.getenv("EBAY_CHANNEL_ID", "1")
        # Per eBay docs: mkevt is tracking event type. Default 1 = click.
        self.event_type = event_type or os.getenv("EBAY_EVENT_TYPE", "1")
        # Per eBay docs: toolid default 10001.
        self.tool_id = tool_id or os.getenv("EBAY_TOOL_ID", "10001")
        # Optional sub ID.
        self.custom_id = custom_id or os.getenv("EBAY_CUSTOM_ID", "")
    
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

        if not self.rotation_id:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False,
                metadata={"error": "No rotation ID configured (EBAY_ROTATION_ID)"},
            )
        
        try:
            # Proper EPN tracking link format (per eBay docs):
            # {target}&mkevt={event_type}&mkcid={channel_id}&mkrid={rotation_id}&campid={campaign_id}&toolid={tool_id}&customid={custom_id}
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            query_params['mkevt'] = [self.event_type]
            query_params['mkcid'] = [self.channel_id]
            query_params['mkrid'] = [self.rotation_id]
            query_params['campid'] = [self.campaign_id]
            query_params['toolid'] = [self.tool_id]

            custom_id = self.custom_id
            if not custom_id:
                # Best-effort per-click sub-id for attribution/debugging (<=256 chars).
                parts = []
                if context.user_id is not None:
                    parts.append(f"u{context.user_id}")
                if context.row_id is not None:
                    parts.append(f"r{context.row_id}")
                parts.append(f"i{context.offer_index}")
                custom_id = "_".join(parts)[:256]
            if custom_id:
                query_params['customid'] = [custom_id]
            
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
                metadata={
                    "mkevt": self.event_type,
                    "mkcid": self.channel_id,
                    "mkrid": self.rotation_id,
                    "toolid": self.tool_id,
                },
            )
        except Exception as e:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False,
                metadata={"error": f"Transformation failed: {str(e)}"},
            )


class SkimlinksHandler(AffiliateHandler):
    """
    Skimlinks universal affiliate handler.
    Works with 48,000+ merchants automatically.
    
    Skimlinks uses a redirect through their domain:
    https://go.skimresources.com?id=PUBLISHER_ID&url=ENCODED_URL
    """
    
    def __init__(self, publisher_id: Optional[str] = None):
        self.publisher_id = publisher_id or os.getenv("SKIMLINKS_PUBLISHER_ID", "")
    
    @property
    def name(self) -> str:
        return "skimlinks"
    
    @property
    def domains(self) -> List[str]:
        return []  # Universal fallback - doesn't match specific domains
    
    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        if not self.publisher_id:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False,
                metadata={"error": "No Skimlinks publisher ID configured"},
            )
        
        try:
            from urllib.parse import quote
            # Skimlinks redirect format
            skimlinks_url = f"https://go.skimresources.com?id={self.publisher_id}&url={quote(url, safe='')}"
            
            return ResolvedLink(
                final_url=skimlinks_url,
                handler_name=self.name,
                affiliate_tag=self.publisher_id,
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
        self.skimlinks_handler = SkimlinksHandler()  # Universal fallback
        
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
        
        # No domain-specific handler - try Skimlinks universal fallback
        if self.skimlinks_handler.publisher_id:
            return self.skimlinks_handler.transform(url, context)
        
        # No Skimlinks configured, use default (no affiliate)
        return self.default_handler.transform(url, context)
    
    def list_handlers(self) -> List[Dict]:
        """List all registered handlers (for admin UI)."""
        handlers = [
            {
                "name": h.name,
                "domains": h.domains,
                "configured": self._is_configured(h),
            }
            for h in self.handlers.values()
        ]
        # Add Skimlinks universal handler
        handlers.append({
            "name": self.skimlinks_handler.name,
            "domains": ["(universal fallback)"],
            "configured": bool(self.skimlinks_handler.publisher_id),
        })
        return handlers
    
    def _is_configured(self, handler: AffiliateHandler) -> bool:
        """Check if handler has required config (e.g., API keys)."""
        if isinstance(handler, AmazonAssociatesHandler):
            return bool(handler.tag)
        if isinstance(handler, EbayPartnerHandler):
            return bool(handler.campaign_id)
        if isinstance(handler, SkimlinksHandler):
            return bool(handler.publisher_id)
        return True


# Global singleton
link_resolver = LinkResolver()
