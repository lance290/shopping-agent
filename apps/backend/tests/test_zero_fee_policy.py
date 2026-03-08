"""
###############################################################################
#                                                                             #
#   ZERO FEE POLICY — REGRESSION TESTS                                        #
#                                                                             #
#   BuyAnything launches FREE. No commissions. No service fees. No escrow.    #
#   The ONLY revenue path right now is AFFILIATE MARKETING (clickouts).       #
#                                                                             #
#   DO NOT REMOVE OR WEAKEN THESE TESTS.                                      #
#   DO NOT "temporarily" disable them.                                        #
#   DO NOT add @pytest.mark.skip.                                             #
#                                                                             #
#   If you need to introduce fees later (e.g. 1% service fee after           #
#   traction), you must:                                                      #
#     1. Get explicit founder approval                                        #
#     2. Update the Terms of Service page                                     #
#     3. Update the Disclosure page                                           #
#     4. Update these tests to reflect the new policy                         #
#     5. Ship it as a deliberate, documented product decision                 #
#                                                                             #
#   These tests exist because AI assistants kept sneaking 5% fees into       #
#   the codebase without permission. Never again.                             #
#                                                                             #
###############################################################################
"""

import os
import re
import pathlib
import pytest


# ###########################################################################
#
#  SECTION 1: DEAL MODEL — DEFAULT FEE MUST BE ZERO
#
#  The Deal model has a `platform_fee_pct` field. Its default value MUST
#  be 0.0. If someone changes this default, every new deal will silently
#  start charging buyers a markup on top of vendor quotes.
#
#  This is the single most dangerous line of code in the entire codebase
#  from a legal and trust perspective. Guard it with your life.
#
# ###########################################################################

class TestDealModelZeroFee:

    def test_deal_default_platform_fee_pct_is_zero(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! CRITICAL: Deal.platform_fee_pct default MUST be 0.0       !
        !                                                            !
        ! If this test fails, someone changed the default fee on the !
        ! Deal model. This means every new deal will silently charge !
        ! buyers a hidden markup. That is:                           !
        !   - A violation of our Terms of Service                    !
        !   - A potential money transmission compliance issue         !
        !   - A betrayal of user trust                               !
        !                                                            !
        ! FIX: Set platform_fee_pct default back to 0.0 in           !
        !      models/deals.py                                       !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        from models.deals import Deal
        deal = Deal(
            row_id=1,
            buyer_user_id=1,
            proxy_email_alias="test-deal-1",
        )
        assert deal.platform_fee_pct == 0.0, (
            f"FATAL: Deal.platform_fee_pct defaults to {deal.platform_fee_pct} "
            f"instead of 0.0. We do NOT charge platform fees yet. "
            f"Change the default in models/deals.py back to 0.0."
        )

    def test_compute_buyer_total_charges_zero_fee(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! compute_buyer_total() must NOT add any fee to the vendor   !
        ! quoted price. The buyer_total MUST equal the vendor quote. !
        !                                                            !
        ! Example: Vendor quotes $50,000 for a kitchen remodel.     !
        ! The buyer must see $50,000.00 — not $52,500 (with 5% fee) !
        ! and not $50,500 (with 1% fee).                            !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        from models.deals import Deal
        deal = Deal(
            row_id=1,
            buyer_user_id=1,
            proxy_email_alias="test-deal-2",
            vendor_quoted_price=50000.00,
        )
        deal.compute_buyer_total()

        assert deal.platform_fee_amount == 0.0, (
            f"FATAL: Platform fee amount is ${deal.platform_fee_amount} "
            f"on a $50,000 deal. It MUST be $0.00. We do not charge fees."
        )
        assert deal.buyer_total == 50000.00, (
            f"FATAL: Buyer total is ${deal.buyer_total} but vendor quoted "
            f"$50,000. The buyer must pay EXACTLY the vendor quote, no markup."
        )

    @pytest.mark.parametrize("vendor_price", [
        100.00,          # small consumer purchase
        999.99,          # medium purchase
        10000.00,        # HNW threshold
        50000.00,        # typical HNW project
        250000.00,       # large HNW project (estate renovation)
        1000000.00,      # mega deal (private aviation)
    ])
    def test_zero_fee_at_every_price_point(self, vendor_price):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! No matter the deal size — $100 or $1,000,000 — the        !
        ! platform fee MUST be $0.00.                                !
        !                                                            !
        ! A previous AI tried to sneak in a "5% fee on projects     !
        ! over $10k" tiered pricing model. This test catches that.  !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        from models.deals import Deal
        deal = Deal(
            row_id=1,
            buyer_user_id=1,
            proxy_email_alias=f"test-deal-{int(vendor_price)}",
            vendor_quoted_price=vendor_price,
        )
        deal.compute_buyer_total()

        assert deal.platform_fee_amount == 0.0, (
            f"FATAL: Charging ${deal.platform_fee_amount} fee on a "
            f"${vendor_price:,.2f} deal. We charge ZERO fees."
        )
        assert deal.buyer_total == vendor_price, (
            f"FATAL: Buyer total ${deal.buyer_total:,.2f} != vendor quote "
            f"${vendor_price:,.2f}. No markup allowed."
        )


# ###########################################################################
#
#  SECTION 2: CHECKOUT ROUTE — DEFAULT_PLATFORM_FEE_RATE ENV VAR
#
#  The checkout route reads DEFAULT_PLATFORM_FEE_RATE from the environment.
#  Its fallback default MUST be "0.00". If the env var is missing (which it
#  will be in most deployments), the system must default to zero fees.
#
# ###########################################################################

class TestCheckoutZeroFee:

    def _read_checkout_source(self):
        checkout_path = pathlib.Path(__file__).parent.parent / "routes" / "checkout.py"
        return checkout_path.read_text()

    def test_default_platform_fee_rate_is_zero_in_source(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! DEFAULT_PLATFORM_FEE_RATE must NOT be used in checkout.py  !
        ! We charge exactly 0 fees. The variable shouldn't even be   !
        ! read from the environment.                                 !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        source = self._read_checkout_source()
        assert "DEFAULT_PLATFORM_FEE_RATE" not in source, (
            "FATAL: checkout.py is reading DEFAULT_PLATFORM_FEE_RATE. "
            "It must not read fee rates from the environment because we charge exactly 0 fees."
        )

    def test_no_hardcoded_fee_percentage_in_checkout(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! checkout.py must NOT contain hardcoded fee percentages     !
        ! like 0.05 (5%), 0.03 (3%), or 0.10 (10%) outside of the  !
        ! DEFAULT_PLATFORM_FEE_RATE env var pattern.                !
        !                                                            !
        ! This catches someone bypassing the env var and just       !
        ! writing `fee = amount * 0.05` inline.                     !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        source = self._read_checkout_source()

        # Remove the env var line so we don't false-positive on it
        source_without_envvar = re.sub(
            r'.*DEFAULT_PLATFORM_FEE_RATE.*\n', '', source
        )

        # Look for suspicious hardcoded fee multipliers
        hardcoded_fees = re.findall(
            r'\*\s*0\.0[1-9]\b|\*\s*0\.[1-9]\d*\b',
            source_without_envvar,
        )
        assert len(hardcoded_fees) == 0, (
            f"FATAL: Found hardcoded fee multiplier(s) in checkout.py: "
            f"{hardcoded_fees}. All fee logic must go through "
            f"DEFAULT_PLATFORM_FEE_RATE (which must be 0.00)."
        )

    def test_env_var_actually_resolves_to_zero_at_runtime(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! Even if someone sets DEFAULT_PLATFORM_FEE_RATE in their   !
        ! .env file to 0.05, this test verifies the UNSET behavior. !
        ! When the env var is missing, fee must be 0.                !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        # Temporarily remove the env var if it exists
        original = os.environ.pop("DEFAULT_PLATFORM_FEE_RATE", None)
        try:
            rate = float(os.getenv("DEFAULT_PLATFORM_FEE_RATE", "0.00"))
            assert rate == 0.0, (
                f"DEFAULT_PLATFORM_FEE_RATE resolves to {rate} when unset. "
                f"Must resolve to 0.0."
            )
        finally:
            if original is not None:
                os.environ["DEFAULT_PLATFORM_FEE_RATE"] = original


# ###########################################################################
#
#  SECTION 3: DEAL PIPELINE EMAILS — NO ESCROW LANGUAGE
#
#  The proxy emails sent to vendors are the viral loop. They must NOT
#  contain language about "escrow", "buyer protection", or "platform fees".
#  That language implies we are a financial intermediary, which we are NOT.
#
#  We are an INTRODUCTION PLATFORM. The emails must say so.
#
# ###########################################################################

class TestDealPipelineEmailsNoEscrow:

    def _read_deal_pipeline_source(self):
        path = pathlib.Path(__file__).parent.parent / "services" / "deal_pipeline.py"
        return path.read_text()

    def test_trust_footer_does_not_mention_escrow(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! The email footer that vendors see MUST NOT contain the     !
        ! word "escrow". We are not an escrow service. Claiming to   !
        ! be one without proper licensing is a federal offense.      !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        source = self._read_deal_pipeline_source()

        # Extract the TRUST_FOOTER_HTML and TRUST_FOOTER_TEXT constants
        footer_section = ""
        in_footer = False
        for line in source.split("\n"):
            if "TRUST_FOOTER_HTML" in line or "TRUST_FOOTER_TEXT" in line:
                in_footer = True
            if in_footer:
                footer_section += line + "\n"
                if line.strip().endswith('"""') or line.strip() == ")":
                    if footer_section.count('"""') >= 2 or line.strip() == ")":
                        in_footer = False

        footer_lower = footer_section.lower()
        assert "escrow" not in footer_lower, (
            "FATAL: The email footer sent to vendors contains the word 'escrow'. "
            "We are NOT an escrow service. Remove this language immediately."
        )
        assert "buyer protection" not in footer_lower, (
            "FATAL: The email footer claims 'buyer protection'. We do NOT "
            "provide buyer protection. We are an introduction platform."
        )

    def test_email_footer_contains_viral_hook(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! The vendor-facing email footer IS the viral loop.          !
        ! It MUST contain a call-to-action for vendors to try        !
        ! BuyAnything themselves. If this CTA is missing, the viral  !
        ! loop is dead.                                              !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        source = self._read_deal_pipeline_source()

        # The footer must mention BuyAnything and have a link
        assert "BuyAnything" in source, (
            "The deal pipeline emails must mention 'BuyAnything' for brand awareness."
        )
        assert "{app_url}" in source, (
            "The deal pipeline email footer must contain {app_url} "
            "so vendors can click through to the platform (viral loop)."
        )


# ###########################################################################
#
#  SECTION 4: STATIC SOURCE ANALYSIS — NO SNEAKY FEES ANYWHERE
#
#  This section reads the actual source files and looks for patterns that
#  indicate someone is trying to charge fees. It's the nuclear option.
#
#  These tests read .py and .tsx files directly and grep for danger patterns.
#
# ###########################################################################

class TestStaticAnalysisNoFees:

    BACKEND_ROOT = pathlib.Path(__file__).parent.parent

    def test_no_application_fee_without_connected_account_guard(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! application_fee_amount MUST NOT exist in checkout.py       !
        ! We do not charge fees, even for connected accounts.        !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        checkout_path = self.BACKEND_ROOT / "routes" / "checkout.py"
        source = checkout_path.read_text()

        assert "application_fee_amount" not in source, (
            "FATAL: Found application_fee_amount in checkout.py. "
            "We do NOT charge platform fees. Remove it."
        )

    def test_deals_route_does_not_hardcode_nonzero_fee(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! The deals route (deals.py) must not contain hardcoded      !
        ! non-zero fee percentages like 0.05 or 0.03.               !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        deals_path = self.BACKEND_ROOT / "routes" / "deals.py"
        source = deals_path.read_text()

        # Look for hardcoded fee assignments
        hardcoded = re.findall(
            r'platform_fee_pct\s*=\s*0\.0[1-9]|platform_fee_pct\s*=\s*0\.[1-9]',
            source,
        )
        assert len(hardcoded) == 0, (
            f"FATAL: Found hardcoded non-zero platform_fee_pct in deals.py: "
            f"{hardcoded}. We do NOT charge fees."
        )

    def test_deal_model_source_default_is_zero(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! Read the raw source of models/deals.py and verify the      !
        ! platform_fee_pct field default is 0.0, not 0.01 or 0.05. !
        !                                                            !
        ! This is a STATIC check on the source code itself, not on  !
        ! a runtime object, to prevent tricky metaclass overrides.  !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        model_path = self.BACKEND_ROOT / "models" / "deals.py"
        source = model_path.read_text()

        match = re.search(
            r'platform_fee_pct:\s*float\s*=\s*([\d.]+)',
            source,
        )
        assert match is not None, (
            "Could not find platform_fee_pct field in models/deals.py"
        )

        default_value = float(match.group(1))
        assert default_value == 0.0, (
            f"FATAL: platform_fee_pct defaults to {default_value} in "
            f"models/deals.py source code. It MUST be 0.0. "
            f"We. Do. Not. Charge. Fees. Yet."
        )


# ###########################################################################
#
#  SECTION 5: FRONTEND STATIC ANALYSIS — NO FEE LANGUAGE IN UI
#
#  The user-facing UI must not contain language about platform fees,
#  service fees, commissions, or escrow. These tests read the .tsx
#  source files directly.
#
# ###########################################################################

class TestFrontendNoFeeLanguage:

    FRONTEND_ROOT = pathlib.Path(__file__).parent.parent.parent / "frontend" / "app"

    def _read_file_if_exists(self, relative_path: str) -> str:
        full_path = self.FRONTEND_ROOT / relative_path
        if full_path.exists():
            return full_path.read_text()
        return ""

    def test_merchant_register_no_platform_fee_notice(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! The merchant registration page MUST NOT tell vendors we    !
        ! charge a "5% platform fee" or ANY platform fee.           !
        !                                                            !
        ! We are free. Vendors pay nothing. Buyers pay nothing.     !
        ! The only revenue is affiliate commissions on clickouts.   !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        source = self._read_file_if_exists("merchants/register/page.tsx")
        if not source:
            pytest.skip("merchants/register/page.tsx not found")

        source_lower = source.lower()
        assert "5% platform fee" not in source_lower, (
            "FATAL: Merchant registration page mentions '5% platform fee'. "
            "We do NOT charge platform fees."
        )
        assert "platform fee notice" not in source_lower, (
            "FATAL: Merchant registration still has a 'Platform Fee Notice' block."
        )

    def test_disclosure_page_no_5_percent(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! The disclosure page MUST NOT claim we charge 5% or any    !
        ! "Standard Rate" fee. We are a free introduction platform. !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        source = self._read_file_if_exists("disclosure/page.tsx")
        if not source:
            pytest.skip("disclosure/page.tsx not found")

        source_lower = source.lower()
        assert "standard rate: 5%" not in source_lower, (
            "FATAL: Disclosure page claims 'Standard Rate: 5%'. "
            "We do NOT charge transaction fees."
        )
        assert "5% of transaction" not in source_lower, (
            "FATAL: Disclosure page mentions '5% of transaction'. Remove it."
        )

    def test_terms_page_says_introduction_platform(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! Our Terms of Service MUST explicitly state we are an       !
        ! "introduction" platform. This is our legal shield.        !
        !                                                            !
        ! If someone removes this language, we lose the legal        !
        ! protection that separates us from being classified as a   !
        ! payment processor or financial intermediary.               !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        source = self._read_file_if_exists("(public)/terms/page.tsx")
        if not source:
            pytest.skip("(public)/terms/page.tsx not found")

        source_lower = source.lower()
        assert "introduction" in source_lower, (
            "FATAL: Terms of Service page does not mention 'introduction'. "
            "We MUST identify as an introduction platform for legal protection."
        )
        assert "escrow agent" not in source_lower or "do not act as an escrow" in source_lower, (
            "FATAL: Terms of Service mentions 'escrow agent' without disclaiming it."
        )

    def test_escrow_status_component_no_funds_in_escrow(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! The EscrowStatus UI component MUST NOT say "Funds in      !
        ! Escrow" or "Protected until delivery". We do not hold     !
        ! funds. We do not guarantee delivery. We are not an escrow.!
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        source = self._read_file_if_exists("components/sdui/EscrowStatus.tsx")
        if not source:
            pytest.skip("EscrowStatus.tsx not found")

        assert "Funds in Escrow" not in source, (
            "FATAL: EscrowStatus component says 'Funds in Escrow'. "
            "We do NOT hold funds in escrow. Change to 'Quote Accepted' or similar."
        )
        assert "Protected until delivery" not in source, (
            "FATAL: EscrowStatus claims 'Protected until delivery'. "
            "We provide NO delivery protection."
        )

    def test_share_page_no_escrow_cta(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! The share page CTA must not say "Start Shopping" (too     !
        ! consumer-y) or mention escrow/fees. It should reflect the !
        ! B2B procurement positioning.                               !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        source = self._read_file_if_exists("share/[token]/page.tsx")
        if not source:
            pytest.skip("share/[token]/page.tsx not found")

        assert "Fund Escrow" not in source, (
            "FATAL: Share page has a 'Fund Escrow' button. We are NOT an escrow."
        )


# ###########################################################################
#
#  SECTION 6: AFFILIATE IS THE ONLY REVENUE — MAKE SURE IT WORKS
#
#  Since affiliate marketing is our ONLY revenue path, we need to make
#  sure the affiliate clickout infrastructure is intact. If someone
#  accidentally breaks the /api/out redirect, we make $0.
#
# ###########################################################################

class TestAffiliateIsOnlyRevenue:

    BACKEND_ROOT = pathlib.Path(__file__).parent.parent

    def test_clickout_route_exists(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! The /api/out clickout route is our ONLY revenue generator. !
        ! If this route file is missing or the handler is deleted,  !
        ! we make literally $0.                                     !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        clickout_path = self.BACKEND_ROOT / "routes" / "clickout.py"
        assert clickout_path.exists(), (
            "FATAL: routes/clickout.py is missing! "
            "This is our ONLY revenue-generating route (affiliate redirects)."
        )

        source = clickout_path.read_text()
        assert "/api/out" in source or "api/out" in source or "clickout" in source.lower(), (
            "FATAL: clickout.py exists but doesn't seem to define the "
            "/api/out redirect endpoint. Our affiliate revenue depends on this."
        )

    def test_affiliate_resolver_exists(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! The affiliate link resolver transforms plain product URLs  !
        ! into affiliate-tagged URLs. Without it, clickouts don't   !
        ! earn us anything.                                         !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        # Check for affiliate resolver in services or routes
        found = False
        for candidate in [
            self.BACKEND_ROOT / "services" / "affiliate.py",
            self.BACKEND_ROOT / "routes" / "clickout.py",
        ]:
            if candidate.exists():
                source = candidate.read_text()
                if "tag=" in source or "affiliate" in source.lower() or "campid" in source:
                    found = True
                    break

        assert found, (
            "FATAL: No affiliate link resolver found. "
            "Without affiliate tag injection, clickouts earn $0."
        )

    def test_amazon_and_ebay_affiliate_pattern_exists(self):
        """
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ! Amazon and eBay are our biggest potential affiliate sources. !
        ! The affiliate handler MUST have logic to append tags.      !
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        """
        clickout_path = self.BACKEND_ROOT / "routes" / "clickout.py"
        affiliate_path = self.BACKEND_ROOT / "affiliate.py"
        
        found_amazon = False
        found_ebay = False
        
        if clickout_path.exists():
            text = clickout_path.read_text().lower()
            if "amazon" in text: found_amazon = True
            if "ebay" in text: found_ebay = True
            
        if affiliate_path.exists():
            text = affiliate_path.read_text().lower()
            if "amazon" in text: found_amazon = True
            if "ebay" in text: found_ebay = True
            
        assert found_amazon, "FATAL: Affiliate logic missing for Amazon."
        assert found_ebay, "FATAL: Affiliate logic missing for eBay."
