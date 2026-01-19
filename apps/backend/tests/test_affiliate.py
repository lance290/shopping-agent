import pytest
import os
from affiliate import (
    AmazonAssociatesHandler, EbayPartnerHandler, NoAffiliateHandler,
    LinkResolver, ClickContext
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
    handler = EbayPartnerHandler(campaign_id="123456")
    result = handler.transform("https://ebay.com/itm/12345", context)
    assert "campid=123456" in result.final_url
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
