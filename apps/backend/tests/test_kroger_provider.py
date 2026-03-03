from sourcing.kroger_provider import KrogerProvider


def test_kroger_product_url_includes_slug_and_id():
    url = KrogerProvider._build_product_url(
        "Kroger 2% Reduced Fat Milk Half Gallon",
        "0001111041600",
    )
    assert url.startswith("https://www.kroger.com/p/")
    assert url.endswith("/0001111041600")
    assert "/kroger-2-reduced-fat-milk-half-gallon/" in url
