import math

from sourcing.utils import (
    DEFAULT_CURRENCY_RATES,
    ConversionResult,
    canonicalize_url,
    convert_currency,
    normalize_currency_code,
)


def test_canonicalize_url_strips_tracking_and_normalizes_path():
    url = "HTTP://WWW.Example.com/products//laptop//?utm_source=ad&gclid=abc123&ref=foo&id=42"
    assert (
        canonicalize_url(url)
        == "https://example.com/products/laptop?id=42"
    )


def test_canonicalize_url_handles_relative_and_duplicate_params():
    url = "/shopping/deals?utm_medium=email&id=42&id=42"
    assert canonicalize_url(url) == "https://google.com/shopping/deals?id=42"


def test_normalize_currency_code_validates_iso():
    assert normalize_currency_code(" usd ") == "USD"
    assert normalize_currency_code("eur") == "EUR"
    assert normalize_currency_code("bad") is None
    assert normalize_currency_code("12") is None


def test_convert_currency_same_code_returns_amount():
    assert convert_currency(100, "USD", "usd") == 100.0


def test_convert_currency_with_metadata():
    result = convert_currency(
        100,
        from_currency="EUR",
        to_currency="USD",
        return_metadata=True,
    )
    assert isinstance(result, ConversionResult)
    assert math.isclose(result.amount, 108.0, rel_tol=1e-6)
    assert result.currency == "USD"
    assert result.rate_used > 0


def test_convert_currency_missing_rate_returns_none():
    custom_rates = DEFAULT_CURRENCY_RATES.copy()
    custom_rates.pop("EUR")
    assert convert_currency(10, "EUR", "USD", rates=custom_rates) is None
