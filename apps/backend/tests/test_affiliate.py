import pytest
import os
from affiliate import (
    AmazonAssociatesHandler, EbayPartnerHandler, NoAffiliateHandler,
    LinkResolver, ClickContext, SkimlinksHandler
)

@pytest.fixture
def context():
    return ClickContext(
        user_id=1,
        row_id=10,
        offer_index=0,
        source="test",
        merchant_domain="amazon.com",
    )

def test_amazon_handler_adds_tag(context):
    handler = AmazonAssociatesHandler(tag="test-20")
    result = handler.transform("https://amazon.com/dp/B08N5/", context)
    assert "tag=test-20" in result.final_url
    assert result.handler_name == "amazon_associates"
    assert result.rewrite_applied

def test_amazon_handler_no_tag_configured(context):
    handler = AmazonAssociatesHandler(tag="")
    result = handler.transform("https://amazon.com/dp/B08N5/", context)
    assert result.final_url == "https://amazon.com/dp/B08N5/"
    assert not result.rewrite_applied
    assert "error" in result.metadata

def test_ebay_handler_adds_campaign(context):
    context.merchant_domain = "ebay.com"
    handler = EbayPartnerHandler(campaign_id="123456", rotation_id="710-53481-19255-0")
    result = handler.transform("https://ebay.com/itm/12345", context)
    assert "mkevt=1" in result.final_url
    assert "mkcid=1" in result.final_url
    assert "mkrid=710-53481-19255-0" in result.final_url
    assert "campid=123456" in result.final_url
    assert "toolid=10001" in result.final_url
    assert result.handler_name == "ebay_partner"

def test_resolver_routes_to_correct_handler(context):
    resolver = LinkResolver()
    # Mock handlers are registered in __init__ but rely on env vars or default args.
    # We can manually register a configured handler for testing
    amazon_handler = AmazonAssociatesHandler(tag="test-tag")
    resolver.register(amazon_handler)
    
    result = resolver.resolve("https://amazon.com/dp/B08N5/", context)
    assert result.handler_name == "amazon_associates"
    assert "tag=test-tag" in result.final_url

def test_resolver_fallback_to_default(context):
    context.merchant_domain = "randomshop.com"
    resolver = LinkResolver()
    result = resolver.resolve("https://randomshop.com/product", context)
    assert result.handler_name == "none"
    assert result.final_url == "https://randomshop.com/product"


def test_skimlinks_handler_builds_redirect_url(context):
    context.merchant_domain = "randomshop.com"
    handler = SkimlinksHandler(publisher_id="pub_123")
    result = handler.transform("https://randomshop.com/product?ref=abc", context)
    assert result.handler_name == "skimlinks"
    assert result.rewrite_applied
    assert result.final_url.startswith("https://go.skimresources.com?id=pub_123&url=")
    # Ensure the original URL is encoded
    assert "https%3A%2F%2Frandomshop.com%2Fproduct%3Fref%3Dabc" in result.final_url


def test_resolver_fallback_to_skimlinks_when_configured(context, monkeypatch):
    context.merchant_domain = "randomshop.com"
    monkeypatch.setenv("SKIMLINKS_PUBLISHER_ID", "pub_123")
    resolver = LinkResolver()
    result = resolver.resolve("https://randomshop.com/product", context)
    assert result.handler_name == "skimlinks"
    assert result.rewrite_applied
    assert result.final_url.startswith("https://go.skimresources.com?id=pub_123&url=")
