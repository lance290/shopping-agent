"""Currency normalization and conversion utilities."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Mapping, MutableMapping, Optional

DEFAULT_CURRENCY_RATES: "Mapping[str, Decimal]" = {
    "USD": Decimal("1"),
    "EUR": Decimal("1.08"),
    "GBP": Decimal("1.27"),
    "CAD": Decimal("0.74"),
    "AUD": Decimal("0.66"),
    "JPY": Decimal("0.0067"),
    "CNY": Decimal("0.14"),
    "INR": Decimal("0.012"),
    "MXN": Decimal("0.058"),
}

KNOWN_CURRENCIES = set(DEFAULT_CURRENCY_RATES.keys())


@dataclass(frozen=True)
class ConversionResult:
    amount: float
    currency: str
    rate_used: Decimal


def normalize_currency_code(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    trimmed = code.strip().upper()
    if len(trimmed) != 3 or not trimmed.isalpha():
        return None
    if trimmed not in KNOWN_CURRENCIES:
        return None
    return trimmed


def _to_decimal(amount: float | int | str | Decimal | None) -> Optional[Decimal]:
    if amount is None:
        return None
    if isinstance(amount, Decimal):
        return amount
    try:
        return Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        return None


def convert_currency(
    amount: float | int | str | Decimal | None,
    from_currency: Optional[str],
    to_currency: Optional[str] = "USD",
    *,
    rates: Mapping[str, Decimal] = DEFAULT_CURRENCY_RATES,
    precision: int = 2,
    return_metadata: bool = False,
) -> Optional[float | ConversionResult]:
    """Convert an amount between currencies using static FX references.

    Args:
        amount: Numeric value to convert.
        from_currency: ISO currency code of the amount provided.
        to_currency: Target ISO currency code (default USD).
        rates: Mapping of currency -> USD-conversion multiplier.
        precision: Decimal places to round to (banker's rounding).
        return_metadata: When True, returns ConversionResult with rate info.
    """

    value = _to_decimal(amount)
    if value is None:
        return None

    src = normalize_currency_code(from_currency) or "USD"
    dst = normalize_currency_code(to_currency) or "USD"

    quant = Decimal(1).scaleb(-precision)

    if src == dst:
        rounded_same = value.quantize(quant, rounding=ROUND_HALF_UP)
        return (
            ConversionResult(float(rounded_same), dst, Decimal("1"))
            if return_metadata
            else float(rounded_same)
        )

    src_rate = rates.get(src)
    dst_rate = rates.get(dst)
    if src_rate is None or dst_rate is None or src_rate <= 0 or dst_rate <= 0:
        return None

    usd_value = value * src_rate
    converted = usd_value / dst_rate
    rounded = converted.quantize(quant, rounding=ROUND_HALF_UP)

    if return_metadata:
        rate_used = (src_rate / dst_rate) if dst_rate != 0 else Decimal("0")
        return ConversionResult(float(rounded), dst, rate_used)
    return float(rounded)


__all__ = [
    "DEFAULT_CURRENCY_RATES",
    "ConversionResult",
    "convert_currency",
    "normalize_currency_code",
]
