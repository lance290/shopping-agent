from unittest.mock import AsyncMock, patch

import pytest

from services.llm import generate_outreach_email


@pytest.mark.asyncio
async def test_outreach_fallback_uses_rich_raw_input_over_generic_row_title():
    with patch("services.llm.call_gemini", new=AsyncMock(side_effect=RuntimeError("boom"))):
        generated = await generate_outreach_email(
            row_title="Residential real estate listing services",
            vendor_company="Christie's International Real Estate",
            sender_name="BuyAnything Concierge",
            search_intent={
                "product_name": "Residential real estate listing services",
                "raw_input": "local boutique luxury real estate firms in Nashville for a $2.4M modern home with small acreage",
                "location_context": {
                    "relevance": "service_area",
                    "targets": {"search_area": "Nashville, TN"},
                },
            },
            structured_constraints={
                "search_area": "Nashville, TN",
                "budget": "$2.4M",
                "style": "modern",
                "acreage": "small",
                "local_only": True,
            },
        )

    assert "Residential real estate listing services" not in generated["subject"]
    assert "Nashville" in generated["subject"]
    assert "local boutique luxury real estate firms in Nashville" in generated["body"]
